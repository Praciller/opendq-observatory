import Link from "next/link";

import { Metric } from "../../components/metric";
import { PageHeader } from "../../components/page-header";
import { Section } from "../../components/section";
import { StatusBadge } from "../../components/status-badge";
import { getIncidents, type Incident } from "../../lib/incidents";

export const dynamic = "force-dynamic";

function incidentPriority(incident: Incident): number {
  return { OPEN: 0, ACKNOWLEDGED: 1, RESOLVED: 2 }[incident.status] ?? 3;
}

function orderedIncidents(incidents: Incident[]): Incident[] {
  return [...incidents].sort((left, right) => incidentPriority(left) - incidentPriority(right));
}

export default async function IncidentsPage() {
  const response = await getIncidents();
  const open = response.incidents.filter((incident) => incident.status === "OPEN").length;
  const acknowledged = response.incidents.filter((incident) => incident.status === "ACKNOWLEDGED").length;
  const resolved = response.incidents.filter((incident) => incident.status === "RESOLVED").length;

  return (
    <main className="shell" id="main-content">
      <PageHeader
        title="Incidents"
        description="Inspect deterministic interpretations of persisted quality and drift evidence. Active incidents lead the list; resolved history remains available for context."
        actions={<div className="page-actions"><Link className="secondary-link" href="/drift">Drift</Link><Link className="secondary-link" href="/lineage">Lineage</Link></div>}
        meta={<span className="page-meta">Read-only incident history</span>}
      />

      <div className="summary-strip page-summary" aria-label="Incident status summary">
        <Metric label="Open" value={open} detail="Needs investigation" tone={open > 0 ? "danger" : "success"} />
        <Metric label="Acknowledged" value={acknowledged} detail="Active, being tracked" tone={acknowledged > 0 ? "warning" : "neutral"} />
        <Metric label="Resolved" value={resolved} detail="Persisted history" tone="success" />
      </div>

      {response.incidents.length === 0 ? (
        <Section title="No incidents detected" description="An empty history is a valid result when persisted quality and drift evidence has not produced an incident.">
          <div className="empty-state empty-success"><StatusBadge status="RESOLVED" label="No active incident" /><strong>{response.message ?? "No incidents detected."}</strong><span>Continue with quality or drift evidence when you need to inspect the latest data state.</span></div>
        </Section>
      ) : (
        <Section title="Incident history" description="Severity, lifecycle state, dataset, rule, recency, and occurrence count are kept visible in every row.">
          <div className="table-wrap">
            <table className="data-table incident-table">
              <caption className="sr-only">OpenDQ incident history</caption>
              <thead><tr><th scope="col">Severity</th><th scope="col">Status</th><th scope="col">Dataset / rule</th><th scope="col">Last seen</th><th scope="col">Occurrences</th></tr></thead>
              <tbody>
                {orderedIncidents(response.incidents).map((incident) => (
                  <tr key={incident.id}>
                    <td data-label="Severity"><StatusBadge status={incident.severity} /></td>
                    <td data-label="Status"><StatusBadge status={incident.status} /></td>
                    <td data-label="Dataset / rule"><Link className="table-link" href={`/incidents/${incident.id}`}><strong>{incident.datasetName}</strong><span className="table-secondary">{incident.ruleName} · {incident.incidentKind.replace("_", " ")}</span></Link></td>
                    <td data-label="Last seen"><time dateTime={incident.lastSeenAt}>{new Date(incident.lastSeenAt).toLocaleString()}</time></td>
                    <td data-label="Occurrences"><strong>{incident.occurrenceCount.toLocaleString()}</strong></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}
    </main>
  );
}
