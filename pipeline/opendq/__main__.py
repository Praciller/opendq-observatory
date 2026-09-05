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
from opendq.incidents.repository import IncidentRepository
from opendq.ingestion.results import IngestionResult
from opendq.ingestion.runner import run_all, run_source
from opendq.lineage.repository import LineageRepository
from opendq.lineage.seed import seed_lineage
from opendq.lineage.traversal import downstream_blast_radius
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
    incident = commands.add_parser("incident", help="inspect and acknowledge incidents")
    incident_commands = incident.add_subparsers(dest="incident_command", required=True)
    incident_list = incident_commands.add_parser("list", help="list incidents")
    incident_list.add_argument("--status", choices=("open", "acknowledged", "resolved"))
    incident_list.add_argument("--dataset")
    incident_list.add_argument("--severity", choices=("info", "warning", "high", "critical"))
    incident_show = incident_commands.add_parser("show", help="show one incident")
    incident_show.add_argument("incident_id")
    incident_ack = incident_commands.add_parser("acknowledge", help="acknowledge one incident")
    incident_ack.add_argument("incident_id")
    lineage = commands.add_parser("lineage", help="inspect deterministic lineage")
    lineage_commands = lineage.add_subparsers(dest="lineage_command", required=True)
    lineage_show = lineage_commands.add_parser("show", help="show dataset lineage")
    lineage_show.add_argument("dataset")
    lineage_impact = lineage_commands.add_parser("impact", help="show downstream blast radius")
    lineage_impact.add_argument("dataset")
    lineage_commands.add_parser("seed", help="seed implemented lineage idempotently")
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


def _incident(settings: Settings, command: str, args: argparse.Namespace) -> int:
    with psycopg.connect(settings.database_url) as connection:
        repository = IncidentRepository(connection)
        if command == "list":
            payload = {
                "incidents": repository.list_incidents(
                    status=args.status,
                    dataset=args.dataset,
                    severity=args.severity,
                )
            }
        elif command == "show":
            payload = repository.get_incident(args.incident_id)
        else:
            payload = repository.acknowledge(args.incident_id)
    print(json.dumps(payload, sort_keys=True, default=str))
    return 0


def _dataset_slug(value: str) -> str:
    return {
        "open-meteo": "hourly-weather",
        "usgs": "earthquake-events",
        "usgs-earthquakes": "earthquake-events",
    }.get(value, value)


def _lineage(settings: Settings, command: str, dataset: str) -> int:
    with psycopg.connect(settings.database_url) as connection:
        if command == "seed":
            print(json.dumps(seed_lineage(connection), sort_keys=True))
            return 0
        dataset_slug = _dataset_slug(dataset)
        repository = LineageRepository(connection)
        if command == "impact":
            payload = {
                "dataset": dataset_slug,
                "impact": downstream_blast_radius(repository, f"dataset:{dataset_slug}"),
            }
        else:
            dataset_id = repository.dataset_id_for_slug(dataset_slug)
            source_key = (
                "source:usgs" if dataset_slug == "earthquake-events" else "source:open-meteo"
            )
            nodes = repository.nodes_for_dataset(dataset_id, source_key=source_key)
            payload = {
                "dataset": dataset_slug,
                "nodes": nodes,
                "edges": repository.edges_for_nodes([int(node["id"]) for node in nodes]),
            }
    print(json.dumps(payload, sort_keys=True, default=str))
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
        if args.command == "incident":
            return _incident(settings, args.incident_command, args)
        if args.command == "lineage":
            return _lineage(settings, args.lineage_command, getattr(args, "dataset", ""))
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
