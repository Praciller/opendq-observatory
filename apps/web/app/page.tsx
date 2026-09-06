import Link from "next/link";

import { Icon } from "../components/icon";
import { Metric } from "../components/metric";
import { PageHeader } from "../components/page-header";
import { Section } from "../components/section";
import { StatusBadge } from "../components/status-badge";
import { getDrift } from "../lib/drift";
import { getIncidents } from "../lib/incidents";
import { getQualitySummaries } from "../lib/quality";
import { buildHealthResponse, getSourceStatuses } from "../lib/status";

export const dynamic = "force-dynamic";

function dateText(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "Not recorded";
}

export default async function Home() {
  const [health, sources, quality, incidentResponse, drift] = await Promise.all([
    buildHealthResponse(),
    getSourceStatuses(),
    getQualitySummaries(),
    getIncidents(),
    getDrift(),
  ]);
  const activeIncidents = incidentResponse.incidents.filter((incident) => incident.status !== "RESOLVED");
  const driftSignals = drift.results.filter((result) => ["DRIFT", "WARN", "ERROR"].includes(result.status));
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
        description="Application availability and database reachability are reported separately."
        action={<StatusBadge status={platformStatus} label={health.status === "healthy" ? "Operational" : "Degraded"} />}
        className="overview-state"
      >
        <div className="state-grid">
          <div className="state-lead">
            <StatusBadge status={platformStatus} label={health.status === "healthy" ? "Operational" : "Degraded"} />
            <strong>{health.status === "healthy" ? "The observatory is available" : "The observatory is degraded"}</strong>
            <p className="muted">The dashboard remains read-only; data outcomes below are independent evidence.</p>
          </div>
          <div className="status-checks" aria-label="Platform checks">
            <div><span>Application</span><StatusBadge status="OPERATIONAL" label="Healthy" /></div>
            <div><span>Database</span><StatusBadge status={health.database === "healthy" ? "OPERATIONAL" : "UNAVAILABLE"} label={health.database === "healthy" ? "Healthy" : "Unavailable"} /></div>
          </div>
        </div>
        <div className="summary-strip" aria-label="Current operational summary">
          <Metric label="Active incidents" value={activeIncidents.length} detail="Open or acknowledged" tone={activeIncidents.length > 0 ? "danger" : "success"} />
          <Metric label="Drift signals" value={driftSignals.length} detail="Warn, drift, or error" tone={driftSignals.length > 0 ? "warning" : "success"} />
          <Metric label="Datasets" value={quality.datasets.length} detail="With latest quality state" />
        </div>
      </Section>

      <Section
        title="Needs attention"
        description="Signals that may change the next investigation path, ordered before healthy details."
        action={<Link className="text-link" href="/incidents">Open incident history <Icon name="arrow-right" size={15} /></Link>}
      >
        {attentionCount === 0 ? (
          <div className="empty-state empty-success">
            <StatusBadge status="STABLE" label="No active signals" />
            <strong>No active incidents or drift signals were returned.</strong>
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
            <div className="subsection-heading"><h3>Sources</h3><span>{sources.sources.length} recorded</span></div>
            {sources.sources.length === 0 ? (
              <div className="empty-state"><strong>{sources.message ?? "No source status is available."}</strong><span>Source evidence will appear after a successful ingestion is recorded.</span></div>
            ) : (
              <div className="signal-list">
                {sources.sources.map((source) => (
                  <div className="signal-row" key={source.slug}>
                    <span><strong>{source.name}</strong><small>{source.slug} · {source.lastSuccessfulIngestion ? `Last run ${dateText(source.lastSuccessfulIngestion)}` : "No successful ingestion yet"}</small></span>
                    <StatusBadge status={source.enabled && source.hasIngestion ? "OPERATIONAL" : "UNKNOWN"} label={source.enabled && source.hasIngestion ? "Healthy" : "Not available"} />
                  </div>
                ))}
              </div>
            )}
          </div>
          <div>
            <div className="subsection-heading"><h3>Quality state</h3><span>{quality.datasets.length} datasets</span></div>
            {quality.datasets.length === 0 ? (
              <div className="empty-state"><strong>{quality.message ?? "No quality evaluation is available."}</strong><span>Individual rule results will appear when persisted evidence exists.</span></div>
            ) : (
              <div className="signal-list">
                {quality.datasets.map((dataset) => (
                  <Link className="signal-row" href={`/quality#${dataset.datasetSlug}`} key={dataset.datasetSlug}>
                    <span><strong>{dataset.datasetName}</strong><small>{dataset.datasetSlug} · {dataset.ruleCounts.evaluated} rules evaluated</small></span>
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
