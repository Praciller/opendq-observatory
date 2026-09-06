import Link from "next/link";

import { Metric } from "../../components/metric";
import { PageHeader } from "../../components/page-header";
import { Section } from "../../components/section";
import { StatusBadge } from "../../components/status-badge";
import { getReliability, type ReliabilityExecution, type ReliabilityState } from "../../lib/reliability";

export const dynamic = "force-dynamic";

function StateBadge({ state }: { state: ReliabilityState | "MEASURED" | "INSUFFICIENT_HISTORY" }) {
  return <StatusBadge status={state === "INSUFFICIENT_HISTORY" ? "UNAVAILABLE" : state} label={state.replaceAll("_", " ")} />;
}

function rateText(execution: ReliabilityExecution): string {
  return execution.successRate === null ? "Insufficient history" : `${execution.successRate.toFixed(2)}%`;
}

export default async function ReliabilityPage() {
  const reliability = await getReliability();
  const executions: Array<[string, ReliabilityExecution]> = [
    ["Pipeline ingestion", reliability.execution.pipeline],
    ["Quality evaluation", reliability.execution.quality],
    ["Drift evaluation", reliability.execution.drift],
  ];

  return (
    <main className="shell" id="main-content">
      <PageHeader
        title="Reliability evidence"
        description="Read measured execution history separately from data outcomes. A quality failure or drift signal is not the same thing as an unavailable pipeline."
        actions={<div className="page-actions"><Link className="secondary-link" href="/">Overview</Link><Link className="secondary-link" href="/incidents">Incidents</Link></div>}
        meta={<span className="page-meta">Execution, outcome, and incident facts remain separate</span>}
      />

      <Section title="Measured window" description="The time range used for the execution evidence below." action={<StateBadge state={reliability.window.state} />}>
        <div className="window-summary">
          <Metric label="Window start" value={reliability.window.start ? new Date(reliability.window.start).toLocaleDateString() : "Not available"} detail={reliability.window.start ? new Date(reliability.window.start).toLocaleTimeString() : "Insufficient history"} />
          <Metric label="Window end" value={reliability.window.end ? new Date(reliability.window.end).toLocaleDateString() : "Not available"} detail={reliability.window.end ? new Date(reliability.window.end).toLocaleTimeString() : "Insufficient history"} />
          <Metric label="Latest successful ingestion" value={reliability.execution.pipeline.latestSuccessfulIngestionAt ? new Date(reliability.execution.pipeline.latestSuccessfulIngestionAt).toLocaleDateString() : "Not recorded"} detail={reliability.execution.pipeline.latestSuccessfulIngestionAt ? new Date(reliability.execution.pipeline.latestSuccessfulIngestionAt).toLocaleTimeString() : "Pipeline evidence only"} />
        </div>
        {reliability.message && <div className="empty-state"><strong>{reliability.message}</strong><span>Execution percentages remain unavailable until the displayed window contains recorded runs.</span></div>}
      </Section>

      <Section title="Execution history" description="Success rate is calculated only from the recorded runs in the measured window.">
        <div className="table-wrap">
          <table className="data-table reliability-table">
            <caption className="sr-only">Reliability execution history</caption>
            <thead><tr><th scope="col">Operation</th><th scope="col">Success rate</th><th scope="col">Runs</th><th scope="col">Successful / failed</th><th scope="col">Latest run</th></tr></thead>
            <tbody>
              {executions.map(([name, execution]) => (
                <tr key={name}>
                  <td data-label="Operation"><strong>{name}</strong></td>
                  <td data-label="Success rate"><strong className="table-emphasis">{rateText(execution)}</strong></td>
                  <td data-label="Runs">{execution.runCount.toLocaleString()}</td>
                  <td data-label="Successful / failed"><span>{execution.successfulExecutions.toLocaleString()} successful</span><span className="table-secondary">{execution.failedExecutions.toLocaleString()} failed</span></td>
                  <td data-label="Latest run">{execution.latestRunAt ? <time dateTime={execution.latestRunAt}>{new Date(execution.latestRunAt).toLocaleString()}</time> : "Not recorded"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Outcome state" description="Latest quality, drift, and incident outcomes are measured independently from execution availability." action={<span className="section-note">Not an uptime score</span>}>
        <div className="outcome-grid">
          <div><span className="field-label">Latest quality</span><StateBadge state={reliability.state.quality} /></div>
          <div><span className="field-label">Latest drift</span><StateBadge state={reliability.state.drift} /></div>
          <div><span className="field-label">Open incidents</span><strong className="outcome-number">{reliability.incidents.open.toLocaleString()}</strong></div>
          <div><span className="field-label">Acknowledged</span><strong className="outcome-number">{reliability.incidents.acknowledged.toLocaleString()}</strong></div>
          <div><span className="field-label">Resolved</span><strong className="outcome-number">{reliability.incidents.resolved.toLocaleString()}</strong></div>
        </div>
      </Section>

      <p className="page-footnote"><StatusBadge status="INFO" label="Interpretation" />Percentages are measured over the displayed window only; insufficient history remains explicitly labeled.</p>
    </main>
  );
}
