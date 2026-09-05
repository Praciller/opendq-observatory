"""Adapter protocol and normalized result container."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    records: list[Mapping[str, Any]]
    rejected: int


class SourceAdapter(Protocol):
    source_slug: str
    dataset_slug: str
    source_name: str
    dataset_name: str
    description: str
    base_url: str

    async def fetch(self) -> dict[str, Any]: ...

    def normalize(self, payload: Mapping[str, Any]) -> NormalizationResult: ...
