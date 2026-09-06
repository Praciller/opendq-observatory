import Link from "next/link";

import { Icon } from "../../components/icon";
import { Metric } from "../../components/metric";
import { PageHeader } from "../../components/page-header";
import { Section } from "../../components/section";
import { StatusBadge } from "../../components/status-badge";
import { getDrift, type DriftResult } from "../../lib/drift";

export const dynamic = "force-dynamic";

function groupResults(results: DriftResult[]): Array<{ datasetSlug: string; datasetName: string; results: DriftResult[] }> {
  const groups = new Map<string, { datasetSlug: string; datasetName: string; results: DriftResult[] }>();
  for (const result of results) {
    const group = groups.get(result.datasetSlug) ?? { datasetSlug: result.datasetSlug, datasetName: result.datasetName, results: [] };
    group.results.push(result);
    groups.set(result.datasetSlug, group);
  }
  return [...groups.values()];
}

function metricText(value: number | null): string {
  return value === null ? "Not available" : value.toFixed(4);
}

export default async function DriftPage() {
  const response = await getDrift();
  const signals = response.results.filter((result) => ["DRIFT", "WARN", "ERROR"].includes(result.status)).length;
  const stable = response.results.filter((result) => result.status === "STABLE").length;

  return (
    <main className="shell" id="main-content">
      <PageHeader
        title="Drift signals"
        description="Compare the latest persisted distribution checks with their versioned baselines. Drift is statistical evidence, separate from data quality."
        actions={<div className="page-actions"><Link className="secondary-link" href="/incidents">Incidents</Link><Link className="secondary-link" href="/">Overview</Link></div>}
        meta={<span className="page-meta">Latest check per dataset, feature, and method</span>}
      />

      <div className="summary-strip page-summary" aria-label="Drift summary">
        <Metric label="Evaluated features" value={response.results.length} detail="Latest persisted checks" />
        <Metric label="Needs review" value={signals} detail="Warn, drift, or error" tone={signals > 0 ? "danger" : "success"} />
        <Metric label="Stable" value={stable} detail="Below warning boundary" tone="success" />
      </div>

      {response.results.length === 0 ? (
        <Section title="No drift evaluation yet" description="A missing baseline or current sample is reported as missing evidence, not as a stable result.">
          <div className="empty-state"><strong>{response.message ?? "No drift results are available."}</strong><span>Drift evidence will appear when a persisted evaluation has enough legitimate data.</span></div>
        </Section>
      ) : (
        <div className="section-stack">
          {groupResults(response.results).map((group) => (
            <Section
              key={group.datasetSlug}
              title={group.datasetName}
              description={`${group.datasetSlug} · ${group.results.length} feature ${group.results.length === 1 ? "check" : "checks"}`}
              action={<Link className="text-link" href={`/lineage/${group.datasetSlug}`}>View lineage <Icon name="arrow-right" size={15} /></Link>}
            >
              <div className="table-wrap">
                <table className="data-table drift-table">
                  <caption className="sr-only">Drift checks for {group.datasetName}</caption>
                  <thead><tr><th scope="col">Status</th><th scope="col">Feature / method</th><th scope="col">Observed / threshold</th><th scope="col">Samples</th><th scope="col">Baseline</th><th scope="col">Evaluated</th></tr></thead>
                  <tbody>
                    {group.results.map((result) => (
                      <tr key={`${result.datasetSlug}:${result.columnName}:${result.method}`}>
                        <td data-label="Status"><StatusBadge status={result.status} /></td>
                        <td data-label="Feature / method"><strong>{result.columnName}</strong><span className="table-secondary">{result.method} · {result.severity}</span></td>
                        <td data-label="Observed / threshold"><code>{metricText(result.observedMetric)} / {metricText(result.threshold)}</code></td>
                        <td data-label="Samples"><span className="table-secondary">Baseline {result.baselineSampleCount.toLocaleString()}</span><span>{result.currentSampleCount.toLocaleString()} current</span></td>
                        <td data-label="Baseline">{result.baselineVersion === null ? "Not available" : `v${result.baselineVersion}`}</td>
                        <td data-label="Evaluated"><time dateTime={result.evaluatedAt}>{new Date(result.evaluatedAt).toLocaleString()}</time></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Section>
          ))}
        </div>
      )}

      <Section title="How to read drift" description="The status is deterministic and uses the configured method and threshold.">
        <p className="body-copy">Stable is below the warning boundary. WARN is an early signal. DRIFT meets the configured threshold and can create a DATA_DRIFT incident. SKIPPED means there is not enough legitimate baseline or current data.</p>
      </Section>
    </main>
  );
}
