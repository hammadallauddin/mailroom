#!/usr/bin/env python
"""Run the LangSmith evaluation suite for Mailroom."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

LANGSMITH_PROJECT = "Mailroom: Tool Calling and Response Evaluation"
IMPLEMENTATIONS = ["basic"]


def main() -> int:
    """Run pytest for the requested implementation(s)."""
    parser = argparse.ArgumentParser(description="Run Mailroom evaluation tests")
    parser.add_argument("--experiment-name", help="Name for the LangSmith experiment")
    parser.add_argument("--implementation", choices=IMPLEMENTATIONS, help="Graph preset to test")
    parser.add_argument("--all", action="store_true", help="Run every implementation")
    args = parser.parse_args()

    implementations = [args.implementation] if args.implementation else IMPLEMENTATIONS

    for implementation in implementations:
        print(f"\nRunning evaluation for {implementation}...")
        os.environ["LANGSMITH_PROJECT"] = LANGSMITH_PROJECT
        os.environ["LANGSMITH_TEST_SUITE"] = LANGSMITH_PROJECT
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGSMITH_EXPERIMENT"] = (
            args.experiment_name or f"Response eval | Agent: {implementation}"
        )

        command = [
            sys.executable,
            "-m",
            "pytest",
            "test_response.py",
            "-v",
            "--disable-warnings",
            "--langsmith-output",
            f"--agent-module={implementation}",
        ]
        result = subprocess.run(command, cwd=Path(__file__).parent, text=True)
        if result.returncode != 0:
            return result.returncode

    return 0


if __name__ == "__main__":
    sys.exit(main())
