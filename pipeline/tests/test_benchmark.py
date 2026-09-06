from opendq.benchmark import summarize_samples


def test_benchmark_summary_reports_median_and_range() -> None:
    summary = summarize_samples([1.0, 5.0, 3.0, 7.0, 2.0])

    assert summary == {"runs": 5, "medianMs": 3.0, "minMs": 1.0, "maxMs": 7.0}


def test_empty_benchmark_summary_is_explicit() -> None:
    assert summarize_samples([]) == {"runs": 0, "medianMs": None, "minMs": None, "maxMs": None}
