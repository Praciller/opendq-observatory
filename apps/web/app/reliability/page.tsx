import Link from "next/link";

import { getReliability, type ReliabilityExecution, type ReliabilityState } from "../../lib/reliability";

export const dynamic = "force-dynamic";

function StatePill({ state }: { state: ReliabilityState }) {
  return <span className={`status-pill reliability-${state.toLowerCase()}`}>{state}</span>;
}

function ExecutionCard({ name, execution }: { name: string; execution: ReliabilityExecution }) {
  return (
    <article className="reliability-card">
      <p className="eyebrow">Execution SLI</p>
      <h2>{name}</h2>
      <strong className="reliability-number">
        {execution.successRate === null ? "Insufficient history" : `${execution.successRate.toFixed(2)}%`}
      </strong>
      <p className="muted">{execution.successfulExecutions} successful of {execution.runCount} recorded runs; {execution.failedExecutions} failed.</p>
      <p className="muted">Latest run: {execution.latestRunAt ? new Date(execution.latestRunAt).toLocaleString() : "Not recorded"}</p>
    </article>
  );
}

export default async function ReliabilityPage() {
  const reliability = await getReliability();
  return (
    <main className="shell">
      <header className="hero quality-hero">
        <p className="eyebrow">Phase 6 · Reliability evidence</p>
        <h1>Operational reliability</h1>
        <p className="intro">Measured execution history, data outcomes, and incident state are shown separately. A quality FAIL or drift signal is not the same thing as a broken pipeline.</p>
        <nav className="page-nav"><Link className="text-link" href="/">← System status</Link><Link className="text-link" href="/incidents">View incidents →</Link></nav>
      </header>

      <section className="panel" aria-labelledby="window-heading">
        <div className="section-heading"><div><p className="eyebrow">Measured window</p><h2 id="window-heading">Available evidence</h2></div><StatePill state={reliability.window.state === "MEASURED" ? "SUCCESS" : "UNAVAILABLE"} /></div>
        <p className="muted">{reliability.window.start && reliability.window.end ? `${new Date(reliability.window.start).toLocaleString()} → ${new Date(reliability.window.end).toLocaleString()}` : "No completed pipeline history is available yet."}</p>
        {reliability.message && <div className="empty-state"><strong>{reliability.message}</strong><span>Run the scheduled pipeline or a local fixture evaluation before interpreting SLO history.</span></div>}
      </section>

      <div className="reliability-grid">
        <ExecutionCard name="Pipeline" execution={reliability.execution.pipeline} />
        <ExecutionCard name="Quality evaluation" execution={reliability.execution.quality} />
        <ExecutionCard name="Drift evaluation" execution={reliability.execution.drift} />
      </div>

      <section className="panel" aria-labelledby="outcome-heading">
        <div className="section-heading"><div><p className="eyebrow">Outcome state</p><h2 id="outcome-heading">Data and incidents</h2></div><span className="count-label">Not an uptime score</span></div>
        <div className="reliability-outcomes">
          <div><span className="muted">Latest quality execution</span><StatePill state={reliability.state.quality} /></div>
          <div><span className="muted">Latest drift execution</span><StatePill state={reliability.state.drift} /></div>
          <div><span className="muted">Open incidents</span><strong>{reliability.incidents.open}</strong></div>
          <div><span className="muted">Acknowledged</span><strong>{reliability.incidents.acknowledged}</strong></div>
          <div><span className="muted">Resolved</span><strong>{reliability.incidents.resolved}</strong></div>
        </div>
      </section>

      <section className="panel"><p className="eyebrow">Interpretation</p><p className="muted">The SLO document defines how to interpret this evidence. Percentages are measured over the displayed window only; insufficient history remains explicitly labeled.</p></section>
    </main>
  );
}
