"""Chat-model factories.

Keeping model construction here means graphs, tools and tests all agree on the
configured model and temperature.
"""

from __future__ import annotations

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from mailroom.config import get_settings


def get_chat_model(model: str | None = None, temperature: float | None = None) -> BaseChatModel:
    """Create a chat model from the configured provider and model id."""
    settings = get_settings()
    return init_chat_model(
        model or settings.model,
        temperature=settings.temperature if temperature is None else temperature,
    )


def get_router_model(model: str | None = None) -> BaseChatModel:
    """Chat model used for triage with structured output."""
    return get_chat_model(model=model, temperature=0.0)


def get_eval_model(model: str | None = None) -> BaseChatModel:
    """Chat model used by the evaluation suite."""
    return get_chat_model(model=model or get_settings().eval_model)
