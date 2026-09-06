from opendq.drift.engine import (
    DriftStatus,
    categorical_tvd,
    compare_schema,
    evaluate_numeric_drift,
    location_shift,
)


def test_numeric_stable_fixture_has_negligible_psi() -> None:
    result = evaluate_numeric_drift(
        baseline=[10, 11, 12, 13, 14, 15, 16, 17],
        current=[10, 11, 12, 13, 14, 15, 16, 17],
        threshold=0.20,
    )

    assert result.status is DriftStatus.STABLE
    assert result.metric < 0.01


def test_numeric_distribution_shift_is_drift() -> None:
    result = evaluate_numeric_drift(
        baseline=[10, 11, 12, 13, 14, 15, 16, 17],
        current=[40, 41, 42, 43, 44, 45, 46, 47],
        threshold=0.20,
    )

    assert result.status is DriftStatus.DRIFT
    assert result.metric >= result.threshold
    assert result.details["baseline_distribution"]
    assert result.details["current_distribution"]


def test_numeric_moderate_shift_is_warning() -> None:
    result = evaluate_numeric_drift(
        baseline=list(range(100)),
        current=list(range(7, 107)),
        threshold=0.20,
    )

    assert result.status is DriftStatus.WARN


def test_numeric_zero_bins_are_finite() -> None:
    result = evaluate_numeric_drift(
        baseline=[0, 0, 0, 0, 1, 1, 1, 1],
        current=[0, 0, 0, 0, 0, 0, 0, 0],
        threshold=0.20,
    )

    assert result.metric == result.metric
    assert result.details["epsilon"] > 0


def test_numeric_sample_validation_is_explicit() -> None:
    result = evaluate_numeric_drift(
        baseline=[1, 2], current=[3, 4], threshold=0.20, minimum_samples=5
    )

    assert result.status is DriftStatus.SKIPPED
    assert result.details["reason"] == "INSUFFICIENT_BASELINE"


def test_location_shift_is_normalized_and_explainable() -> None:
    shift = location_shift([10, 11, 12, 13, 14], [12, 13, 14, 15, 16])

    assert shift["baseline_median"] == 12
    assert shift["current_median"] == 14
    assert shift["median_shift"] == 2


def test_categorical_tvd_detects_distribution_change() -> None:
    assert categorical_tvd(["a", "a", "b"], ["a", "b", "b"]) == 1 / 3
    assert categorical_tvd(["a", "b"], ["a", "b"]) == 0


def test_schema_diff_reports_add_remove_and_type_change() -> None:
    differences = compare_schema(
        {"a": {"type": "number", "nullable": False}, "b": {"type": "string"}},
        {"a": {"type": "string", "nullable": False}, "c": {"type": "boolean"}},
    )

    assert {item["kind"] for item in differences} == {"TYPE_CHANGED", "REMOVED", "ADDED"}
