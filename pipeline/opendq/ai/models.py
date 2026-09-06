"""Strict, bounded contracts for the optional incident explanation layer."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Set
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

_SECRET_PATTERN = re.compile(
    r"(?i)\b(?:DATABASE_URL|(?:GROQ|GEMINI)_API_KEY|PGPASSWORD|VERCEL_OIDC_TOKEN)\s*=\s*[^\s,;]+"
)
_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _safe_value(value: Any, *, max_chars: int, depth: int = 0) -> Any:
    if depth >= 3:
        if isinstance(value, (Mapping, list, tuple)):
            return "[NESTED_VALUE_OMITTED]"
        return sanitize_text(value, max_chars=max_chars)
    if isinstance(value, str):
        return sanitize_text(value, max_chars=max_chars)
    if isinstance(value, Mapping):
        safe_mapping: dict[str, Any] = {}
        for key, item in list(value.items())[:20]:
            safe_key = sanitize_text(key, max_chars=80)
            if (
                safe_key.upper()
                in {
                    "DATABASE_URL",
                    "GROQ_API_KEY",
                    "GEMINI_API_KEY",
                    "PGPASSWORD",
                    "VERCEL_OIDC_TOKEN",
                }
                or "TOKEN" in safe_key.upper()
            ):
                safe_mapping[safe_key] = "[REDACTED]"
            else:
                safe_mapping[safe_key] = _safe_value(item, max_chars=max_chars, depth=depth + 1)
        return safe_mapping
    if isinstance(value, (list, tuple)):
        return [
            _safe_value(item, max_chars=max_chars, depth=depth + 1) for item in list(value)[:20]
        ]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return sanitize_text(value, max_chars=max_chars)


class AICopilotStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FALLBACK = "FALLBACK"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


def sanitize_text(value: Any, *, max_chars: int = 500) -> str:
    text = _CONTROL_PATTERN.sub(" ", str(value or ""))
    text = _SECRET_PATTERN.sub(lambda match: f"{match.group(0).split('=')[0]}=[REDACTED]", text)
    return " ".join(text.split())[:max_chars]


def _safe_items(
    items: Iterable[Mapping[str, Any]],
    *,
    allowed_keys: Set[str],
    max_items: int,
    max_chars: int,
) -> list[dict[str, Any]]:
    safe: list[dict[str, Any]] = []
    for item in list(items)[:max_items]:
        row: dict[str, Any] = {}
        for key in allowed_keys:
            if key not in item:
                continue
            value = item[key]
            row[key] = _safe_value(value, max_chars=max_chars)
        if row:
            safe.append(row)
    return safe


@dataclass(frozen=True, slots=True)
class IncidentAIInput:
    incident: dict[str, str]
    deterministic_rca: dict[str, str]
    quality_evidence: list[dict[str, Any]]
    drift_evidence: list[dict[str, Any]]
    lineage_impact: list[dict[str, Any]]
    timeline: list[dict[str, Any]]

    @classmethod
    def from_parts(
        cls,
        *,
        incident: Mapping[str, Any],
        deterministic_rca: Mapping[str, Any],
        quality_evidence: Iterable[Mapping[str, Any]],
        drift_evidence: Iterable[Mapping[str, Any]],
        lineage_impact: Iterable[Mapping[str, Any]],
        timeline: Iterable[Mapping[str, Any]],
        max_chars: int = 500,
    ) -> IncidentAIInput:
        return cls(
            incident={
                key: sanitize_text(incident.get(key), max_chars=max_chars)
                for key in ("kind", "severity", "status", "dataset")
            },
            deterministic_rca={
                key: sanitize_text(deterministic_rca.get(key), max_chars=max_chars)
                for key in ("top_cause", "confidence", "algorithm_version")
            },
            quality_evidence=_safe_items(
                quality_evidence,
                allowed_keys={
                    "evidence_id",
                    "text",
                    "source_table",
                    "source_id",
                    "reason_code",
                    "details",
                },
                max_items=10,
                max_chars=max_chars,
            ),
            drift_evidence=_safe_items(
                drift_evidence,
                allowed_keys={
                    "evidence_id",
                    "text",
                    "source_table",
                    "source_id",
                    "reason_code",
                    "column_name",
                    "method",
                    "metric",
                    "threshold",
                    "details",
                },
                max_items=10,
                max_chars=max_chars,
            ),
            lineage_impact=_safe_items(
                lineage_impact,
                allowed_keys={"key", "name", "node_type", "distance"},
                max_items=10,
                max_chars=max_chars,
            ),
            timeline=_safe_items(
                timeline,
                allowed_keys={"event", "message", "created_at"},
                max_items=20,
                max_chars=max_chars,
            ),
        )

    def evidence_ids(self) -> set[str]:
        return {
            str(item["evidence_id"])
            for item in [*self.quality_evidence, *self.drift_evidence]
            if item.get("evidence_id")
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident": self.incident,
            "deterministicRca": self.deterministic_rca,
            "qualityEvidence": self.quality_evidence,
            "driftEvidence": self.drift_evidence,
            "lineageImpact": self.lineage_impact,
            "timeline": self.timeline,
        }


@dataclass(frozen=True, slots=True)
class AIExplanation:
    summary: str
    probable_cause_explanation: str
    evidence_highlights: list[dict[str, str]]
    investigation_steps: list[str]
    uncertainties: list[str]

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
        *,
        allowed_evidence_ids: set[str],
    ) -> AIExplanation:
        required = {
            "summary",
            "probable_cause_explanation",
            "evidence_highlights",
            "investigation_steps",
            "uncertainties",
        }
        if not required.issubset(payload):
            raise ValueError("AI output is missing required fields")
        highlights = payload["evidence_highlights"]
        steps = payload["investigation_steps"]
        uncertainties = payload["uncertainties"]
        if (
            not isinstance(highlights, list)
            or not isinstance(steps, list)
            or not isinstance(uncertainties, list)
        ):
            raise ValueError("AI output arrays are invalid")
        normalized_highlights: list[dict[str, str]] = []
        for item in highlights[:10]:
            if not isinstance(item, Mapping) or not isinstance(item.get("evidence_id"), str):
                raise ValueError("AI evidence_highlights requires evidence_id")
            evidence_id = item["evidence_id"]
            if evidence_id not in allowed_evidence_ids:
                raise ValueError("AI output referenced unknown evidence_id")
            normalized_highlights.append(
                {"evidence_id": evidence_id, "text": sanitize_text(item.get("text"), max_chars=600)}
            )
        normalized_steps = [
            sanitize_text(item, max_chars=400) for item in steps[:8] if isinstance(item, str)
        ]
        normalized_uncertainties = [
            sanitize_text(item, max_chars=400)
            for item in uncertainties[:8]
            if isinstance(item, str)
        ]
        if not isinstance(payload["summary"], str) or not isinstance(
            payload["probable_cause_explanation"], str
        ):
            raise ValueError("AI output narrative fields are invalid")
        return cls(
            summary=sanitize_text(payload["summary"], max_chars=1000),
            probable_cause_explanation=sanitize_text(
                payload["probable_cause_explanation"], max_chars=1500
            ),
            evidence_highlights=normalized_highlights,
            investigation_steps=normalized_steps,
            uncertainties=normalized_uncertainties,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "probable_cause_explanation": self.probable_cause_explanation,
            "evidence_highlights": self.evidence_highlights,
            "investigation_steps": self.investigation_steps,
            "uncertainties": self.uncertainties,
        }
