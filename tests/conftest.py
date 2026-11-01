#!/usr/bin/env python
"""Shared pytest configuration."""

from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
for path in (str(PROJECT_ROOT), str(SRC_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)


def pytest_addoption(parser):
    """Register the graph preset selector."""
    parser.addoption(
        "--agent-module",
        action="store",
        default="basic",
        choices=["basic", "hitl", "memory", "gmail"],
        help="Which Mailroom graph preset to test",
    )


@pytest.fixture(scope="session")
def agent_module_name(request):
    """Return the graph preset selected on the command line."""
    return request.config.getoption("--agent-module")
