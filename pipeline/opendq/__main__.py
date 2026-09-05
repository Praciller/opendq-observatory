"""Command-line entry point for migrations and public source ingestion."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence

import httpx
import psycopg

from opendq.config import Settings
from opendq.ingestion.results import IngestionResult
from opendq.ingestion.runner import run_all, run_source
from opendq.logging import configure_logging
from opendq.quality.engine import evaluate_dataset
from opendq.sources.open_meteo import OpenMeteoAdapter
from opendq.sources.usgs import USGSAdapter
from opendq.storage.migrations import apply_migrations
from opendq.storage.repository import Repository


def exit_code_for_results(results: Sequence[IngestionResult]) -> int:
    return 1 if any(result.exit_code != 0 for result in results) else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="opendq")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("migrate", help="apply pending SQL migrations")
    ingest = commands.add_parser("ingest", help="ingest one or all public sources")
    ingest.add_argument("source", choices=("open-meteo", "usgs", "all"))
    quality = commands.add_parser("quality", help="evaluate deterministic data quality")
    quality_commands = quality.add_subparsers(dest="quality_command", required=True)
    evaluate = quality_commands.add_parser("evaluate", help="evaluate one or all datasets")
    evaluate.add_argument("dataset", choices=("open-meteo", "usgs", "all"))
    return parser


def _adapters(
    settings: Settings, client: httpx.AsyncClient
) -> list[OpenMeteoAdapter | USGSAdapter]:
    return [
        OpenMeteoAdapter(client=client, base_url=settings.open_meteo_base_url),
        USGSAdapter(client=client, base_url=settings.usgs_base_url),
    ]


async def _ingest(settings: Settings, source: str) -> int:
    with psycopg.connect(settings.database_url) as connection:
        repository = Repository(connection)
        async with httpx.AsyncClient() as client:
            adapters = _adapters(settings, client)
            if source == "all":
                results = await run_all(repository, adapters)
            else:
                selected = next(
                    adapter
                    for adapter in adapters
                    if adapter.source_slug == ("usgs-earthquakes" if source == "usgs" else source)
                )
                results = [await run_source(repository, selected)]
    for result in results:
        print(json.dumps(result.as_dict(), sort_keys=True, default=str))
    return exit_code_for_results(results)


def _quality(settings: Settings, dataset: str) -> int:
    dataset_slugs = {
        "open-meteo": "hourly-weather",
        "usgs": "earthquake-events",
    }
    selected = tuple(dataset_slugs.values()) if dataset == "all" else (dataset_slugs[dataset],)
    with psycopg.connect(settings.database_url) as connection:
        repository = Repository(connection)
        summaries = [evaluate_dataset(repository, slug, triggered_by="cli") for slug in selected]
    for summary in summaries:
        print(json.dumps(summary.as_dict(), sort_keys=True, default=str))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = Settings.from_env()
        configure_logging(settings.log_level)
        if args.command == "migrate":
            with psycopg.connect(settings.database_url) as connection:
                applied = apply_migrations(connection)
            print(json.dumps({"applied": applied}))
            return 0
        if args.command == "quality":
            return _quality(settings, args.dataset)
        return asyncio.run(_ingest(settings, args.source))
    except (ValueError, psycopg.Error) as exc:
        print(
            json.dumps({"status": "FAILED", "error_code": "CONFIGURATION_OR_DATABASE_ERROR"}),
            file=sys.stderr,
        )
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
