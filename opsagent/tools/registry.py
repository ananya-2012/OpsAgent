"""Decorator-based tool registry for OpsAgent.
Each tool declares its schema, risk level, and required permissions."""
import functools
import inspect
from typing import Any, Callable

# Global tool registry
_TOOL_REGISTRY: dict[str, dict] = {}


def tool(name: str, description: str, risk: str = "read",
         requires_permission: bool = False, parameters: dict = None):
    """Decorator to register a function as an agent tool.

    Args:
        name: Unique tool name (used in LLM function calling)
        description: Human-readable description for the LLM
        risk: Risk level - "read", "write", or "destructive"
        requires_permission: Whether the tool needs explicit user permission
        parameters: JSON Schema for tool parameters
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        # Register the tool
        _TOOL_REGISTRY[name] = {
            "name": name,
            "description": description,
            "risk": risk,
            "requires_permission": requires_permission,
            "parameters": parameters or _infer_parameters(func),
            "function": wrapper,
        }
        wrapper._tool_name = name
        wrapper._tool_info = _TOOL_REGISTRY[name]
        return wrapper
    return decorator


def _infer_parameters(func: Callable) -> dict:
    """Infer JSON Schema parameters from function signature."""
    sig = inspect.signature(func)
    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        if param_name in ('self', 'cls', 'context'):
            continue

        prop = {"type": "string"}  # default
        annotation = param.annotation
        if annotation == int:
            prop = {"type": "integer"}
        elif annotation == float:
            prop = {"type": "number"}
        elif annotation == bool:
            prop = {"type": "boolean"}
        elif annotation == list:
            prop = {"type": "array", "items": {"type": "string"}}

        if param.default == inspect.Parameter.empty:
            required.append(param_name)

        properties[param_name] = prop

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def get_all_tools() -> dict[str, dict]:
    """Get all registered tools."""
    return _TOOL_REGISTRY.copy()


def get_tool(name: str) -> dict | None:
    """Get a specific tool by name."""
    return _TOOL_REGISTRY.get(name)


def get_tool_schemas_for_llm() -> list[dict]:
    """Get tool schemas formatted for Gemini function calling."""
    schemas = []
    for name, info in _TOOL_REGISTRY.items():
        schema = {
            "name": name,
            "description": info["description"],
            "parameters": info["parameters"],
        }
        schemas.append(schema)
    return schemas


def get_tool_descriptions() -> str:
    """Get human-readable tool descriptions for system prompt."""
    lines = []
    for name, info in _TOOL_REGISTRY.items():
        risk_badge = f"[{info['risk'].upper()}]"
        lines.append(f"- {name} {risk_badge}: {info['description']}")
    return "\n".join(lines)
