"""Reproducible local-only SQL plan probe; all fixture rows are rolled back.

Run with APP_ENV=test and SQL_PLAN_DATABASE_URL pointing to the dedicated local
opendq_sqlperf_* PostgreSQL database. Never run on production or a shared DB.
"""

from __future__ import annotations

import json
import os
import platform
from datetime import UTC, datetime
from urllib.parse import urlparse

import psycopg


def guarded_database_url() -> str:
    url = os.getenv("SQL_PLAN_DATABASE_URL", "")
    parsed = urlparse(url)
    if (
        os.getenv("APP_ENV") != "test"
        or parsed.scheme not in {"postgres", "postgresql"}
        or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        or not parsed.path.lstrip("/").startswith("opendq_sqlperf_")
        or (os.getenv("DATABASE_URL") and url == os.getenv("DATABASE_URL"))
    ):
        raise ValueError(
            "SQL plan probe requires APP_ENV=test and a dedicated local opendq_sqlperf_* DB"
        )
    return url


def seed_fixture(cursor: psycopg.Cursor[object], *, rows: int = 16000) -> dict[str, int]:
    cursor.execute(
        """INSERT INTO sources(slug, name, base_url)
           VALUES ('sqlplan-local-source', 'SQL plan fixture', 'https://example.test')
           RETURNING id"""
    )
    source_id = int(cursor.fetchone()[0])
    dataset_ids = []
    for slug in ("sqlplan-hot", "sqlplan-cold"):
        cursor.execute(
            """INSERT INTO datasets(source_id, slug, name, schema_version)
               VALUES (%s, %s, %s, '1') RETURNING id""",
            (source_id, slug, slug),
        )
        dataset_ids.append(int(cursor.fetchone()[0]))
    hot, cold = dataset_ids

    cursor.execute(
        """INSERT INTO ingestion_runs(
               run_id, source_id, dataset_id, status, started_at, finished_at)
           SELECT gen_random_uuid(), %s,
                  CASE WHEN g %% 2 = 0 THEN %s ELSE %s END,
                  'SUCCESS',
                  '2026-01-01'::timestamptz + g * interval '1 minute',
                  '2026-01-01'::timestamptz + (g + 1) * interval '1 minute'
           FROM generate_series(1, %s) AS g""",
        (source_id, hot, cold, rows),
    )
    for dataset_id in (hot, cold):
        cursor.execute(
            """INSERT INTO raw_observations(
                   dataset_id, ingestion_run_id, observation_type, observed_at,
                   location_latitude, location_longitude, temperature_c, payload)
               SELECT %s, (SELECT run_id FROM ingestion_runs WHERE dataset_id = %s LIMIT 1),
                      'weather', '2026-01-01'::timestamptz + g * interval '1 minute',
                      13.7, 100.5, 20 + (g %% 9), '{}'::jsonb
               FROM generate_series(1, %s) AS g""",
            (dataset_id, dataset_id, rows // 2),
        )

    cursor.execute(
        """INSERT INTO quality_rules(dataset_id, slug, name, dimension, rule_type, severity)
           VALUES (%s, 'fixture-rule', 'Fixture rule', 'freshness', 'freshness', 'HIGH')
           RETURNING id""",
        (hot,),
    )
    rule_id = int(cursor.fetchone()[0])
    cursor.execute(
        """INSERT INTO incidents(
               id, incident_key, incident_kind, dataset_id, rule_id,
               status, severity, opened_at, last_seen_at, summary)
           SELECT gen_random_uuid(), 'fixture-' || g, 'DATA_QUALITY', %s, %s,
                  'RESOLVED', 'HIGH', '2026-01-01'::timestamptz,
                  '2026-01-02'::timestamptz, 'Fixture incident'
           FROM generate_series(1, %s) AS g""",
        (hot, rule_id, rows // 2),
    )
    cursor.execute(
        """INSERT INTO incidents(
               id, incident_key, incident_kind, dataset_id, rule_id,
               status, severity, opened_at, last_seen_at, summary)
           VALUES (gen_random_uuid(), 'fixture-active', 'DATA_QUALITY', %s, %s,
                   'OPEN', 'HIGH', '2026-01-03'::timestamptz,
                   '2026-01-03'::timestamptz, 'Fixture active')""",
        (hot, rule_id),
    )

    upstream = []
    for suffix in ("hot", "cold"):
        cursor.execute(
            """INSERT INTO lineage_nodes(key, name, node_type)
               VALUES (%s, %s, 'SOURCE') RETURNING id""",
            (f"sqlplan-source-{suffix}", f"Source {suffix}"),
        )
        upstream.append(int(cursor.fetchone()[0]))
    hot_node, cold_node = upstream
    cursor.execute(
        """INSERT INTO lineage_nodes(key, name, node_type)
           SELECT 'sqlplan-target-' || g, 'Target ' || g, 'API'
           FROM generate_series(1, %s) AS g""",
        (rows // 4,),
    )
    cursor.execute(
        """INSERT INTO lineage_edges(upstream_node_id, downstream_node_id, edge_type)
           SELECT CASE WHEN right(n.key, 2)::integer <= 20 THEN %s ELSE %s END,
                  n.id, 'FEEDS'
           FROM lineage_nodes n WHERE n.key LIKE 'sqlplan-target-%%'
              AND right(n.key, 2) ~ '^[0-9][0-9]$'""",
        (hot_node, cold_node),
    )
    # Statistics are updated only for this local fixture. All inserts are rolled back.
    cursor.execute(
        "ANALYZE ingestion_runs, raw_observations, incidents, lineage_nodes, lineage_edges"
    )
    return {"hot": hot, "cold": cold, "rule": rule_id, "upstream": hot_node}


def selected_queries(ids: dict[str, int]) -> dict[str, tuple[str, tuple[object, ...]]]:
    return {
        "rca_latest_ingestion": (
            """SELECT run_id, status, records_received, records_written, records_rejected,
                      error_code, error_message, finished_at
               FROM ingestion_runs WHERE dataset_id = %s
               ORDER BY started_at DESC LIMIT 1""",
            (ids["hot"],),
        ),
        "quality_observations": (
            """SELECT observation_type, observed_at, location_latitude, location_longitude,
                      source_event_id, temperature_c, relative_humidity_pct,
                      precipitation_mm, wind_speed_kmh, magnitude, depth_km, place
               FROM raw_observations WHERE dataset_id = %s ORDER BY observed_at""",
            (ids["hot"],),
        ),
        "drift_recent_observations": (
            """SELECT observed_at, temperature_c, ingestion_run_id
               FROM raw_observations
               WHERE dataset_id = %s AND temperature_c IS NOT NULL
               ORDER BY observed_at DESC LIMIT %s""",
            (ids["hot"], 100),
        ),
        "incident_active_reconciliation": (
            """SELECT id, status, severity, occurrence_count FROM incidents
               WHERE dataset_id = %s AND rule_id = %s
               AND status IN ('OPEN', 'ACKNOWLEDGED') FOR UPDATE""",
            (ids["hot"], ids["rule"]),
        ),
        "lineage_downstream": (
            """SELECT n.id, n.key, n.name, n.node_type, e.edge_type
               FROM lineage_edges e JOIN lineage_nodes n ON n.id = e.downstream_node_id
               WHERE e.upstream_node_id = %s AND n.active ORDER BY n.key, e.edge_type""",
            (ids["upstream"],),
        ),
    }


def summarize_plan(plan: dict[str, object]) -> dict[str, object]:
    indices: set[str] = set()
    scan_nodes: list[dict[str, object]] = []

    def walk(node: dict[str, object]) -> None:
        node_type = str(node["Node Type"])
        if "Index Name" in node:
            indices.add(str(node["Index Name"]))
        if "Scan" in node_type:
            loops = int(node.get("Actual Loops", 1))
            scan_nodes.append(
                {
                    "node": node_type,
                    "relation": node.get("Relation Name"),
                    "index": node.get("Index Name"),
                    "rows": int(node.get("Actual Rows", 0)) * loops,
                    "rowsFiltered": int(node.get("Rows Removed by Filter", 0)) * loops,
                }
            )
        for child in node.get("Plans", []):
            walk(child)

    walk(plan["Plan"])
    return {
        "executionMs": round(float(plan["Execution Time"]), 3),
        "planningMs": round(float(plan["Planning Time"]), 3),
        "topNode": plan["Plan"]["Node Type"],
        "indices": sorted(indices),
        "scans": scan_nodes,
        "plan": plan["Plan"],
    }


def main() -> None:
    url = guarded_database_url()
    connection = psycopg.connect(url)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW server_version")
            version = str(cursor.fetchone()[0])
            cursor.execute("SHOW max_parallel_workers_per_gather")
            parallel = str(cursor.fetchone()[0])
            ids = seed_fixture(cursor)
            results = {}
            for label, (query, params) in selected_queries(ids).items():
                cursor.execute(query, params)
                actual = cursor.fetchall()
                expected = {
                    "rca_latest_ingestion": 1,
                    "quality_observations": 8000,
                    "drift_recent_observations": 100,
                    "incident_active_reconciliation": 1,
                }
                if label in expected and len(actual) != expected[label]:
                    raise AssertionError(
                        f"{label}: got {len(actual)} rows, expected {expected[label]}"
                    )
                if label == "lineage_downstream" and not actual:
                    raise AssertionError("lineage downstream returned no rows")
                cursor.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + query, params)
                plan = cursor.fetchone()[0][0]
                results[label] = {"returnedRows": len(actual), **summarize_plan(plan)}
            print(
                json.dumps(
                    {
                        "capturedAt": datetime.now(UTC).isoformat(),
                        "scope": "dedicated-local-postgres-only",
                        "environment": {
                            "postgres": version,
                            "python": platform.python_version(),
                            "platform": platform.platform(),
                            "parallelWorkersPerGather": parallel,
                            "ingestionRuns": 16000,
                            "observations": 16000,
                            "resolvedIncidents": 8000,
                        },
                        "queries": results,
                    },
                    default=str,
                    indent=2,
                )
            )
    finally:
        connection.rollback()  # No fixture data survives, even when EXPLAIN fails.
        connection.close()


if __name__ == "__main__":
    main()
