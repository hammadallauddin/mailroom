"""Runtime settings for Mailroom.

All settings are optional. Values are read from the environment (and from a
local ``.env`` file, when one is present) the first time they are needed, so
importing a graph never requires credentials.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

# ``google_genai`` is the provider id used by LangChain. The old
# ``google-genai:...`` spelling is not a valid provider and fails at import.
DEFAULT_MODEL = "google_genai:gemini-2.5-flash"
DEFAULT_EVAL_MODEL = "openai:gpt-4o"
DEFAULT_NAMESPACE = "mailroom"
DEFAULT_BACKGROUND = (
    "I'm a software engineer who wants help staying on top of a busy inbox."
)


@dataclass(frozen=True)
class Settings:
    """User- and deployment-specific configuration."""

    model: str = DEFAULT_MODEL
    eval_model: str = DEFAULT_EVAL_MODEL
    temperature: float = 0.0
    background: str = DEFAULT_BACKGROUND
    namespace: str = DEFAULT_NAMESPACE

    @classmethod
    def from_env(cls) -> "Settings":
        """Build settings from environment variables."""
        load_dotenv()
        return cls(
            model=os.getenv("MAILROOM_MODEL", DEFAULT_MODEL),
            eval_model=os.getenv("MAILROOM_EVAL_MODEL", DEFAULT_EVAL_MODEL),
            temperature=float(os.getenv("MAILROOM_TEMPERATURE", "0")),
            background=os.getenv("MAILROOM_BACKGROUND", DEFAULT_BACKGROUND),
            namespace=os.getenv("MAILROOM_NAMESPACE", DEFAULT_NAMESPACE),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings, loading them once."""
    return Settings.from_env()
