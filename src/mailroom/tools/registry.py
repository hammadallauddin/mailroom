"""Tool registry.

Tools are looked up by name so a graph can opt into a subset (or swap the mock
tools for the Gmail-backed ones) without importing provider SDKs eagerly.
"""

from __future__ import annotations

from typing import Iterable

from langchain_core.tools import BaseTool

MOCK_TOOL_NAMES = (
    "write_email",
    "schedule_meeting",
    "check_calendar_availability",
    "Question",
    "Done",
)

GMAIL_TOOL_NAMES = (
    "fetch_emails_tool",
    "send_email_tool",
    "check_calendar_tool",
    "schedule_meeting_tool",
)


def _mock_tools() -> dict[str, BaseTool]:
    from mailroom.tools.mock import (
        Done,
        Question,
        check_calendar_availability,
        schedule_meeting,
        triage_email,
        write_email,
    )

    return {
        "write_email": write_email,
        "schedule_meeting": schedule_meeting,
        "check_calendar_availability": check_calendar_availability,
        "triage_email": triage_email,
        "Question": Question,
        "Done": Done,
    }


def _gmail_tools() -> dict[str, BaseTool]:
    from mailroom.tools.gmail import (
        check_calendar_tool,
        fetch_emails_tool,
        schedule_meeting_tool,
        send_email_tool,
    )

    return {
        "fetch_emails_tool": fetch_emails_tool,
        "send_email_tool": send_email_tool,
        "check_calendar_tool": check_calendar_tool,
        "schedule_meeting_tool": schedule_meeting_tool,
    }


def get_tools(
    tool_names: Iterable[str] | None = None,
    *,
    include_gmail: bool = False,
) -> list[BaseTool]:
    """Return the requested tools, or every available tool."""
    available = _mock_tools()
    if include_gmail:
        available.update(_gmail_tools())

    if tool_names is None:
        return list(available.values())

    missing = [name for name in tool_names if name not in available]
    if missing:
        raise KeyError(f"Unknown tool(s): {', '.join(missing)}")
    return [available[name] for name in tool_names]


def get_tools_by_name(tools: Iterable[BaseTool] | None = None) -> dict[str, BaseTool]:
    """Index tools by their ``name`` attribute."""
    tools = list(tools) if tools is not None else get_tools()
    return {tool.name: tool for tool in tools}
