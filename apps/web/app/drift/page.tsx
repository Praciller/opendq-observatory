import Link from "next/link";

import { getDrift, type DriftResult } from "../../lib/drift";

export const dynamic = "force-dynamic";

function DriftPill({ status }: { status: DriftResult["status"] }) {
  return <span className={`status-pill drift-${status.toLowerCase()}`}>{status}</span>;
}

function metric(result: DriftResult): string {
  return result.observedMetric === null ? "—" : result.observedMetric.toFixed(4);
}

export default async function DriftPage() {
  const response = await getDrift();
  return (
    <main className="shell">
      <header className="hero quality-hero">
        <p className="eyebrow">Phase 4 · Distribution Monitoring</p>
        <h1>Drift detection</h1>
        <p className="intro">Versioned baselines and interpretable distribution checks. Drift is statistical evidence, separate from data quality.</p>
        <nav className="page-nav"><Link className="text-link" href="/">← System status</Link><Link className="text-link" href="/incidents">View incidents →</Link></nav>
      </header>
      {response.results.length === 0 ? (
        <section className="panel empty-state"><strong>{response.message ?? "No drift results available."}</strong><span>Create a trusted baseline after enough legitimate observations exist.</span></section>
      ) : (
        <section className="panel">
          <div className="section-heading"><div><p className="eyebrow">Persisted evidence</p><h2>Latest checks</h2></div><span className="count-label">{response.results.length} checks</span></div>
          <div className="drift-list">
            {response.results.map((result) => (
              <article className="drift-row" key={`${result.datasetSlug}:${result.columnName}:${result.method}`}>
                <div><strong>{result.datasetName}</strong><span className="muted">{result.columnName} · {result.method}</span></div>
                <div className="drift-meta"><DriftPill status={result.status} /><span>Metric {metric(result)} / {result.threshold ?? "—"}</span><span>Baseline v{result.baselineVersion ?? "—"}</span><span>{result.currentSampleCount} current samples</span><time>{new Date(result.evaluatedAt).toLocaleString()}</time></div>
              </article>
            ))}
          </div>
        </section>
      )}
      <section className="panel"><div className="section-heading"><h2>Interpretation</h2><span className="count-label">Deterministic PSI</span></div><p className="muted">Stable is below the warning boundary; WARN is an early signal; DRIFT meets the configured threshold and can create a DATA_DRIFT incident. SKIPPED means there is not enough legitimate baseline or current data.</p></section>
      <footer>Drift baselines are immutable and versioned. No fabricated trend data.</footer>
    </main>
  );
}
