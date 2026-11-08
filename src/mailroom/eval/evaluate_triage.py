"""Evaluate triage accuracy against a LangSmith dataset."""

from __future__ import annotations

import os
from datetime import datetime

import matplotlib.pyplot as plt
from langsmith import Client

from mailroom.eval.email_dataset import examples_triage
from mailroom.graph import basic

DATASET_NAME = "Mailroom: E-mail Triage Dataset"
FEEDBACK_KEY = "classification"
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def ensure_dataset(client: Client) -> str:
    """Create the triage dataset on first run and return its name."""
    if not client.has_dataset(dataset_name=DATASET_NAME):
        dataset = client.create_dataset(
            dataset_name=DATASET_NAME,
            description="A dataset of emails and their expected triage decisions.",
        )
        client.create_examples(dataset_id=dataset.id, examples=examples_triage)
    return DATASET_NAME


def target_email_assistant(inputs: dict) -> dict:
    """Run one email through the basic graph and return its classification."""
    try:
        response = basic.invoke({"email_input": inputs["email_input"]})
        return {"classification_decision": response.get("classification_decision", "unknown")}
    except Exception as exc:  # noqa: BLE001 - keep evaluation running
        print(f"Agent invocation failed: {exc}")
        return {"classification_decision": "unknown"}


def classification_evaluator(outputs: dict, reference_outputs: dict) -> bool:
    """Exact-match evaluation against the ground-truth classification."""
    return outputs["classification_decision"].lower() == reference_outputs["classification"].lower()


def plot_results(score: float) -> str:
    """Save a one-bar comparison chart and return its path."""
    plt.figure(figsize=(10, 6))
    plt.bar(["Agentic Workflow"], [score], color=["#5DA5DA"], width=0.5)
    plt.xlabel("Agent Type")
    plt.ylabel("Average Score")
    plt.title(f"Email Triage Performance — {FEEDBACK_KEY.capitalize()} Score")
    plt.text(0, score + 0.02, f"{score:.2f}", ha="center", fontweight="bold")
    plt.ylim(0, 1.1)
    plt.grid(axis="y", linestyle="--", alpha=0.7)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    plot_path = os.path.join(
        RESULTS_DIR, f"triage_comparison_{datetime.now():%Y%m%d_%H%M%S}.png"
    )
    plt.savefig(plot_path)
    plt.close()
    return plot_path


def main() -> None:
    """Run the triage evaluation and save a chart."""
    client = Client()
    dataset_name = ensure_dataset(client)
    results = client.evaluate(
        target_email_assistant,
        data=dataset_name,
        evaluators=[classification_evaluator],
        experiment_prefix="Mailroom triage",
        max_concurrency=2,
    )

    frame = results.to_pandas()
    column = "feedback.classification_evaluator"
    score = frame[column].mean() if column in frame.columns else 0.0

    plot_path = plot_results(score)
    print(f"Evaluation chart saved to {plot_path}")
    print(f"Triage score: {score:.2f}")


if __name__ == "__main__":
    main()
