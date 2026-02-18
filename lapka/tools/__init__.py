"""Tool registry for Lapka agent."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

# Global registry
_TOOLS: dict[str, "ToolDef"] = {}


@dataclass
class ToolDef:
    name: str
    description: str
    parameters: dict[str, Any]
    fn: Callable[..., Awaitable[str]]


def tool(name: str, description: str, parameters: dict[str, Any] | None = None):
    """Decorator to register a tool function."""
    def decorator(fn: Callable[..., Awaitable[str]]) -> Callable[..., Awaitable[str]]:
        _TOOLS[name] = ToolDef(
            name=name,
            description=description,
            parameters=parameters or {},
            fn=fn,
        )
        return fn
    return decorator


def get_all_tools() -> dict[str, ToolDef]:
    return _TOOLS


def get_tool(name: str) -> ToolDef | None:
    return _TOOLS.get(name)


def tools_for_llm() -> list[dict[str, Any]]:
    """Return tool definitions in OpenAI function-calling format."""
    result = []
    for t in _TOOLS.values():
        result.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        })
    return result
