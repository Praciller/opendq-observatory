"""Transparent root-cause ranking; this module makes no causal certainty claim."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class EvidenceSignal:
    evidence_type: str
    cause: str
    weight: float
    reason_code: str
    details: dict[str, Any] = field(default_factory=dict)
    reference: str | None = None


@dataclass(frozen=True, slots=True)
class RankedCause:
    cause: str
    score: float
    rank: int
    confidence: str
    evidence: tuple[EvidenceSignal, ...]


def _confidence(score: float, runner_up: float | None) -> str:
    if score <= 0:
        return "UNKNOWN"
    if score >= 10 and (runner_up is None or score > runner_up):
        return "HIGH"
    if score >= 5:
        return "MEDIUM"
    return "LOW"


def rank_root_causes(signals: list[EvidenceSignal]) -> list[RankedCause]:
    grouped: dict[str, list[EvidenceSignal]] = defaultdict(list)
    for signal in signals:
        grouped[signal.cause].append(signal)
    if not grouped:
        return [RankedCause("UNKNOWN", 0, 1, "UNKNOWN", ())]
    scores = sorted(
        (
            (cause, sum(signal.weight for signal in cause_signals))
            for cause, cause_signals in grouped.items()
        ),
        key=lambda item: (-item[1], item[0]),
    )
    ranked: list[RankedCause] = []
    for index, (cause, score) in enumerate(scores):
        runner_up = scores[index + 1][1] if index + 1 < len(scores) else None
        ranked.append(
            RankedCause(
                cause=cause,
                score=score,
                rank=index + 1,
                confidence=_confidence(score, runner_up),
                evidence=tuple(
                    sorted(
                        grouped[cause],
                        key=lambda signal: (
                            -signal.weight,
                            signal.reason_code,
                            signal.reference or "",
                        ),
                    )
                ),
            )
        )
    return ranked
