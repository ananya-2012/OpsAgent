"""Dashboard server: main FastAPI app serving the dashboard UI,
task management API, SSE live trace, and proxying to the sandbox."""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse
from pathlib import Path

from opsagent.config import DASHBOARD_PORT, SANDBOX_PORT
from opsagent.database import (
    get_db, create_task, get_task, list_tasks, update_task,
    get_audit_log, get_all_facts, get_pending_approvals,
    respond_to_approval, enqueue_task, add_audit_entry,
)
from opsagent.runtime.agent import get_sse_queue, emit_event, AgentRuntime
from opsagent.runtime.worker import TaskWorker
from opsagent.verifier.verify import verify_task, verify_and_loop_back
from opsagent.policy.engine import PolicyEngine

worker = TaskWorker()
worker_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background worker on startup."""
    global worker_task
    worker_task = asyncio.create_task(worker.start())
    yield
    await worker.stop()
    if worker_task:
        worker_task.cancel()


app = FastAPI(title="OpsAgent Dashboard", version="1.0.0", lifespan=lifespan)

# Static files and templates
static_dir = Path(__file__).parent / "static"
templates_dir = Path(__file__).parent / "templates"
static_dir.mkdir(parents=True, exist_ok=True)
templates_dir.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
jinja_templates = Jinja2Templates(directory=str(templates_dir))


# ---------- Dashboard UI ----------

@app.get("/", response_class=HTMLResponse)
async def dashboard_home():
    html_path = templates_dir / "dashboard.html"
    return HTMLResponse(html_path.read_text())


# ---------- Task API ----------

@app.post("/api/tasks")
async def create_new_task(request: Request):
    """Submit a new task."""
    body = await request.json()
    description = body.get("description", "").strip()
    if not description:
        raise HTTPException(status_code=400, detail="Task description is required")

    task_id = str(uuid.uuid4())[:8]
    db = await get_db()
    task = await create_task(db, task_id, description)
    await enqueue_task(db, task_id)
    await add_audit_entry(db, task_id, "task_created",
                          action="create", input_data=description)
    await db.close()

    return {"task_id": task_id, "status": "pending", "message": "Task queued"}


@app.get("/api/tasks")
async def api_list_tasks():
    db = await get_db()
    tasks = await list_tasks(db)
    await db.close()
    return {"tasks": tasks}


@app.get("/api/tasks/{task_id}")
async def api_get_task(task_id: str):
    db = await get_db()
    task = await get_task(db, task_id)
    await db.close()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.get("/api/tasks/{task_id}/audit")
async def api_get_audit(task_id: str):
    db = await get_db()
    log = await get_audit_log(db, task_id)
    await db.close()
    return {"audit_log": log}


@app.get("/api/tasks/{task_id}/verify")
async def api_verify_task(task_id: str):
    report = await verify_task(task_id)
    return report


@app.post("/api/tasks/{task_id}/verify-and-fix")
async def api_verify_and_fix(task_id: str):
    """Verify and loop back if discrepancies found."""
    report = await verify_and_loop_back(task_id)
    return report


# ---------- SSE Live Trace ----------

@app.get("/api/tasks/{task_id}/stream")
async def task_stream(task_id: str):
    """SSE endpoint for live task trace."""
    queue = get_sse_queue(task_id)

    async def event_generator():
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30)
                yield {
                    "event": event["type"],
                    "data": json.dumps(event["data"]),
                }
            except asyncio.TimeoutError:
                yield {"event": "heartbeat", "data": json.dumps({"alive": True})}
            except Exception:
                break

    return EventSourceResponse(event_generator())


# ---------- Approvals ----------

@app.get("/api/approvals")
async def api_get_approvals():
    db = await get_db()
    approvals = await get_pending_approvals(db)
    await db.close()
    return {"approvals": approvals}


@app.post("/api/approvals/{approval_id}/respond")
async def api_respond_approval(approval_id: int, request: Request):
    body = await request.json()
    response = body.get("response", "")
    if not response:
        raise HTTPException(status_code=400, detail="Response is required")

    db = await get_db()
    await respond_to_approval(db, approval_id, response)
    await add_audit_entry(db, "", "approval_response",
                          approval_status=response,
                          input_data=f"approval_id={approval_id}")
    await db.close()
    return {"status": "responded", "response": response}


# ---------- Memory ----------

@app.get("/api/memory")
async def api_get_memory():
    db = await get_db()
    facts = await get_all_facts(db)
    await db.close()
    return {"facts": facts}


# ---------- Policy ----------

@app.get("/api/policy")
async def api_get_policy():
    engine = PolicyEngine()
    return engine.get_policy_summary()


# ---------- Health ----------

@app.get("/health")
async def health():
    return {"status": "ok", "service": "dashboard", "worker_running": worker.running}
