"""Memory and control tools for OpsAgent."""
from opsagent.tools.registry import tool


@tool(
    name="memory_remember",
    description="Store a fact in persistent memory that will be available across tasks. Use to remember vendor IDs, login tokens, discovered information, etc.",
    risk="write",
    parameters={
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "The key/name for the fact (e.g. 'acme_vendor_id')"},
            "value": {"type": "string", "description": "The value to remember"},
            "category": {"type": "string", "description": "Category: 'vendor', 'credential', 'procedure', 'general'"}
        },
        "required": ["key", "value"]
    }
)
async def memory_remember(key: str, value: str, category: str = "general") -> dict:
    # Actual storage is done by the runtime after this returns
    return {
        "success": True,
        "action": "remember",
        "key": key,
        "value": value,
        "category": category,
        "message": f"Stored fact: {key} = {value}"
    }


@tool(
    name="memory_recall",
    description="Recall facts from persistent memory. Search by key or category to find previously stored information.",
    risk="read",
    parameters={
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Specific key to recall (leave empty to search by category)"},
            "category": {"type": "string", "description": "Category to search in"},
            "query": {"type": "string", "description": "Free-text query to search stored facts"}
        },
        "required": []
    }
)
async def memory_recall(key: str = "", category: str = "", query: str = "") -> dict:
    # Actual retrieval is done by the runtime
    return {
        "success": True,
        "action": "recall",
        "key": key,
        "category": category,
        "query": query,
        "message": "Memory recall request - results will be injected by runtime"
    }


@tool(
    name="ask_human",
    description="Ask the human operator for clarification or approval. Use when the task is ambiguous, requires a decision, or needs human judgment. The task will pause until the human responds.",
    risk="read",
    parameters={
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The question to ask the human"},
            "context": {"type": "string", "description": "Relevant context to help the human make a decision"},
            "options": {"type": "string", "description": "Comma-separated list of suggested options (optional)"}
        },
        "required": ["question"]
    }
)
async def ask_human(question: str, context: str = "", options: str = "") -> dict:
    # Actual pause is handled by the runtime
    return {
        "success": True,
        "action": "ask_human",
        "question": question,
        "context": context,
        "options": options.split(",") if options else [],
        "message": "Question sent to human operator. Task paused."
    }


@tool(
    name="finish",
    description="Mark the task as complete with a summary of what was accomplished. Include evidence of completion.",
    risk="read",
    parameters={
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "Summary of what was accomplished"},
            "evidence": {"type": "string", "description": "JSON string of evidence items (screenshots, record IDs, etc.)"},
            "status": {"type": "string", "description": "'success' or 'failure'"}
        },
        "required": ["summary"]
    }
)
async def finish(summary: str, evidence: str = "[]", status: str = "success") -> dict:
    return {
        "success": True,
        "action": "finish",
        "summary": summary,
        "evidence": evidence,
        "status": status,
        "message": "Task completed."
    }
