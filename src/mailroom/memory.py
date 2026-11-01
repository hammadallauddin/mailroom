"""Long-term memory helpers backed by a LangGraph Store."""

from __future__ import annotations

from typing import Iterable

from langgraph.store.base import BaseStore

from mailroom.config import get_settings
from mailroom.llm import get_chat_model
from mailroom.prompts import (
    MEMORY_UPDATE_INSTRUCTIONS,
    MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT,
)
from mailroom.schemas import UserPreferences

PROFILE_KEY = "user_preferences"

TRIAGE_PREFERENCES = "triage_preferences"
RESPONSE_PREFERENCES = "response_preferences"
CAL_PREFERENCES = "cal_preferences"


def _namespace(name: str) -> tuple[str, str]:
    return (get_settings().namespace, name)


def get_profile(store: BaseStore, name: str, default: str) -> str:
    """Return a stored preference profile, seeding it with ``default``."""
    namespace = _namespace(name)
    item = store.get(namespace, PROFILE_KEY)
    if item is not None:
        return item.value
    store.put(namespace, PROFILE_KEY, default)
    return default


def update_profile(store: BaseStore, name: str, messages: Iterable[dict], default: str = "") -> str:
    """Rewrite a preference profile based on human feedback."""
    namespace = _namespace(name)
    current = get_profile(store, name, default)
    model = get_chat_model(temperature=0.0).with_structured_output(UserPreferences)
    result = model.invoke(
        [
            {
                "role": "system",
                "content": MEMORY_UPDATE_INSTRUCTIONS.format(
                    current_profile=current, namespace=namespace
                ),
            },
            *messages,
        ]
    )
    store.put(namespace, PROFILE_KEY, result.user_preferences)
    return result.user_preferences


def reinforce(feedback: str) -> str:
    """Append the memory-update reinforcement block to a feedback message."""
    return f"{feedback}\n\n{MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT}"
