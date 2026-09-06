import Link from "next/link";

import { getIncident } from "../../../lib/incidents";
import { getRca } from "../../../lib/rca";

export const dynamic = "force-dynamic";

export default async function IncidentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const response = await getIncident(id);
  const rcaResponse = await getRca(id);
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
          <section className="panel" aria-labelledby="rca-heading">
            <div className="section-heading"><div><p className="eyebrow">Evidence ranking</p><h2 id="rca-heading">Deterministic Root Cause Analysis</h2></div><span className="count-label">No AI inference</span></div>
            {!rcaResponse.analysis ? <div className="empty-state"><strong>{rcaResponse.message ?? "No RCA analysis is available."}</strong><span>Analysis is created when an incident is opened or meaningfully updated.</span></div> : <div className="rca-content"><div className="rca-summary"><strong>{rcaResponse.analysis.topCause.replaceAll("_", " ")}</strong><span className={`status-pill rca-${rcaResponse.analysis.confidence.toLowerCase()}`}>{rcaResponse.analysis.confidence} confidence</span><p className="muted">{rcaResponse.analysis.summary}</p></div><div className="rca-candidates">{(rcaResponse.analysis.details.candidates as Array<{cause: string; score: number; rank: number; confidence: string}> | undefined)?.map((candidate) => <div className="rca-candidate" key={candidate.cause}><span><strong>#{candidate.rank} {candidate.cause.replaceAll("_", " ")}</strong><small>{candidate.confidence} · score {candidate.score}</small></span></div>)}</div><div className="event-list">{rcaResponse.analysis.evidence.map((evidence, index) => <div className="event-row" key={`${evidence.reasonCode}-${index}`}><div><strong>{evidence.reasonCode.replaceAll("_", " ")}</strong><span className="muted">{evidence.evidenceType} · weight {evidence.weight}</span></div><span className="muted">{evidence.sourceTable}</span></div>)}</div><p className="muted">Algorithm {rcaResponse.analysis.algorithmVersion} · fingerprint {rcaResponse.analysis.evidenceFingerprint.slice(0, 12)}…</p></div>}
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
