import Link from "next/link";

import { EvidenceRow } from "../../components/evidence-row";
import { Metric } from "../../components/metric";
import { PageHeader } from "../../components/page-header";
import { Section } from "../../components/section";
import { StatusBadge } from "../../components/status-badge";
import { getQualitySummaries, type QualityResult } from "../../lib/quality";

export const dynamic = "force-dynamic";

function valueText(value: Record<string, unknown>): string {
  return Object.entries(value)
    .map(([key, item]) => `${key}: ${typeof item === "string" ? item : JSON.stringify(item)}`)
    .join(" · ");
}

function resultPriority(result: QualityResult): number {
  return { FAIL: 0, ERROR: 0, WARN: 1, PASS: 2, SKIPPED: 3 }[result.status] ?? 4;
}

function orderResults(results: QualityResult[]): QualityResult[] {
  return [...results].sort((left, right) => resultPriority(left) - resultPriority(right));
}

export default async function QualityPage() {
  const quality = await getQualitySummaries();

  return (
    <main className="shell" id="main-content">
      <PageHeader
        title="Quality evidence"
        description="Review dataset health first, then open individual deterministic rules to inspect observed and expected values."
        actions={<Link className="secondary-link" href="/">Overview</Link>}
        meta={<span className="page-meta">Latest persisted evaluation per dataset</span>}
      />

      {quality.datasets.length === 0 ? (
        <Section title="No quality evaluation yet" description="The dashboard does not infer a score when persisted rule results are missing.">
          <div className="empty-state"><strong>{quality.message ?? "No quality evaluation has been recorded yet."}</strong><span>Individual rule results will appear when evaluation evidence is available.</span></div>
        </Section>
      ) : (
        <div className="section-stack">
          {quality.datasets.map((dataset) => (
            <Section
              key={dataset.datasetSlug}
              id={dataset.datasetSlug}
              title={dataset.datasetName}
              description={`${dataset.datasetSlug} · ${dataset.evaluationRunId ? "Latest evaluation recorded" : "No evaluation run recorded"}`}
              action={<StatusBadge status={dataset.status} />}
            >
              <div className="dataset-summary">
                <Metric label="Latest score" value={dataset.score === null ? "No score" : `${dataset.score.toFixed(1)} / 100`} detail={dataset.evaluatedAt ? `Evaluated ${new Date(dataset.evaluatedAt).toLocaleString()}` : "Not evaluated"} tone={dataset.status === "PASS" ? "success" : dataset.status === "UNKNOWN" ? "neutral" : "warning"} />
                <Metric label="Rules evaluated" value={dataset.ruleCounts.evaluated} detail={`${dataset.ruleCounts.passed} passed · ${dataset.ruleCounts.failed + dataset.ruleCounts.errored} failed or errored`} />
                <Metric label="Attention" value={dataset.ruleCounts.failed + dataset.ruleCounts.errored + dataset.ruleCounts.warned} detail={`${dataset.ruleCounts.warned} warned · ${dataset.ruleCounts.skipped} skipped`} tone={dataset.ruleCounts.failed + dataset.ruleCounts.errored > 0 ? "danger" : dataset.ruleCounts.warned > 0 ? "warning" : "success"} />
              </div>

              {dataset.results.length === 0 ? (
                <div className="empty-state"><strong>No individual rule results are available.</strong><span>The dataset summary has no persisted rule-level evidence to inspect.</span></div>
              ) : (
                <div className="quality-rules" aria-label={`${dataset.datasetName} quality rules`}>
                  {orderResults(dataset.results).map((result) => (
                    <details className="quality-rule" key={result.ruleSlug}>
                      <summary>
                        <span className="rule-title"><strong>{result.ruleName}</strong><small>{result.dimension} · {result.severity}</small></span>
                        <StatusBadge status={result.status} />
                      </summary>
                      <dl className="rule-evidence">
                        <EvidenceRow label="Observed" value={valueText(result.observedValue) || "Not available"} />
                        <EvidenceRow label="Expected" value={valueText(result.expectedValue) || "Not available"} />
                        <EvidenceRow label="Affected records" value={result.affectedRecords.toLocaleString()} />
                        <EvidenceRow label="Evaluated records" value={result.evaluatedRecords.toLocaleString()} />
                        {Object.keys(result.details).length > 0 && <EvidenceRow label="Details" value={valueText(result.details)} />}
                      </dl>
                    </details>
                  ))}
                </div>
              )}
            </Section>
          ))}
        </div>
      )}
    </main>
  );
}
