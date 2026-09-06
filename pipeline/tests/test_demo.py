from datetime import UTC, datetime, timedelta

import pytest
from opendq.demo import demo_timeline, validate_demo_environment


def test_demo_requires_explicit_non_production_database() -> None:
    assert (
        validate_demo_environment(
            app_env="demo",
            demo_database_url="postgresql://opendq:opendq@localhost:5432/opendq_demo",
            production_database_url="postgresql://opendq:opendq@localhost:5432/opendq",
        )
        == "postgresql://opendq:opendq@localhost:5432/opendq_demo"
    )


def test_demo_recovery_fills_the_only_temporal_gap() -> None:
    timeline = demo_timeline(datetime(2026, 9, 6, tzinfo=UTC))

    assert timeline.baseline_start + timedelta(hours=100) == timeline.repair_gap
    assert timeline.failure_start + timedelta(hours=100) == timeline.recovery_start


@pytest.mark.parametrize(
    ("app_env", "demo_url", "production_url"),
    [
        ("development", "postgresql://opendq:opendq@localhost:5432/opendq_demo", None),
        ("demo", None, None),
        (
            "demo",
            "postgresql://opendq:opendq@localhost:5432/opendq",
            "postgresql://opendq:opendq@localhost:5432/opendq",
        ),
        ("demo", "postgresql://opendq:opendq@ep-example.neon.tech/demo", None),
    ],
)
def test_demo_refuses_unsafe_environment(app_env, demo_url, production_url) -> None:
    with pytest.raises(ValueError, match="demo"):
        validate_demo_environment(
            app_env=app_env,
            demo_database_url=demo_url,
            production_database_url=production_url,
        )
