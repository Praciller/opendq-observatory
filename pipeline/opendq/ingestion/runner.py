"""Run one or all source adapters with explicit terminal states."""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from dataclasses import replace
from time import perf_counter

from opendq.errors import ErrorCode, IngestionError
from opendq.ingestion.results import IngestionResult
from opendq.logging import log_event
from opendq.quality.engine import evaluate_dataset
from opendq.sources.base import SourceAdapter
from opendq.storage.repository import Repository

LOGGER = logging.getLogger("opendq.ingestion")
_SECRET_URL = re.compile(r"(postgres(?:ql)?://)([^/@\s]+)@", re.IGNORECASE)


def _sanitize(message: str) -> str:
    return _SECRET_URL.sub(r"\1<redacted>@", message)[:500]


async def run_source(repository: Repository, adapter: SourceAdapter) -> IngestionResult:
    source_id, dataset_id = repository.ensure_source_dataset(
        source_slug=adapter.source_slug,
        source_name=adapter.source_name,
        description=adapter.description,
        base_url=adapter.base_url,
        dataset_slug=adapter.dataset_slug,
        dataset_name=adapter.dataset_name,
        schema_version="1",
    )
    run_id = repository.create_ingestion_run(source_id, dataset_id)
    started = perf_counter()
    try:
        payload = await adapter.fetch()
        normalized = adapter.normalize(payload)
        received = len(normalized.records) + normalized.rejected
        written = repository.upsert_observations(dataset_id, run_id, normalized.records)
        status = "PARTIAL" if normalized.rejected else ("NO_CHANGE" if written == 0 else "SUCCESS")
        repository.finish_ingestion_run(
            run_id,
            status=status,
            records_received=received,
            records_written=written,
            records_rejected=normalized.rejected,
            metadata={"duration_ms": round((perf_counter() - started) * 1000, 2)},
        )
        result = IngestionResult(
            source_slug=adapter.source_slug,
            status=status,
            run_id=run_id,
            records_received=received,
            records_written=written,
            records_rejected=normalized.rejected,
        )
    except IngestionError as exc:
        message = _sanitize(str(exc))
        repository.finish_ingestion_run(
            run_id,
            status="FAILED",
            records_received=0,
            records_written=0,
            records_rejected=0,
            error_code=exc.code.value,
            error_message=message,
        )
        result = IngestionResult(
            source_slug=adapter.source_slug,
            status="FAILED",
            run_id=run_id,
            error_code=exc.code.value,
            error_message=message,
        )
    except Exception as exc:
        message = _sanitize(str(exc)) or "unexpected ingestion failure"
        try:
            repository.finish_ingestion_run(
                run_id,
                status="FAILED",
                records_received=0,
                records_written=0,
                records_rejected=0,
                error_code=ErrorCode.DATABASE_ERROR.value,
                error_message=message,
            )
        except Exception:
            raise
        result = IngestionResult(
            source_slug=adapter.source_slug,
            status="FAILED",
            run_id=run_id,
            error_code=ErrorCode.DATABASE_ERROR.value,
            error_message=message,
        )
    if result.status in {"SUCCESS", "NO_CHANGE"}:
        try:
            quality = evaluate_dataset(
                repository,
                adapter.dataset_slug,
                triggered_by=f"ingestion:{result.run_id}",
            )
            result = replace(
                result,
                quality_evaluation_run_id=quality.evaluation_run_id,
                quality_status=quality.status,
                quality_score=quality.score,
            )
        except Exception:
            LOGGER.exception(
                "quality evaluation failed after ingestion",
                extra={"dataset": adapter.dataset_slug, "ingestion_run_id": str(result.run_id)},
            )
            result = replace(result, quality_error="QUALITY_EVALUATION_ERROR")
    log_event(
        LOGGER,
        run_id=str(result.run_id) if result.run_id else None,
        source=result.source_slug,
        event="ingestion_complete",
        status=result.status,
        records_received=result.records_received,
        records_written=result.records_written,
        duration_ms=round((perf_counter() - started) * 1000, 2),
        error_type=result.error_code,
    )
    return result


async def run_all(
    repository: Repository, adapters: Sequence[SourceAdapter]
) -> list[IngestionResult]:
    results: list[IngestionResult] = []
    for adapter in adapters:
        results.append(await run_source(repository, adapter))
    return results
