import Link from "next/link";

import { getQualitySummaries, type QualityStatus } from "../../lib/quality";

export const dynamic = "force-dynamic";

function QualityPill({ status }: { status: QualityStatus }) {
  return <span className={`status-pill quality-pill quality-${status.toLowerCase()}`}>{status}</span>;
}

function valueText(value: Record<string, unknown>): string {
  return Object.entries(value)
    .map(([key, item]) => `${key}: ${typeof item === "string" ? item : JSON.stringify(item)}`)
    .join(" · ");
}

export default async function QualityPage() {
  const quality = await getQualitySummaries();

  return (
    <main className="shell">
      <header className="hero quality-hero">
        <p className="eyebrow">Phase 2 · Data Quality Engine</p>
        <h1>Quality evidence</h1>
        <p className="intro">Deterministic checks over the persisted Open-Meteo and USGS observations. Scores summarize the rules; individual results remain the source of truth.</p>
        <Link className="text-link" href="/">← Back to system status</Link>
      </header>

      {quality.datasets.length === 0 ? (
        <section className="panel empty-state">
          <strong>{quality.message ?? "No quality evaluation has been recorded yet."}</strong>
          <span>Apply the quality migration and run <code>python -m opendq quality evaluate all</code>.</span>
        </section>
      ) : (
        <div className="quality-detail-list">
          {quality.datasets.map((dataset) => (
            <section className="panel" key={dataset.datasetSlug} aria-labelledby={`${dataset.datasetSlug}-heading`}>
              <div className="quality-detail-heading">
                <div>
                  <p className="eyebrow">Dataset</p>
                  <h2 id={`${dataset.datasetSlug}-heading`}>{dataset.datasetName}</h2>
                  <p className="muted">{dataset.datasetSlug}</p>
                </div>
                <div className="quality-score-block">
                  <QualityPill status={dataset.status} />
                  <strong>{dataset.score === null ? "No score" : `${dataset.score.toFixed(1)} / 100`}</strong>
                  <span className="muted">{dataset.evaluatedAt ? `Evaluated ${new Date(dataset.evaluatedAt).toLocaleString()}` : "Not evaluated"}</span>
                </div>
              </div>
              <div className="quality-counts" aria-label="Quality result counts">
                <span>Pass {dataset.ruleCounts.passed}</span>
                <span>Warn {dataset.ruleCounts.warned}</span>
                <span>Fail {dataset.ruleCounts.failed}</span>
                <span>Error {dataset.ruleCounts.errored}</span>
                <span>Skipped {dataset.ruleCounts.skipped}</span>
              </div>
              {dataset.results.length === 0 ? (
                <div className="empty-state"><span>No individual rule results are available.</span></div>
              ) : (
                <div className="quality-rules">
                  {dataset.results.map((result) => (
                    <details className="quality-rule" key={result.ruleSlug}>
                      <summary>
                        <span><strong>{result.ruleName}</strong><small>{result.dimension} · {result.severity}</small></span>
                        <QualityPill status={result.status === "SKIPPED" ? "UNKNOWN" : result.status} />
                      </summary>
                      <div className="quality-rule-body">
                        <p><strong>Observed:</strong> {valueText(result.observedValue) || "—"}</p>
                        <p><strong>Expected:</strong> {valueText(result.expectedValue) || "—"}</p>
                        <p><strong>Affected records:</strong> {result.affectedRecords} · <strong>Evaluated:</strong> {result.evaluatedRecords}</p>
                        {Object.keys(result.details).length > 0 && <p><strong>Details:</strong> {valueText(result.details)}</p>}
                      </div>
                    </details>
                  ))}
                </div>
              )}
            </section>
          ))}
        </div>
      )}
    </main>
  );
}
