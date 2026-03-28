"""Reusable UI rendering components for the Streamlit frontend."""

import json
from html import escape
from typing import Any


def _normalize_args(raw: Any) -> dict[str, Any]:
    """Coerce tool args to a dict regardless of how they arrive."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
        return {"input": raw}
    if raw is None:
        return {}
    return {"value": str(raw)}


def dedup_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate tool entries, keeping the one with the richest args per name."""
    best: dict[str, dict[str, Any]] = {}
    for tool in tools:
        name = tool.get("tool_name") or tool.get("name", "unknown")
        args = _normalize_args(tool.get("args"))
        existing = best.get(name)
        if existing is None or len(args) > len(_normalize_args(existing.get("args"))):
            best[name] = tool
    return list(best.values())


def render_tool_card(tool: dict[str, Any]) -> str:
    """Return an HTML tool card showing tool name and arguments."""
    tool_name = escape(str(tool.get("tool_name") or tool.get("name", "unknown")))
    args = _normalize_args(tool.get("args"))

    args_html = ""
    for key, value in args.items():
        display_value = str(value)
        if len(display_value) > 80:
            display_value = display_value[:77] + "..."
        args_html += (
            f'<div class="tool-args">'
            f'<span class="arg-key">{escape(key)}:</span> '
            f"{escape(display_value)}"
            f"</div>"
        )

    return (
        f'<div class="tool-card">'
        f'<div class="tool-name">{tool_name}</div>'
        f"{args_html}"
        f"</div>"
    )


def render_health_indicator(health: dict[str, Any] | None) -> str:
    """Return HTML for health status dots in the sidebar."""
    if health is None:
        return (
            '<div class="health-indicator">'
            '<span class="dot-err">\u25cf</span> API offline'
            "</div>"
        )

    db_val = health.get("database", False)
    graph_val = health.get("graph_database") or health.get("neo4j", False)
    db_ok = db_val is True or db_val == "connected"
    graph_ok = graph_val is True or graph_val == "connected"

    db_dot = "dot-ok" if db_ok else "dot-err"
    graph_dot = "dot-ok" if graph_ok else "dot-err"

    return (
        '<div class="health-indicator">'
        f'<span class="{db_dot}">\u25cf</span> Database &nbsp; '
        f'<span class="{graph_dot}">\u25cf</span> Graph'
        "</div>"
    )


def render_empty_state() -> str:
    """Return HTML for the empty state placeholder shown before any search."""
    examples = [
        "What Mexican recipes do you have?",
        "Show me recipes that use garlic and tomatoes",
        "What pairs well with carnitas?",
        "Compare Italian and Chinese cooking techniques",
    ]

    example_html = "\n".join(
        f'<div class="example-query">{escape(q)}</div>' for q in examples
    )

    return (
        '<div class="empty-state">'
        '<div class="empty-title">Search your recipe knowledge base</div>'
        '<div class="empty-desc">'
        "Ask a question about recipes, ingredients, cuisines, or cooking techniques."
        "</div>"
        f"{example_html}"
        "</div>"
    )
