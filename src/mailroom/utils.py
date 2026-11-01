"""Small helpers for parsing, formatting and displaying emails."""

from __future__ import annotations

import json
from typing import Any, Iterable

import html2text

_HTML_MARKERS = ("<!doctype", "<html", "<body")
_GMAIL_KEYS = {
    "author": ("from", "From"),
    "to": ("to", "To"),
    "subject": ("subject", "Subject"),
    "email_thread": ("body", "Body", "page_content"),
    "email_id": ("id", "Id", "message_id"),
}


def _is_html(content: str) -> bool:
    head = content.lstrip()[:200].lower()
    return any(marker in head for marker in _HTML_MARKERS)


def _to_markdown(content: str) -> str:
    """Convert HTML email bodies to readable Markdown."""
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = True
    converter.body_width = 0
    return converter.handle(content)


def _format_markdown(
    subject: str,
    author: str,
    to: str,
    email_thread: str,
    email_id: str | None = None,
    *,
    convert_html: bool = False,
) -> str:
    id_section = f"\n**ID**: {email_id}" if email_id else ""
    if convert_html and email_thread and _is_html(email_thread):
        email_thread = _to_markdown(email_thread)

    return f"""
**Subject**: {subject}
**From**: {author}
**To**: {to}{id_section}

{email_thread}

---
"""


def format_email_markdown(
    subject: str,
    author: str,
    to: str,
    email_thread: str,
    email_id: str | None = None,
) -> str:
    """Format a plain-text email for display."""
    return _format_markdown(subject, author, to, email_thread, email_id)


def format_gmail_markdown(
    subject: str,
    author: str,
    to: str,
    email_thread: str,
    email_id: str | None = None,
) -> str:
    """Format a Gmail email for display, converting HTML bodies to Markdown."""
    return _format_markdown(
        subject, author, to, email_thread, email_id, convert_html=True
    )


def format_for_display(tool_call: dict) -> str:
    """Render a tool call for Agent Inbox."""
    name = tool_call.get("name", "")
    args = tool_call.get("args") or {}

    if name in {"write_email", "send_email_tool"}:
        return (
            f"# Email Draft\n\n"
            f"**To**: {args.get('to') or args.get('email_address')}\n"
            f"**Subject**: {args.get('subject', '')}\n\n"
            f"{args.get('content') or args.get('response_text') or ''}\n"
        )

    if name in {"schedule_meeting", "schedule_meeting_tool"}:
        attendees = args.get("attendees") or []
        return (
            f"# Calendar Invite\n\n"
            f"**Meeting**: {args.get('subject', '')}\n"
            f"**Attendees**: {', '.join(attendees)}\n"
            f"**Duration**: {args.get('duration_minutes', '')} minutes\n"
            f"**Day**: {args.get('preferred_day') or args.get('start_time')}\n"
        )

    if name == "Question":
        return f"# Question for User\n\n{args.get('content', '')}\n"

    if isinstance(args, dict):
        rendered = json.dumps(args, indent=2)
    else:
        rendered = str(args)
    return f"# Tool Call: {name}\n\nArguments:\n{rendered}\n"


def parse_email(email_input: dict) -> tuple[str, str, str, str]:
    """Return ``(author, to, subject, email_thread)`` from a normalized email."""
    return (
        email_input["author"],
        email_input["to"],
        email_input["subject"],
        email_input["email_thread"],
    )


def parse_gmail(email_input: dict) -> tuple[str, str, str, str, str | None]:
    """Return ``(author, to, subject, email_thread, email_id)`` from a Gmail payload.

    Gmail ingestion emits capitalized keys, while the mock tools use snake_case,
    so both spellings are accepted.
    """

    def first(key: str) -> Any:
        for candidate in _GMAIL_KEYS[key]:
            if candidate in email_input:
                return email_input[candidate]
        return None

    return (
        first("author") or "",
        first("to") or "",
        first("subject") or "",
        first("email_thread") or "",
        first("email_id"),
    )


def extract_message_content(message: Any) -> str:
    """Extract text from a message, handling both string and block content."""
    content = getattr(message, "content", message)

    if isinstance(content, str):
        if "<Recursion on AIMessage with id=" in content:
            return "[Recursive content]"
        return content

    if isinstance(content, list):
        return "\n".join(
            item["text"]
            for item in content
            if isinstance(item, dict) and "text" in item
        )

    return str(content)


def format_few_shot_examples(examples: Iterable[Any]) -> str:
    """Format router examples stored by the vector store."""
    formatted = []
    for example in examples:
        email_part, rest = example.value.split("Original routing:", 1)
        original_routing, correct_routing = rest.split("Correct routing:", 1)
        formatted.append(
            f"""Example:
Email: {email_part.strip()}
Original Classification: {original_routing.strip()}
Correct Classification: {correct_routing.strip()}
---"""
        )
    return "\n".join(formatted)


def extract_tool_calls(messages: Iterable[Any]) -> list[str]:
    """Extract lower-cased tool-call names from messages."""
    names: list[str] = []
    for message in messages:
        tool_calls = (
            message.get("tool_calls")
            if isinstance(message, dict)
            else getattr(message, "tool_calls", None)
        )
        if tool_calls:
            names.extend(call["name"].lower() for call in tool_calls)
    return names


def format_messages_string(messages: Iterable[Any]) -> str:
    """Join messages into a single string for evaluation."""
    return "\n".join(message.pretty_repr() for message in messages)


def show_graph(graph: Any, xray: bool = False) -> Any:
    """Render a LangGraph mermaid diagram, with a pyppeteer fallback."""
    from IPython.display import Image

    try:
        return Image(graph.get_graph(xray=xray).draw_mermaid_png())
    except Exception:  # noqa: BLE001 - renderer failures are environment-specific
        import nest_asyncio
        from langchain_core.runnables.graph import MermaidDrawMethod

        nest_asyncio.apply()
        return Image(
            graph.get_graph().draw_mermaid_png(draw_method=MermaidDrawMethod.PYPPETEER)
        )
