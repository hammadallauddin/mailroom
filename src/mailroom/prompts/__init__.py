"""Prompt templates and defaults for Mailroom.

Names are re-exported in both ``SCREAMING_CASE`` (new code) and the original
snake_case spellings used by the notebooks.
"""

from mailroom.config import DEFAULT_BACKGROUND
from mailroom.prompts.defaults import (
    DEFAULT_CAL_PREFERENCES,
    DEFAULT_RESPONSE_PREFERENCES,
    DEFAULT_TRIAGE_INSTRUCTIONS,
)
from mailroom.prompts.memory import (
    MEMORY_UPDATE_INSTRUCTIONS,
    MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT,
)
from mailroom.prompts.response import (
    AGENT_SYSTEM_PROMPT,
    AGENT_SYSTEM_PROMPT_HITL,
    render_agent_prompt,
)
from mailroom.prompts.tools import (
    AGENT_TOOLS_PROMPT,
    COMBINED_TOOLS_PROMPT,
    GMAIL_TOOLS_PROMPT,
    HITL_MEMORY_TOOLS_PROMPT,
    HITL_TOOLS_PROMPT,
    STANDARD_TOOLS_PROMPT,
)
from mailroom.prompts.triage import TRIAGE_SYSTEM_PROMPT, TRIAGE_USER_PROMPT

# Backwards-compatible aliases (notebooks and earlier versions).
triage_system_prompt = TRIAGE_SYSTEM_PROMPT
triage_user_prompt = TRIAGE_USER_PROMPT
agent_system_prompt = AGENT_SYSTEM_PROMPT
agent_system_prompt_hitl = AGENT_SYSTEM_PROMPT_HITL
agent_system_prompt_hitl_memory = AGENT_SYSTEM_PROMPT_HITL
default_background = DEFAULT_BACKGROUND
default_triage_instructions = DEFAULT_TRIAGE_INSTRUCTIONS
default_response_preferences = DEFAULT_RESPONSE_PREFERENCES
default_cal_preferences = DEFAULT_CAL_PREFERENCES

__all__ = [
    "AGENT_SYSTEM_PROMPT",
    "AGENT_SYSTEM_PROMPT_HITL",
    "AGENT_TOOLS_PROMPT",
    "COMBINED_TOOLS_PROMPT",
    "DEFAULT_BACKGROUND",
    "DEFAULT_CAL_PREFERENCES",
    "DEFAULT_RESPONSE_PREFERENCES",
    "DEFAULT_TRIAGE_INSTRUCTIONS",
    "GMAIL_TOOLS_PROMPT",
    "HITL_MEMORY_TOOLS_PROMPT",
    "HITL_TOOLS_PROMPT",
    "MEMORY_UPDATE_INSTRUCTIONS",
    "MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT",
    "STANDARD_TOOLS_PROMPT",
    "TRIAGE_SYSTEM_PROMPT",
    "TRIAGE_USER_PROMPT",
    "agent_system_prompt",
    "agent_system_prompt_hitl",
    "agent_system_prompt_hitl_memory",
    "default_background",
    "default_cal_preferences",
    "default_response_preferences",
    "default_triage_instructions",
    "render_agent_prompt",
    "triage_system_prompt",
    "triage_user_prompt",
]
