"""Background worker: processes tasks from the SQLite-backed queue.
Supports exponential-backoff retries and task resumption after restart."""
import asyncio
import traceback
from datetime import datetime, timezone, timedelta

from opsagent.config import RETRY_MAX_ATTEMPTS, RETRY_BASE_DELAY, RETRY_MAX_DELAY, DEMO_MODE, DEMO_MAX_TASKS_PER_HOUR
from opsagent.database import (
    get_db, dequeue_task, get_task, update_task, update_queue_retry,
    remove_from_queue, add_audit_entry,
)
from opsagent.runtime.agent import AgentRuntime


class TaskWorker:
    """Background worker that processes tasks from the queue."""

    def __init__(self):
        self.running = False
        self.runtime = AgentRuntime()
        self._tasks_this_hour = 0
        self._hour_start = datetime.now(timezone.utc)

    async def start(self):
        """Start the background worker loop."""
        self.running = True
        while self.running:
            try:
                await self._process_next()
            except Exception as e:
                print(f"Worker error: {e}")
                traceback.print_exc()
            await asyncio.sleep(2)  # Poll interval

    async def stop(self):
        self.running = False

    async def _process_next(self):
        """Process the next task from the queue."""
        # Demo mode rate limiting
        if DEMO_MODE:
            now = datetime.now(timezone.utc)
            if (now - self._hour_start).total_seconds() > 3600:
                self._tasks_this_hour = 0
                self._hour_start = now
            if self._tasks_this_hour >= DEMO_MAX_TASKS_PER_HOUR:
                return

        db = await get_db()
        task_id = await dequeue_task(db)
        await db.close()

        if not task_id:
            return

        db = await get_db()
        task = await get_task(db, task_id)
        if not task:
            await remove_from_queue(db, task_id)
            await db.close()
            return

        if task['status'] in ('completed', 'failed', 'cancelled'):
            await remove_from_queue(db, task_id)
            await db.close()
            return

        await db.close()

        try:
            self._tasks_this_hour += 1
            self.runtime = AgentRuntime()  # Fresh runtime per task
            await self.runtime.run_task(task_id, task['description'])
            db = await get_db()
            await remove_from_queue(db, task_id)
            await db.close()
        except Exception as e:
            db = await get_db()
            task = await get_task(db, task_id)
            retry_count = task.get('steps_taken', 0) if task else 0
            if retry_count < RETRY_MAX_ATTEMPTS:
                delay = min(RETRY_BASE_DELAY * (2 ** retry_count), RETRY_MAX_DELAY)
                next_retry = (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat()
                await update_queue_retry(db, task_id, retry_count + 1, next_retry)
                await add_audit_entry(db, task_id, "retry_scheduled",
                                      action="retry",
                                      output_data=f"Retry {retry_count + 1} in {delay}s: {str(e)}")
            else:
                await update_task(db, task_id, status='failed',
                                 error=f"Max retries exceeded: {str(e)}")
                await remove_from_queue(db, task_id)
            await db.close()
