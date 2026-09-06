import Link from "next/link";

import { getIncidents, type Incident } from "../../lib/incidents";

export const dynamic = "force-dynamic";

function IncidentPill({ incident }: { incident: Incident }) {
  return <span className={`status-pill incident-${incident.status.toLowerCase()}`}>{incident.status}</span>;
}

export default async function IncidentsPage() {
  const response = await getIncidents();
  return (
    <main className="shell">
      <header className="hero quality-hero">
        <p className="eyebrow">Phase 3 · Incident Detection</p>
        <h1>Incident history</h1>
        <p className="intro">Stateful interpretations of persisted quality and drift evidence. Incidents are deterministic, lineage-aware, and read-only here.</p>
        <nav className="page-nav"><Link className="text-link" href="/">← System status</Link><Link className="text-link" href="/drift">View drift →</Link><Link className="text-link" href="/lineage">View lineage →</Link></nav>
      </header>
      {response.incidents.length === 0 ? (
        <section className="panel empty-state">
          <strong>{response.message ?? "No incidents detected"}</strong>
          <span>Healthy production data may legitimately produce an empty incident history.</span>
        </section>
      ) : (
        <section className="incident-list">
          {response.incidents.map((incident) => (
            <article className="panel incident-row" key={incident.id}>
              <div className="incident-row-heading">
                <div>
                  <p className="eyebrow">{incident.severity} · {incident.incidentKind.replace("_", " ")}</p>
                  <h2><Link className="plain-link" href={`/incidents/${incident.id}`}>{incident.datasetName}</Link></h2>
                  <p className="muted">{incident.ruleName} · {incident.ruleSlug}</p>
                </div>
                <IncidentPill incident={incident} />
              </div>
              <p>{incident.summary}</p>
              <div className="incident-meta"><span>Opened {new Date(incident.openedAt).toLocaleString()}</span><span>Last seen {new Date(incident.lastSeenAt).toLocaleString()}</span><span>{incident.occurrenceCount} occurrence{incident.occurrenceCount === 1 ? "" : "s"}</span></div>
            </article>
          ))}
        </section>
      )}
    </main>
  );
}
