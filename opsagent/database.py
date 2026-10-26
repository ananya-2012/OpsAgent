"""SQLite database layer for OpsAgent - tasks, audit log, memory, queue."""
import aiosqlite
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from opsagent.config import DB_PATH


async def get_db() -> aiosqlite.Connection:
    """Get a database connection, creating tables if needed."""
    os.makedirs(DB_PATH.parent, exist_ok=True)
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    await _init_tables(db)
    return db


async def _init_tables(db: aiosqlite.Connection):
    await db.executescript("""
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        description TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        plan TEXT DEFAULT '[]',
        memory TEXT DEFAULT '{}',
        evidence TEXT DEFAULT '[]',
        result TEXT DEFAULT '',
        error TEXT DEFAULT '',
        steps_taken INTEGER DEFAULT 0,
        max_steps INTEGER DEFAULT 50,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        completed_at TEXT DEFAULT NULL
    );

    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        event_type TEXT NOT NULL,
        tool_name TEXT DEFAULT '',
        action TEXT DEFAULT '',
        input_data TEXT DEFAULT '',
        output_data TEXT DEFAULT '',
        policy_decision TEXT DEFAULT '',
        approval_status TEXT DEFAULT '',
        llm_step TEXT DEFAULT '',
        FOREIGN KEY (task_id) REFERENCES tasks(id)
    );

    CREATE TABLE IF NOT EXISTS persistent_facts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT DEFAULT '',
        key TEXT NOT NULL,
        value TEXT NOT NULL,
        category TEXT DEFAULT 'general',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS task_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT NOT NULL UNIQUE,
        priority INTEGER DEFAULT 0,
        retry_count INTEGER DEFAULT 0,
        next_retry_at TEXT DEFAULT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (task_id) REFERENCES tasks(id)
    );

    CREATE TABLE IF NOT EXISTS approval_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT NOT NULL,
        question TEXT NOT NULL,
        context TEXT DEFAULT '',
        request_type TEXT DEFAULT 'approval',
        response TEXT DEFAULT NULL,
        responded_at TEXT DEFAULT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (task_id) REFERENCES tasks(id)
    );

    CREATE INDEX IF NOT EXISTS idx_audit_task ON audit_log(task_id);
    CREATE INDEX IF NOT EXISTS idx_facts_key ON persistent_facts(key);
    CREATE INDEX IF NOT EXISTS idx_queue_next ON task_queue(next_retry_at);
    """)
    await db.commit()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- Task CRUD ----------

async def create_task(db: aiosqlite.Connection, task_id: str, description: str,
                      max_steps: int = 50) -> dict:
    now = now_iso()
    await db.execute(
        "INSERT INTO tasks (id, description, status, created_at, updated_at, max_steps) "
        "VALUES (?, ?, 'pending', ?, ?, ?)",
        (task_id, description, now, now, max_steps)
    )
    await db.commit()
    return await get_task(db, task_id)


async def get_task(db: aiosqlite.Connection, task_id: str) -> dict | None:
    cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = await cursor.fetchone()
    if not row:
        return None
    d = dict(row)
    d['plan'] = json.loads(d['plan']) if d['plan'] else []
    d['memory'] = json.loads(d['memory']) if d['memory'] else {}
    d['evidence'] = json.loads(d['evidence']) if d['evidence'] else []
    return d


async def update_task(db: aiosqlite.Connection, task_id: str, **kwargs):
    now = now_iso()
    sets = ["updated_at = ?"]
    vals = [now]
    for k, v in kwargs.items():
        if k in ('plan', 'memory', 'evidence'):
            v = json.dumps(v)
        sets.append(f"{k} = ?")
        vals.append(v)
    vals.append(task_id)
    await db.execute(f"UPDATE tasks SET {', '.join(sets)} WHERE id = ?", vals)
    await db.commit()


async def list_tasks(db: aiosqlite.Connection, limit: int = 50) -> list:
    cursor = await db.execute(
        "SELECT id, description, status, steps_taken, created_at, updated_at, completed_at "
        "FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)
    )
    return [dict(r) for r in await cursor.fetchall()]


# ---------- Audit Log ----------

