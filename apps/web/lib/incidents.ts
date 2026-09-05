import { queryValues } from "./db";

export type IncidentStatus = "OPEN" | "ACKNOWLEDGED" | "RESOLVED";
export type IncidentSeverity = "INFO" | "WARNING" | "HIGH" | "CRITICAL";

export type Incident = {
  id: string;
  incidentKey: string;
  incidentKind: "DATA_QUALITY" | "EVALUATION_ERROR";
  datasetSlug: string;
  datasetName: string;
  ruleSlug: string;
  ruleName: string;
  status: IncidentStatus;
  severity: IncidentSeverity;
  openedAt: string;
  lastSeenAt: string;
  resolvedAt: string | null;
  acknowledgedAt: string | null;
  occurrenceCount: number;
  summary: string;
  evidence: Record<string, unknown>;
};

export type IncidentEvent = {
  id: number;
  eventType: string;
  fromStatus: string | null;
  toStatus: string;
  severity: IncidentSeverity;
  message: string;
  details: Record<string, unknown>;
  createdAt: string;
};

export type IncidentImpact = {
  lineageNodeId: number;
  key: string;
  name: string;
  nodeType: string;
  distance: number;
  path: string[];
  capturedAt: string;
};

export type IncidentDetail = Incident & { events: IncidentEvent[]; impacts: IncidentImpact[] };
export type IncidentsResponse = { incidents: Incident[]; message?: string };
export type IncidentDetailResponse = { incident: IncidentDetail | null; message?: string };

type IncidentRow = {
  id: string;
  incident_key: string;
  incident_kind: Incident["incidentKind"];
  dataset_slug: string;
  dataset_name: string;
  rule_slug: string;
  rule_name: string;
  status: IncidentStatus;
  severity: IncidentSeverity;
  opened_at: Date;
  last_seen_at: Date;
  resolved_at: Date | null;
  acknowledged_at?: Date | null;
  occurrence_count: number;
  summary: string;
  evidence_json: Record<string, unknown>;
};

function dateValue(value: Date | string | null): string | null {
  return value ? new Date(value).toISOString() : null;
}

export function incidentEmptyState(): IncidentsResponse {
  return { incidents: [], message: "No incidents detected." };
}

export function mapIncidentRow(row: IncidentRow): Incident {
  return {
    id: row.id,
    incidentKey: row.incident_key,
    incidentKind: row.incident_kind,
    datasetSlug: row.dataset_slug,
    datasetName: row.dataset_name,
    ruleSlug: row.rule_slug,
    ruleName: row.rule_name,
    status: row.status,
    severity: row.severity,
    openedAt: dateValue(row.opened_at) as string,
    lastSeenAt: dateValue(row.last_seen_at) as string,
    resolvedAt: dateValue(row.resolved_at),
    acknowledgedAt: dateValue(row.acknowledged_at ?? null),
    occurrenceCount: row.occurrence_count,
    summary: row.summary,
    evidence: row.evidence_json,
  };
}

export async function getIncidents(filters: {
  status?: string;
  dataset?: string;
  severity?: string;
} = {}): Promise<IncidentsResponse> {
  try {
    const rows = await queryValues<IncidentRow>(
      `SELECT incident.id, incident.incident_key, incident.incident_kind,
              d.slug AS dataset_slug, d.name AS dataset_name,
              rule.slug AS rule_slug, rule.name AS rule_name,
              incident.status, incident.severity, incident.opened_at,
              incident.last_seen_at, incident.resolved_at, incident.acknowledged_at,
              incident.occurrence_count, incident.summary, incident.evidence_json
       FROM incidents incident
       JOIN datasets d ON d.id = incident.dataset_id
       JOIN quality_rules rule ON rule.id = incident.rule_id
       WHERE ($1::text IS NULL OR incident.status = $1)
         AND ($2::text IS NULL OR d.slug = $2)
         AND ($3::text IS NULL OR incident.severity = $3)
       ORDER BY incident.opened_at DESC, incident.id DESC
       LIMIT 100`,
      [filters.status?.toUpperCase() ?? null, filters.dataset ?? null, filters.severity?.toUpperCase() ?? null],
    );
    return { incidents: rows.map(mapIncidentRow) };
  } catch {
    return { incidents: [], message: "Incident data is unavailable." };
  }
}

export async function getIncident(id: string): Promise<IncidentDetailResponse> {
  if (!/^[0-9a-f-]{36}$/i.test(id)) return { incident: null, message: "Incident not found." };
  try {
    const rows = await queryValues<IncidentRow>(
      `SELECT incident.id, incident.incident_key, incident.incident_kind,
              d.slug AS dataset_slug, d.name AS dataset_name,
              rule.slug AS rule_slug, rule.name AS rule_name,
              incident.status, incident.severity, incident.opened_at,
              incident.last_seen_at, incident.resolved_at, incident.acknowledged_at,
              incident.occurrence_count, incident.summary, incident.evidence_json
       FROM incidents incident
       JOIN datasets d ON d.id = incident.dataset_id
       JOIN quality_rules rule ON rule.id = incident.rule_id
       WHERE incident.id = $1::uuid`,
      [id],
    );
    if (rows.length === 0) return { incident: null, message: "Incident not found." };
    const events = await queryValues<{
      id: number; event_type: string; from_status: string | null; to_status: string;
      severity: IncidentSeverity; message: string; details_json: Record<string, unknown>; created_at: Date;
    }>(
      `SELECT id, event_type, from_status, to_status, severity, message, details_json, created_at
       FROM incident_events WHERE incident_id = $1::uuid ORDER BY id`,
      [id],
    );
    const impacts = await queryValues<{
      lineage_node_id: number; key: string; name: string; node_type: string;
      distance: number; path_json: string[]; captured_at: Date;
    }>(
      `SELECT impact.lineage_node_id, node.key, node.name, node.node_type,
              impact.distance, impact.path_json, impact.captured_at
       FROM incident_impacts impact
       JOIN lineage_nodes node ON node.id = impact.lineage_node_id
       WHERE impact.incident_id = $1::uuid
       ORDER BY impact.distance, node.key`,
      [id],
    );
    return {
      incident: {
        ...mapIncidentRow(rows[0]),
        events: events.map((event) => ({
          id: event.id,
          eventType: event.event_type,
          fromStatus: event.from_status,
          toStatus: event.to_status,
          severity: event.severity,
          message: event.message,
          details: event.details_json,
          createdAt: dateValue(event.created_at) as string,
        })),
        impacts: impacts.map((impact) => ({
          lineageNodeId: impact.lineage_node_id,
          key: impact.key,
          name: impact.name,
          nodeType: impact.node_type,
          distance: impact.distance,
          path: impact.path_json,
          capturedAt: dateValue(impact.captured_at) as string,
        })),
      },
    };
  } catch {
    return { incident: null, message: "Incident data is unavailable." };
  }
}
