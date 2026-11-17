import Link from "next/link";

import { Icon } from "../components/icon";
import { Metric } from "../components/metric";
import { PageHeader } from "../components/page-header";
import { Section } from "../components/section";
import { StatusBadge } from "../components/status-badge";
import { getDrift } from "../lib/drift";
import { getIncidents } from "../lib/incidents";
import { overviewEvidence } from "../lib/overview";
import { getQualitySummaries } from "../lib/quality";
import { evaluatePollReadiness, type SourcePollState } from "../lib/source-freshness";
import { buildHealthResponse, getSourceStatuses } from "../lib/status";
import { ageText, currentTime, utcTime } from "../lib/time";

export const dynamic = "force-dynamic";

const pollLabel: Record<SourcePollState, string> = {
  CURRENT: "Current poll",
  STALE: "Stale poll",
  NO_HISTORY: "No poll history",
  DISABLED: "Disabled",
  INVALID_TIME: "Invalid poll time",
};

export default async function Home() {
  const [{ health, checkedAt }, sources, quality, incidentResponse, drift] = await Promise.all([
    buildHealthResponse().then((health) => ({ health, checkedAt: currentTime() })),
    getSourceStatuses(),
    getQualitySummaries(),
    getIncidents(),
    getDrift(),
  ]);
  const observedAt = currentTime();
  const pollReadiness = evaluatePollReadiness(sources, true, new Date(observedAt));
  const polls = pollReadiness.sources;
  const evidence = overviewEvidence(incidentResponse, drift, quality);
  const { activeIncidents, driftSignals } = evidence;
  const attentionCount = activeIncidents.length + driftSignals.length;
  const platformStatus = health.status === "healthy" ? "OPERATIONAL" : "DEGRADED";

  return (
    <main className="shell" id="main-content">
      <PageHeader
        title="Operational overview"
        description="Start with platform state, then follow the latest data signals into persisted evidence."
        actions={<Link className="secondary-link" href="/reliability">View reliability</Link>}
        meta={<span className="page-meta"><span className="meta-dot" aria-hidden="true" />Read-only · persisted evidence</span>}
      />

      <Section
        title="Platform state"
        description="The database check tests reachability at page load; persisted evidence reflects earlier runs."
        action={<StatusBadge status={platformStatus} label={health.status === "healthy" ? "Operational" : "Degraded"} />}
        className="overview-state"
      >
        <div className="state-grid">
          <div className="state-lead">
            <StatusBadge status={platformStatus} label={health.status === "healthy" ? "Operational" : "Degraded"} />
            <strong>{health.status === "healthy" ? "The observatory is available" : "The observatory is degraded"}</strong>
            <p className="muted">Database check completed {utcTime(new Date(checkedAt).toISOString())}. A failed check can also reflect a timeout; it does not establish the cause.</p>
          </div>
          <div className="status-checks" aria-label="Platform checks">
            <div><span>Application</span><StatusBadge status="OPERATIONAL" label="Responding" /></div>
            <div><span>Database</span><StatusBadge status={health.database === "healthy" ? "OPERATIONAL" : "UNAVAILABLE"} label={health.database === "healthy" ? "Reachable" : "Check failed"} /></div>
          </div>
        </div>
        <div className="summary-strip" aria-label="Current operational summary">
          <Metric label="Active incidents" value={evidence.incidentCount} detail="Open or acknowledged in the latest 100 incident records" tone={evidence.incidentCount === "Unavailable" ? "neutral" : activeIncidents.length > 0 ? "danger" : "success"} />
          <Metric label="Drift signals" value={evidence.driftCount} detail="Warn, drift, or error in evaluated results" tone={driftSignals.length > 0 ? "warning" : evidence.driftComplete ? "success" : "neutral"} />
          <Metric label="Datasets" value={evidence.datasetCount} detail="With latest quality state" />
        </div>
      </Section>

      <Section
        title="Needs attention"
        description="Signals that may change the next investigation path, ordered before healthy details."
        action={<Link className="text-link" href="/incidents">Open incident history <Icon name="arrow-right" size={15} /></Link>}
      >
        {evidence.notes.length > 0 && <p className="muted">{evidence.notes.join(" ")}</p>}
        {attentionCount === 0 && evidence.incomplete ? (
          <div className="empty-state"><strong>Signal status is incomplete.</strong></div>
        ) : attentionCount === 0 ? (
          <div className="empty-state empty-success">
            <StatusBadge status="STABLE" label="None returned" />
            <strong>No active incidents in the latest 100 records or signals in the evaluated drift results.</strong>
            <span>Review dataset health below for the latest quality evidence.</span>
          </div>
        ) : (
          <div className="attention-grid">
            {activeIncidents.length > 0 && (
              <div className="attention-block">
                <div className="subsection-heading"><h3>Active incidents</h3><span>{activeIncidents.length}</span></div>
                <div className="signal-list">
                  {activeIncidents.slice(0, 4).map((incident) => (
                    <Link className="signal-row" href={`/incidents/${incident.id}`} key={incident.id}>
                      <span><strong>{incident.datasetName}</strong><small>{incident.ruleName}</small></span>
                      <StatusBadge status={incident.status} label={incident.severity} />
                    </Link>
                  ))}
                </div>
              </div>
            )}
            {driftSignals.length > 0 && (
              <div className="attention-block">
                <div className="subsection-heading"><h3>Drift signals</h3><span>{driftSignals.length}</span></div>
                <div className="signal-list">
                  {driftSignals.slice(0, 4).map((result) => (
                    <Link className="signal-row" href="/drift" key={`${result.datasetSlug}:${result.columnName}:${result.method}`}>
                      <span><strong>{result.datasetName}</strong><small>{result.columnName} · {result.method}</small></span>
                      <StatusBadge status={result.status} />
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </Section>

      <Section
        title="Dataset health"
        description="Latest source and quality states from the persisted observatory record."
        action={<Link className="text-link" href="/quality">View quality evidence <Icon name="arrow-right" size={15} /></Link>}
        className="dataset-health"
      >
        <div className="overview-subsections">
          <div>
            <div className="subsection-heading"><h3>Source polls</h3><span>{pollReadiness.status === "unavailable" ? "Unavailable" : `${polls.length} configured`}</span></div>
            {polls.length === 0 ? (
              <div className="empty-state"><strong>{sources.message ?? "No source status is available."}</strong><span>Source evidence will appear after a successful ingestion is recorded.</span></div>
            ) : (
              <div className="signal-list">
                {polls.map((source) => (
                  <div className="signal-row" key={source.slug}>
                    <span><strong>{source.name}</strong><small>{source.slug} · {source.lastSuccessfulPollAt ? `Last successful poll ${utcTime(source.lastSuccessfulPollAt)} · ${ageText(source.lastSuccessfulPollAt, observedAt)}` : "No successful poll yet"}</small></span>
                    <StatusBadge status={source.state} label={pollLabel[source.state]} />
                  </div>
                ))}
              </div>
            )}
          </div>
          <div>
            <div className="subsection-heading"><h3>Quality state</h3><span>{quality.message ? "Unavailable" : `${quality.datasets.length} datasets`}</span></div>
            {quality.datasets.length === 0 ? (
              <div className="empty-state"><strong>{quality.message ?? "No quality evaluation is available."}</strong><span>Individual rule results will appear when persisted evidence exists.</span></div>
            ) : (
              <div className="signal-list">
                {quality.datasets.map((dataset) => (
                  <Link className="signal-row" href={`/quality#${dataset.datasetSlug}`} key={dataset.datasetSlug}>
                    <span><strong>{dataset.datasetName}</strong><small>{dataset.datasetSlug} · {dataset.ruleCounts.evaluated} rules evaluated · Evaluated {utcTime(dataset.evaluatedAt)} ({ageText(dataset.evaluatedAt, observedAt)})</small></span>
                    <span className="signal-value"><StatusBadge status={dataset.status} /><strong>{dataset.score === null ? "No score" : `${dataset.score.toFixed(1)} / 100`}</strong></span>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      </Section>

      <Section title="Investigate next" description="Follow the evidence boundary that matches the question you need to answer.">
        <nav className="action-links" aria-label="Investigation paths">
          <Link className="action-link" href="/quality"><span><strong>Quality</strong><small>Rule-level outcomes</small></span><Icon name="arrow-right" size={17} /></Link>
          <Link className="action-link" href="/drift"><span><strong>Drift</strong><small>Distribution changes and baselines</small></span><Icon name="arrow-right" size={17} /></Link>
          <Link className="action-link" href="/lineage"><span><strong>Lineage</strong><small>Upstream source to downstream surface</small></span><Icon name="arrow-right" size={17} /></Link>
          <Link className="action-link" href="/reliability"><span><strong>Reliability</strong><small>Measured execution history</small></span><Icon name="arrow-right" size={17} /></Link>
        </nav>
      </Section>
    </main>
  );
}
