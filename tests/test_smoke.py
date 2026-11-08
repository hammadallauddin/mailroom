#!/usr/bin/env python
"""Offline smoke tests: no model calls, credentials, or network access."""

from __future__ import annotations

import asyncio

from mailroom.cron import IngestionJob, IngestionState
from mailroom.cron import graph as cron_graph
from mailroom.graph import GraphOptions, build_workflow
from mailroom.utils import parse_email, parse_gmail


def test_parse_email_round_trip():
    email = {
        "author": "Alice <alice@example.com>",
        "to": "you@example.com",
        "subject": "Hello",
        "email_thread": "Body",
    }
    assert parse_email(email) == (
        "Alice <alice@example.com>",
        "you@example.com",
        "Hello",
        "Body",
    )


def test_parse_gmail_accepts_capitalized_and_snake_case_keys():
    payload = {
        "from": "Alice <alice@example.com>",
        "to": "you@example.com",
        "subject": "Hello",
        "body": "Body",
        "id": "msg-1",
    }
    assert parse_gmail(payload) == (
        "Alice <alice@example.com>",
        "you@example.com",
        "Hello",
        "Body",
        "msg-1",
    )
    assert parse_gmail(
        {
            "author": "Alice <alice@example.com>",
            "to": "you@example.com",
            "subject": "Hello",
            "email_thread": "Body",
            "email_id": "msg-1",
        }
    ) == (
        "Alice <alice@example.com>",
        "you@example.com",
        "Hello",
        "Body",
        "msg-1",
    )


def test_graph_options_select_expected_tools():
    assert GraphOptions().hitl_tools == frozenset()
    assert GraphOptions(hitl=True).hitl_tools == frozenset(
        {"write_email", "schedule_meeting", "Question"}
    )
    assert GraphOptions(gmail=True).tool_names == (
        "send_email_tool",
        "schedule_meeting_tool",
        "check_calendar_tool",
        "Question",
        "Done",
    )


def test_workflow_builds_and_compiles():
    workflow = build_workflow(GraphOptions(hitl=True, memory=True))
    assert workflow.compile() is not None


def test_cron_graph_records_success(monkeypatch):
    async def fake_ingest(job):
        assert job.email == "you@example.com"
        return 0

    monkeypatch.setattr("mailroom.cron.fetch_and_process_emails", fake_ingest)
    result = asyncio.run(cron_graph.ainvoke({"email": "you@example.com"}))

    assert result["status"] == "success"
    assert result["exit_code"] == 0
    assert result["error"] is None


def test_cron_graph_records_failure(monkeypatch):
    async def failing_ingest(job):
        raise RuntimeError("boom")

    monkeypatch.setattr("mailroom.cron.fetch_and_process_emails", failing_ingest)
    result = asyncio.run(cron_graph.ainvoke({"email": "you@example.com"}))

    assert result["status"] == "error"
    assert result["error"] == "boom"


def test_ingestion_job_defaults():
    job = IngestionJob(email="you@example.com")
    assert job.minutes_since == 60
    assert job.graph_name == "mailroom_gmail"
    assert job.url == "http://127.0.0.1:2024"


def test_ingestion_state_defaults():
    state = IngestionState(email="you@example.com")
    assert state.status == ""
    assert state.exit_code == 0
    assert state.error is None
