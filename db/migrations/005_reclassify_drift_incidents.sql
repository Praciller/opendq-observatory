WITH drift_repair AS (
    SELECT incident.id AS incident_id, drift.id AS drift_result_id,
           drift.evaluation_run_id
    FROM incidents AS incident
    JOIN quality_rules AS rule ON rule.id = incident.rule_id
    JOIN LATERAL (
        SELECT result.id, result.evaluation_run_id
        FROM drift_results AS result
        WHERE result.dataset_id = incident.dataset_id
          AND result.column_name = split_part(rule.slug, ':', 2)
          AND result.method = upper(split_part(rule.slug, ':', 3))
        ORDER BY result.evaluated_at DESC, result.id DESC
        LIMIT 1
    ) AS drift ON TRUE
    WHERE rule.dimension = 'drift'
      AND incident.incident_kind <> 'DATA_DRIFT'
)
UPDATE incidents AS incident
SET incident_kind = 'DATA_DRIFT',
    first_evaluation_run_id = NULL,
    latest_evaluation_run_id = NULL,
    first_quality_result_id = NULL,
    latest_quality_result_id = NULL,
    first_drift_evaluation_run_id = repair.evaluation_run_id,
    latest_drift_evaluation_run_id = repair.evaluation_run_id,
    first_drift_result_id = repair.drift_result_id,
    latest_drift_result_id = repair.drift_result_id
FROM drift_repair AS repair
WHERE incident.id = repair.incident_id;
