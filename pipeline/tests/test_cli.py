from uuid import uuid4

from opendq.__main__ import exit_code_for_results
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
