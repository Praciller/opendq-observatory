"""Deterministic explanation when an AI provider is unavailable or disabled."""

from __future__ import annotations

from opendq.ai.models import AIExplanation, IncidentAIInput, sanitize_text

_CAUSE_STEPS = {
    "DISTRIBUTION_SHIFT": (
        "Compare the current distribution with the stored baseline and inspect the affected column."
    ),
    "SCHEMA_CHANGE": (
        "Compare the current schema with the previous accepted schema and review upstream changes."
    ),
    "FRESHNESS_DELAY": (
        "Check source arrival time, ingestion lag, and the latest successful source run."
    ),
    "TIMESTAMP_GAP": (
        "Inspect timestamp continuity around the reported gap and the upstream partition or feed."
    ),
    "INVALID_VALUES": (
        "Review rejected records and the upstream field contract for the failing quality rule."
    ),
    "VOLUME_CHANGE": (
        "Compare current and baseline record counts, then inspect source "
        "completeness for the window."
    ),
    "UPSTREAM_SOURCE_FAILURE": (
        "Inspect the upstream source health and the latest failed ingestion run."
    ),
    "DATABASE_OR_PIPELINE_ERROR": (
        "Review the evaluation run error and the pipeline logs for the affected dataset."
    ),
}


def build_fallback(value: IncidentAIInput, deterministic_rca: dict[str, object]) -> AIExplanation:
    cause = str(deterministic_rca.get("top_cause") or "UNKNOWN")
    confidence = str(deterministic_rca.get("confidence") or "UNKNOWN")
    cause_label = cause.replace("_", " ").lower()
    summary = sanitize_text(
        f"Deterministic OpenDQ analysis identifies {cause_label} as the leading explanation "
        f"with {confidence.lower()} confidence.",
        max_chars=1000,
    )
    explanation = (
        f"This explanation follows the persisted deterministic RCA result. "
        f"The leading cause is {cause_label}; the AI provider was not used or was unavailable."
    )
    highlights = []
    for item in [*value.quality_evidence, *value.drift_evidence][:3]:
        if item.get("evidence_id"):
            highlights.append(
                {
                    "evidence_id": str(item["evidence_id"]),
                    "text": sanitize_text(item.get("text"), max_chars=600),
                }
            )
    uncertainties = []
    if confidence in {"LOW", "UNKNOWN"}:
        uncertainties.append(
            "The deterministic RCA confidence is limited; review the evidence before acting."
        )
    if cause == "UNKNOWN":
        uncertainties.append(
            "No supported deterministic cause was established from the available evidence."
        )
    return AIExplanation(
        summary=summary,
        probable_cause_explanation=sanitize_text(explanation, max_chars=1500),
        evidence_highlights=highlights,
        investigation_steps=[
            _CAUSE_STEPS.get(cause, "Review the incident evidence and latest pipeline events.")
        ],
        uncertainties=uncertainties,
    )
