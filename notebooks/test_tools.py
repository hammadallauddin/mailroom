"""Standalone tool-call checks for notebook exploration."""

import sys
from pathlib import Path

# Add the src directory so ``mailroom`` is importable without installing.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from dotenv import load_dotenv
from langsmith import testing as t

from mailroom.eval.email_dataset import email_inputs, expected_tool_calls
from mailroom.graph import basic
from mailroom.utils import extract_tool_calls, format_messages_string

load_dotenv()


@pytest.mark.langsmith
@pytest.mark.parametrize(
    "email_input, expected_calls",
    [
        (email_inputs[0], expected_tool_calls[0]),
        (email_inputs[3], expected_tool_calls[3]),
    ],
)
def test_email_dataset_tool_calls(email_input, expected_calls):
    """Check that the basic graph calls every expected tool."""
    result = basic.invoke({"email_input": email_input})
    extracted = extract_tool_calls(result["messages"])
    missing = [call for call in expected_calls if call.lower() not in extracted]

    t.log_outputs({
        "missing_calls": missing,
        "extracted_tool_calls": extracted,
        "response": format_messages_string(result["messages"]),
    })
    assert missing == []
