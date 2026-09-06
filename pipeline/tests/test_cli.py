from uuid import uuid4

from opendq.__main__ import build_parser, exit_code_for_results
from opendq.ingestion.results import IngestionResult


def test_cli_treats_no_change_as_success() -> None:
    result = IngestionResult("open-meteo", "NO_CHANGE", uuid4())

    assert exit_code_for_results([result]) == 0


def test_cli_reports_failure_with_nonzero_exit_code() -> None:
    results = [
        IngestionResult("open-meteo", "SUCCESS", uuid4()),
        IngestionResult("usgs-earthquakes", "FAILED", uuid4(), error_code="SOURCE_TIMEOUT"),
    ]

    assert exit_code_for_results(results) != 0


def test_cli_exposes_quality_evaluation_for_all_datasets() -> None:
    args = build_parser().parse_args(["quality", "evaluate", "all"])

    assert args.command == "quality"
    assert args.quality_command == "evaluate"
    assert args.dataset == "all"


def test_cli_exposes_read_only_incident_and_lineage_commands() -> None:
    incident = build_parser().parse_args(["incident", "list", "--status", "open"])
    lineage = build_parser().parse_args(["lineage", "impact", "open-meteo"])

    assert (incident.command, incident.incident_command, incident.status) == (
        "incident",
        "list",
        "open",
    )
    assert (lineage.command, lineage.lineage_command, lineage.dataset) == (
        "lineage",
        "impact",
        "open-meteo",
    )


def test_cli_exposes_trusted_lineage_seed() -> None:
    args = build_parser().parse_args(["lineage", "seed"])

    assert (args.command, args.lineage_command) == ("lineage", "seed")


def test_cli_exposes_drift_and_rca_commands() -> None:
    drift = build_parser().parse_args(["drift", "evaluate", "open-meteo"])
    baseline = build_parser().parse_args(["drift", "baseline", "create", "usgs"])
    rca = build_parser().parse_args(["rca", "show", "incident-id"])

    assert (drift.command, drift.drift_command, drift.dataset) == (
        "drift",
        "evaluate",
        "open-meteo",
    )
    assert (baseline.command, baseline.drift_command, baseline.baseline_command) == (
        "drift",
        "baseline",
        "create",
    )
    assert (rca.command, rca.rca_command, rca.incident_id) == ("rca", "show", "incident-id")
