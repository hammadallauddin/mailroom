"""Gmail and Google Calendar tools for Mailroom."""

from mailroom.prompts import GMAIL_TOOLS_PROMPT
from mailroom.tools.gmail.gmail_tools import (
    check_calendar_tool,
    fetch_emails_tool,
    schedule_meeting_tool,
    send_email_tool,
)

__all__ = [
    "GMAIL_TOOLS_PROMPT",
    "check_calendar_tool",
    "fetch_emails_tool",
    "schedule_meeting_tool",
    "send_email_tool",
]
