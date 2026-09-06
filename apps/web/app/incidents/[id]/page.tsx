import Link from "next/link";

import { EvidenceList, RawEvidence } from "../../../components/evidence-row";
import { Icon } from "../../../components/icon";
import { Metric } from "../../../components/metric";
import { PageHeader } from "../../../components/page-header";
import { Section } from "../../../components/section";
import { StatusBadge } from "../../../components/status-badge";
import { Timeline } from "../../../components/timeline";
import { getAiAnalysis } from "../../../lib/ai";
import { getIncident, type Incident } from "../../../lib/incidents";
import { getRca, type RCAAnalysis } from "../../../lib/rca";

export const dynamic = "force-dynamic";

type Candidate = { cause: string; score: number; rank: number; confidence: string };

function candidatesFrom(details: RCAAnalysis["details"]): Candidate[] {
  const candidates = details.candidates;
  if (!Array.isArray(candidates)) return [];
  return candidates.filter((candidate): candidate is Candidate => {
    return Boolean(candidate && typeof candidate === "object" && "cause" in candidate && "rank" in candidate && "score" in candidate && "confidence" in candidate);
  });
}

function incidentKindLabel(incident: Incident): string {
  return incident.incidentKind.replace("_", " ");
}

export default async function IncidentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const response = await getIncident(id);
  const rcaResponse = await getRca(id);
  const aiResponse = await getAiAnalysis(id);
  const incident = response.incident;

  return (
    <main className="shell" id="main-content">
      <PageHeader
        title="Incident detail"
        description={incident ? `${incident.datasetName} · ${incident.ruleName}` : "Inspect a persisted incident and its investigation evidence."}
        actions={<Link className="secondary-link" href="/incidents"><Icon name="arrow-right" size={15} className="icon-back" />Back to incidents</Link>}
        meta={<span className="page-meta">Deterministic evidence · read-only</span>}
      />

      {!incident ? (
        <Section title="Incident unavailable" description="The requested incident could not be loaded from the persisted record.">
          <div className="empty-state"><strong>{response.message ?? "Incident not found."}</strong><span>Return to incident history to choose another record.</span></div>
        </Section>
      ) : (
        <div className="section-stack incident-detail-stack">
          <Section title="Incident summary" description={`${incidentKindLabel(incident)} · ${incident.severity} severity`} action={<StatusBadge status={incident.status} />}>
            <div className="incident-summary">
              <div className="incident-summary-copy">
                <h2>{incident.datasetName}</h2>
                <p className="summary-rule">{incident.ruleName} <span>·</span> <code>{incident.ruleSlug}</code></p>
                <p className="body-copy">{incident.summary}</p>
              </div>
              <div className="incident-summary-metrics">
                <Metric label="Occurrences" value={incident.occurrenceCount.toLocaleString()} detail="Persisted observations" />
                <Metric label="Last seen" value={<time dateTime={incident.lastSeenAt}>{new Date(incident.lastSeenAt).toLocaleDateString()}</time>} detail={new Date(incident.lastSeenAt).toLocaleTimeString()} />
              </div>
            </div>
            <dl className="evidence-list summary-evidence">
              <div className="evidence-row"><dt>Opened</dt><dd><strong><time dateTime={incident.openedAt}>{new Date(incident.openedAt).toLocaleString()}</time></strong></dd></div>
              <div className="evidence-row"><dt>Incident key</dt><dd><strong><code>{incident.incidentKey}</code></strong></dd></div>
              {incident.acknowledgedAt && <div className="evidence-row"><dt>Acknowledged</dt><dd><strong><time dateTime={incident.acknowledgedAt}>{new Date(incident.acknowledgedAt).toLocaleString()}</time></strong></dd></div>}
              {incident.resolvedAt && <div className="evidence-row"><dt>Resolved</dt><dd><strong><time dateTime={incident.resolvedAt}>{new Date(incident.resolvedAt).toLocaleString()}</time></strong></dd></div>}
            </dl>
          </Section>

          <Section title="Deterministic root cause" description="A ranked explanation derived from persisted evidence. It is authoritative for this view; optional AI is shown later." action={<span className="section-note">No AI inference</span>}>
            {!rcaResponse.analysis ? (
              <div className="empty-state"><strong>{rcaResponse.message ?? "No RCA analysis is available."}</strong><span>Analysis is created when an incident is opened or meaningfully updated.</span></div>
            ) : (
              <div className="rca-content">
                <div className="rca-lead">
                  <div><span className="field-label">Top ranked cause</span><strong>{rcaResponse.analysis.topCause.replaceAll("_", " ")}</strong></div>
                  <span className={`confidence confidence-${rcaResponse.analysis.confidence.toLowerCase()}`}>{rcaResponse.analysis.confidence} confidence</span>
                  <p className="body-copy">{rcaResponse.analysis.summary}</p>
                </div>
                {candidatesFrom(rcaResponse.analysis.details).length > 0 && (
                  <div className="rca-candidates">
                    <h3>Ranked candidates</h3>
                    <div className="candidate-list">
                      {candidatesFrom(rcaResponse.analysis.details).map((candidate) => (
                        <div className="candidate-row" key={`${candidate.rank}-${candidate.cause}`}>
                          <span><strong>#{candidate.rank} {candidate.cause.replaceAll("_", " ")}</strong><small>{candidate.confidence} confidence</small></span>
                          <code>score {candidate.score}</code>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {rcaResponse.analysis.evidence.length > 0 && (
                  <div className="rca-evidence">
                    <h3>Evidence used</h3>
                    <div className="signal-list">
                      {rcaResponse.analysis.evidence.map((evidence, index) => (
                        <div className="signal-row" key={`${evidence.reasonCode}-${index}`}>
                          <span><strong>{evidence.reasonCode.replaceAll("_", " ")}</strong><small>{evidence.evidenceType} · {evidence.sourceTable}</small></span>
                          <code>weight {evidence.weight}</code>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <p className="quiet-note">Algorithm {rcaResponse.analysis.algorithmVersion} · fingerprint {rcaResponse.analysis.evidenceFingerprint.slice(0, 12)}… · created {new Date(rcaResponse.analysis.createdAt).toLocaleString()}</p>
              </div>
            )}
          </Section>

          <Section title="Evidence" description="Human-readable fields are the first view. Raw JSON remains available when exact payload inspection is useful." action={<span className="section-note">{incident.occurrenceCount} occurrence{incident.occurrenceCount === 1 ? "" : "s"}</span>}>
            <EvidenceList record={incident.evidence} />
            <RawEvidence value={incident.evidence} />
          </Section>

          <Section title="Blast radius" description="Downstream assets captured when this incident was evaluated." action={<Link className="text-link" href={`/lineage/${incident.datasetSlug}`}>Open dataset lineage <Icon name="arrow-right" size={15} /></Link>}>
            {incident.impacts.length === 0 ? (
              <div className="empty-state"><strong>No downstream snapshot is available.</strong><span>The incident record does not include captured lineage impact for this evaluation.</span></div>
            ) : (
              <div className="impact-list">
                {incident.impacts.map((impact) => (
                  <article className="impact-row" key={impact.lineageNodeId}>
                    <div><strong>{impact.name}</strong><span className="table-secondary">{impact.nodeType} · distance {impact.distance}</span></div>
                    <div className="path-list" aria-label={`Path to ${impact.name}`}>{impact.path.map((step, index) => <span key={`${step}-${index}`}>{step}</span>)}</div>
                  </article>
                ))}
              </div>
            )}
          </Section>

          <Section title="Lifecycle" description="Chronological state transitions recorded for this incident." action={<span className="section-note">{incident.events.length} event{incident.events.length === 1 ? "" : "s"}</span>}>
            <Timeline events={incident.events} />
          </Section>

          <Section title="AI Incident Copilot" description="Optional explanatory context based on the same persisted evidence. It cannot change incident state." action={<span className="section-note">Optional · non-authoritative</span>}>
            {!aiResponse.analysis ? (
              <div className="empty-state"><strong>{aiResponse.message ?? "No AI incident explanation is available."}</strong><span>This page never triggers inference; only a persisted analysis is shown.</span></div>
            ) : (
              <div className="ai-content">
                <div className="ai-status-row"><StatusBadge status={aiResponse.analysis.status} /><span className="muted">{aiResponse.analysis.provider} · {aiResponse.analysis.model}</span></div>
                <div className="ai-copy"><strong>{aiResponse.analysis.explanation.summary}</strong><p>{aiResponse.analysis.explanation.probableCauseExplanation}</p></div>
                {aiResponse.analysis.explanation.evidenceHighlights.length > 0 && <div><h3>Evidence highlights</h3><div className="signal-list">{aiResponse.analysis.explanation.evidenceHighlights.map((item) => <div className="signal-row" key={item.evidenceId}><span><strong>{item.evidenceId}</strong><small>{item.text}</small></span></div>)}</div></div>}
                <div className="ai-columns"><div><h3>Suggested investigation</h3><ol>{aiResponse.analysis.explanation.investigationSteps.map((step) => <li key={step}>{step}</li>)}</ol></div><div><h3>Uncertainties</h3>{aiResponse.analysis.explanation.uncertainties.length === 0 ? <p className="muted">No additional uncertainties recorded.</p> : <ul>{aiResponse.analysis.explanation.uncertainties.map((item) => <li key={item}>{item}</li>)}</ul>}</div></div>
                <p className="quiet-note">Prompt {aiResponse.analysis.promptVersion} · generated {new Date(aiResponse.analysis.createdAt).toLocaleString()} · {aiResponse.analysis.cacheHit ? "cache hit" : "new analysis"}</p>
              </div>
            )}
          </Section>
        </div>
      )}
    </main>
  );
}
