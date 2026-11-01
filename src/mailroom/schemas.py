"""State and structured-output schemas shared by every Mailroom graph."""

from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.graph import MessagesState
from pydantic import BaseModel, Field

Classification = Literal["ignore", "respond", "notify"]


class RouterSchema(BaseModel):
    """Triage decision for an incoming email."""

    reasoning: str = Field(
        description="Step-by-step reasoning behind the classification."
    )
    classification: Classification = Field(
        description=(
            "The classification of an email: 'ignore' for irrelevant emails, "
            "'notify' for important information that doesn't need a response, "
            "'respond' for emails that need a reply"
        )
    )


class StateInput(TypedDict, total=False):
    """Graph input: a single email to process."""

    email_input: dict


class State(MessagesState):
    """Graph state.

    ``messages`` comes from :class:`MessagesState`; the remaining fields track
    the email being handled and the triage outcome.
    """

    email_input: dict
    classification_decision: Classification


class EmailData(TypedDict):
    """Normalized email payload."""

    id: str
    thread_id: str
    from_email: str
    subject: str
    page_content: str
    send_time: str
    to_email: str


class UserPreferences(BaseModel):
    """Updated user preferences derived from human feedback."""

    chain_of_thought: str = Field(
        description="Reasoning about which user preferences need to be added or updated"
    )
    user_preferences: str = Field(description="Updated user preferences")
