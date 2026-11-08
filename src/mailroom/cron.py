"""Scheduled inbox ingestion for LangGraph Platform cron jobs.

The graph is a thin wrapper around the same ingestion function used by the
``run_ingest.py`` CLI, so a hosted deployment can poll Gmail on a schedule.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from langgraph.graph import START, StateGraph

from mailroom.tools.gmail.run_ingest import fetch_and_process_emails

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class IngestionJob:
    """Input for one ingestion run."""

    email: str
    minutes_since: int = 60
    graph_name: str = "mailroom_gmail"
    url: str = "http://127.0.0.1:2024"
    include_read: bool = False
    rerun: bool = False
    early: bool = False
    skip_filters: bool = False


async def ingest(state: IngestionJob) -> dict:
    """Fetch recent emails and submit them to the configured graph."""
    logger.info(
        "Ingesting email for %s from the past %s minutes into %s",
        state.email,
        state.minutes_since,
        state.graph_name,
    )
    try:
        exit_code = await fetch_and_process_emails(state)
        return {"status": "success" if exit_code == 0 else "error", "exit_code": exit_code}
    except Exception as exc:  # noqa: BLE001 - report failures through graph state
        logger.exception("Ingestion job failed")
        return {"status": "error", "error": str(exc)}


builder = StateGraph(IngestionJob)
builder.add_node("ingest_emails", ingest)
builder.add_edge(START, "ingest_emails")
graph = builder.compile()
