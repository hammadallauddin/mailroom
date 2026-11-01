#!/usr/bin/env python
"""Response-quality and tool-use evaluations against the Mailroom dataset.

These tests call a real model, so they require ``GOOGLE_API_KEY`` (for the
agent) and ``OPENAI_API_KEY`` (for the grader) plus LangSmith credentials.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langsmith import testing as t
from pydantic import BaseModel, Field

from mailroom.config import get_settings
from mailroom.eval.email_dataset import (
    email_inputs,
    email_names,
    expected_tool_calls,
    response_criteria_list,
    triage_outputs_list,
)
from mailroom.eval.prompts import RESPONSE_CRITERIA_SYSTEM_PROMPT
from mailroom.graph import GraphOptions, build_workflow
from mailroom.llm import get_eval_model
from mailroom.utils import extract_tool_calls, format_messages_string

SUPPORTED_PRESETS = {"basic"}


class CriteriaGrade(BaseModel):
    """Grade a response against evaluation criteria."""

    grade: bool = Field(description="Does the response meet the provided criteria?")
    justification: str = Field(
        description="Justification for the grade, including examples from the response."
    )


@pytest.fixture(scope="module")
def criteria_llm():
    """Build the grader lazily so tests can be collected without API keys."""
    return get_eval_model().with_structured_output(CriteriaGrade)



@pytest.fixture(autouse=True)
def selected_preset(agent_module_name):
    """Expose the selected preset to the tests."""
    return agent_module_name


def setup_assistant(preset: str):
    """Compile the requested preset with an in-memory checkpointer/store."""
    options = {
        "basic": GraphOptions(),
        "hitl": GraphOptions(hitl=True),
        "memory": GraphOptions(hitl=True, memory=True),
        "gmail": GraphOptions(hitl=True, memory=True, gmail=True),
    }[preset]
    workflow = build_workflow(options)
    checkpointer = MemorySaver()
    store = InMemoryStore() if options.memory else None
    assistant = workflow.compile(checkpointer=checkpointer, store=store)
    thread_config = {"configurable": {"thread_id": uuid.uuid4()}}
    return assistant, thread_config


def create_response_test_cases():
    """Build test cases for emails that require a response."""
    return [
        (email_input, name, criteria, calls)
        for email_input, name, criteria, triage, calls in zip(
            email_inputs,
            email_names,
            response_criteria_list,
            triage_outputs_list,
            expected_tool_calls,
            strict=True,
        )
        if triage == "respond"
    ]


def run_agent(preset: str, email_input: dict) -> tuple[Any, dict]:
    """Invoke the agent and return the final state values."""
    if preset not in SUPPORTED_PRESETS:
        raise ValueError(
            f"Unsupported preset {preset!r}; automated tests currently cover {sorted(SUPPORTED_PRESETS)}"
        )
    assistant, thread_config = setup_assistant(preset)
    assistant.invoke({"email_input": email_input}, config=thread_config)
    return assistant.get_state(thread_config).values, thread_config


@pytest.mark.langsmith(output_keys=["expected_calls"])
@pytest.mark.parametrize(
    "email_input,email_name,criteria,expected_calls", create_response_test_cases()
)
def test_email_dataset_tool_calls(email_input, email_name, criteria, expected_calls, agent_module_name):
    """Check that the agent calls every expected tool."""
    t.log_inputs({"preset": agent_module_name, "test": "test_email_dataset_tool_calls"})
    values, _ = run_agent(agent_module_name, email_input)

    extracted = extract_tool_calls(values["messages"])
    missing = [call for call in expected_calls if call.lower() not in extracted]
    extra = [call for call in extracted if call.lower() not in {c.lower() for c in expected_calls}]

    t.log_outputs({
        "extracted_tool_calls": extracted,
        "missing_calls": missing,
        "extra_calls": extra,
        "response": format_messages_string(values["messages"]),
    })

    assert not missing, f"{email_name}: missing tool calls {missing}"


@pytest.mark.langsmith(output_keys=["criteria"])
@pytest.mark.parametrize(
    "email_input,email_name,criteria,expected_calls", create_response_test_cases()
)
def test_response_criteria_evaluation(email_input, email_name, criteria, expected_calls, agent_module_name, criteria_llm):
    """Ask an LLM judge whether the response satisfies its criteria."""
    t.log_inputs({"preset": agent_module_name, "test": "test_response_criteria_evaluation"})
    values, _ = run_agent(agent_module_name, email_input)
    response = format_messages_string(values["messages"])

    result = criteria_llm.invoke([
        {"role": "system", "content": RESPONSE_CRITERIA_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"\n\nResponse criteria: {criteria}\n\n"
                f"Assistant's response:\n\n{response}\n\n"
                "Evaluate whether the response meets the criteria and justify your grade."
            ),
        },
    ])

    t.log_outputs({"justification": result.justification, "response": response})
    assert result.grade, f"{email_name}: {result.justification}"