async def add_audit_entry(db: aiosqlite.Connection, task_id: str, event_type: str, **kwargs):
    await db.execute(
        "INSERT INTO audit_log (task_id, timestamp, event_type, tool_name, action, "
        "input_data, output_data, policy_decision, approval_status, llm_step) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            task_id, now_iso(), event_type,
            kwargs.get('tool_name', ''),
            kwargs.get('action', ''),
            json.dumps(kwargs.get('input_data', ''))[:2000],
            json.dumps(kwargs.get('output_data', ''))[:2000],
            kwargs.get('policy_decision', ''),
            kwargs.get('approval_status', ''),
            json.dumps(kwargs.get('llm_step', ''))[:2000],
        )
    )
    await db.commit()


async def get_audit_log(db: aiosqlite.Connection, task_id: str) -> list:
    cursor = await db.execute(
        "SELECT * FROM audit_log WHERE task_id = ? ORDER BY id ASC", (task_id,)
    )
    return [dict(r) for r in await cursor.fetchall()]


# ---------- Persistent Facts (cross-task memory) ----------

async def set_fact(db: aiosqlite.Connection, key: str, value: str,
                   category: str = 'general', task_id: str = ''):
    now = now_iso()
    existing = await db.execute(
        "SELECT id FROM persistent_facts WHERE key = ?", (key,)
    )
    row = await existing.fetchone()
    if row:
        await db.execute(
            "UPDATE persistent_facts SET value = ?, updated_at = ?, task_id = ? WHERE key = ?",
            (value, now, task_id, key)
        )
    else:
        await db.execute(
            "INSERT INTO persistent_facts (task_id, key, value, category, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (task_id, key, value, category, now, now)
        )
    await db.commit()


async def get_fact(db: aiosqlite.Connection, key: str) -> str | None:
    cursor = await db.execute(
        "SELECT value FROM persistent_facts WHERE key = ?", (key,)
    )
    row = await cursor.fetchone()
    return row['value'] if row else None


async def get_all_facts(db: aiosqlite.Connection) -> list:
    cursor = await db.execute(
        "SELECT key, value, category, updated_at FROM persistent_facts ORDER BY updated_at DESC"
    )
    return [dict(r) for r in await cursor.fetchall()]


# ---------- Queue ----------

async def enqueue_task(db: aiosqlite.Connection, task_id: str, priority: int = 0):
    now = now_iso()
    await db.execute(
        "INSERT OR IGNORE INTO task_queue (task_id, priority, created_at) VALUES (?, ?, ?)",
        (task_id, priority, now)
    )
    await db.commit()


async def dequeue_task(db: aiosqlite.Connection) -> str | None:
    cursor = await db.execute(
        "SELECT tq.task_id FROM task_queue tq JOIN tasks t ON tq.task_id = t.id "
        "WHERE t.status IN ('pending', 'running') "
        "AND (tq.next_retry_at IS NULL OR tq.next_retry_at <= ?) "
        "ORDER BY tq.priority DESC, tq.created_at ASC LIMIT 1",
        (now_iso(),)
    )
    row = await cursor.fetchone()
    if row:
        return row['task_id']
    return None


async def update_queue_retry(db: aiosqlite.Connection, task_id: str,
                              retry_count: int, next_retry_at: str):
    await db.execute(
        "UPDATE task_queue SET retry_count = ?, next_retry_at = ? WHERE task_id = ?",
        (retry_count, next_retry_at, task_id)
    )
    await db.commit()


async def remove_from_queue(db: aiosqlite.Connection, task_id: str):
    await db.execute("DELETE FROM task_queue WHERE task_id = ?", (task_id,))
    await db.commit()


# ---------- Approvals ----------

async def create_approval_request(db: aiosqlite.Connection, task_id: str,
                                   question: str, context: str = '',
                                   request_type: str = 'approval') -> int:
    now = now_iso()
    cursor = await db.execute(
        "INSERT INTO approval_requests (task_id, question, context, request_type, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (task_id, question, context, request_type, now)
    )
    await db.commit()
    return cursor.lastrowid


async def get_pending_approvals(db: aiosqlite.Connection, task_id: str = None) -> list:
    if task_id:
        cursor = await db.execute(
            "SELECT * FROM approval_requests WHERE task_id = ? AND response IS NULL "
            "ORDER BY created_at ASC", (task_id,)
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM approval_requests WHERE response IS NULL ORDER BY created_at ASC"
        )
    return [dict(r) for r in await cursor.fetchall()]


async def respond_to_approval(db: aiosqlite.Connection, approval_id: int, response: str):
    now = now_iso()
    await db.execute(
        "UPDATE approval_requests SET response = ?, responded_at = ? WHERE id = ?",
        (response, now, approval_id)
    )
    await db.commit()
