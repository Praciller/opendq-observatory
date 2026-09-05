import Link from "next/link";

import { getIncident } from "../../../lib/incidents";

export const dynamic = "force-dynamic";

export default async function IncidentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const response = await getIncident(id);
  const incident = response.incident;
  return (
    <main className="shell">
      <header className="hero quality-hero">
        <p className="eyebrow">Deterministic Evidence</p>
        <h1>Incident detail</h1>
        <Link className="text-link" href="/incidents">← Back to incidents</Link>
      </header>
      {!incident ? (
        <section className="panel empty-state"><strong>{response.message ?? "Incident not found."}</strong></section>
      ) : (
        <>
          <section className="panel incident-detail-heading">
            <div><p className="eyebrow">{incident.severity} · {incident.incidentKind.replace("_", " ")}</p><h2>{incident.datasetName} · {incident.ruleName}</h2><p className="muted">{incident.summary}</p></div>
            <span className={`status-pill incident-${incident.status.toLowerCase()}`}>{incident.status}</span>
          </section>
          <section className="panel">
            <div className="section-heading"><h2>Evidence</h2><span className="count-label">{incident.occurrenceCount} occurrence{incident.occurrenceCount === 1 ? "" : "s"}</span></div>
            <pre className="evidence-block">{JSON.stringify(incident.evidence, null, 2)}</pre>
          </section>
          <section className="panel">
            <div className="section-heading"><h2>Lifecycle</h2><span className="count-label">{incident.events.length} events</span></div>
            <div className="event-list">{incident.events.map((event) => <article className="event-row" key={event.id}><div><strong>{event.eventType}</strong><span className="muted">{event.message}</span></div><time>{new Date(event.createdAt).toLocaleString()}</time></article>)}</div>
          </section>
          <section className="panel">
            <div className="section-heading"><h2>Blast radius</h2><span className="count-label">{incident.impacts.length} affected assets</span></div>
            {incident.impacts.length === 0 ? <div className="empty-state"><span>No downstream lineage snapshot was available.</span></div> : <div className="impact-list">{incident.impacts.map((impact) => <div className="impact-row" key={impact.lineageNodeId}><strong>{impact.name}</strong><span className="muted">{impact.nodeType} · distance {impact.distance}</span></div>)}</div>}
          </section>
        </>
      )}
    </main>
  );
}
