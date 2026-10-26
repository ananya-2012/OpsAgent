"""HTTP connector tool for OpsAgent - restricted to allowed domains."""
import json
import httpx
from opsagent.tools.registry import tool


@tool(
    name="http_get",
    description="Make an HTTP GET request to an allowed domain. Returns the response body and status. Use for API calls to the sandbox services.",
    risk="read",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL to send the GET request to"},
            "headers": {"type": "string", "description": "Optional JSON string of headers (e.g. '{\"Authorization\": \"Bearer token\"}')"}
        },
        "required": ["url"]
    }
)
async def http_get(url: str, headers: str = "{}") -> dict:
    try:
        hdrs = json.loads(headers) if headers else {}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=hdrs)
            body = resp.text
            try:
                body_json = resp.json()
            except Exception:
                body_json = None

            # Truncate large responses
            if len(body) > 8000:
                body = body[:8000] + "\n... [truncated]"

            return {
                "success": True,
                "status_code": resp.status_code,
                "body": body_json if body_json else body,
                "headers": dict(resp.headers),
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="http_post",
    description="Make an HTTP POST request to an allowed domain. Use for creating records, submitting forms via API.",
    risk="write",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL to send the POST request to"},
            "body": {"type": "string", "description": "JSON string of the request body"},
            "headers": {"type": "string", "description": "Optional JSON string of headers"},
            "content_type": {"type": "string", "description": "Content type: 'json' (default) or 'form'"}
        },
        "required": ["url", "body"]
    }
)
async def http_post(url: str, body: str, headers: str = "{}", content_type: str = "json") -> dict:
    try:
        hdrs = json.loads(headers) if headers else {}
        body_data = json.loads(body) if body else {}

        async with httpx.AsyncClient(timeout=30) as client:
            if content_type == "form":
                resp = await client.post(url, data=body_data, headers=hdrs)
            else:
                resp = await client.post(url, json=body_data, headers=hdrs)

            try:
                resp_json = resp.json()
            except Exception:
                resp_json = resp.text

            return {
                "success": resp.status_code < 400,
                "status_code": resp.status_code,
                "body": resp_json,
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="http_put",
    description="Make an HTTP PUT request to an allowed domain. Use for updating existing records.",
    risk="write",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL to send the PUT request to"},
            "body": {"type": "string", "description": "JSON string of the request body"},
            "headers": {"type": "string", "description": "Optional JSON string of headers"}
        },
        "required": ["url", "body"]
    }
)
async def http_put(url: str, body: str, headers: str = "{}") -> dict:
    try:
        hdrs = json.loads(headers) if headers else {}
        body_data = json.loads(body) if body else {}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.put(url, json=body_data, headers=hdrs)
            try:
                resp_json = resp.json()
            except Exception:
                resp_json = resp.text

            return {
                "success": resp.status_code < 400,
                "status_code": resp.status_code,
                "body": resp_json,
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="http_delete",
    description="Make an HTTP DELETE request. WARNING: This is a destructive operation and will be blocked by policy.",
    risk="destructive",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL to send the DELETE request to"},
            "headers": {"type": "string", "description": "Optional JSON string of headers"}
        },
        "required": ["url"]
    }
)
async def http_delete(url: str, headers: str = "{}") -> dict:
    # This should never execute - policy engine blocks destructive tools
    return {"success": False, "error": "DELETE operations are forbidden by policy"}
