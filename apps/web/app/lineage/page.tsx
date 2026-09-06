import Link from "next/link";

import { Icon } from "../../components/icon";
import { LineageFlow } from "../../components/lineage-flow";
import { PageHeader } from "../../components/page-header";
import { Section } from "../../components/section";
import { getLineage, type LineageResponse } from "../../lib/lineage";

export const dynamic = "force-dynamic";

function LineageView({ data }: { data: LineageResponse }) {
  return (
    <>
      {data.nodes.length === 0 ? (
        <Section title="Dependency flow unavailable" description="No persisted lineage nodes were returned for this dataset.">
          <div className="empty-state"><strong>{data.message ?? "No lineage recorded."}</strong><span>Lineage impact will appear when a captured dependency record is available.</span></div>
        </Section>
      ) : (
        <>
          <Section
            title="Dependency flow"
            description="Read left to right: source feeds the dataset, the process evaluates it, the API serves it, and the dashboard presents it."
            action={<span className="section-note">{data.nodes.length} nodes · {data.edges.length} edges</span>}
          >
            <LineageFlow nodes={data.nodes} />
          </Section>
          <Section
            title="Downstream impact"
            description="Reachable assets from the selected dataset, ordered by shortest deterministic path."
            action={<span className="section-note">{data.impact.length} asset{data.impact.length === 1 ? "" : "s"}</span>}
          >
            {data.impact.length === 0 ? (
              <div className="empty-state"><strong>No downstream assets found.</strong><span>The selected dataset has no captured downstream path.</span></div>
            ) : (
              <div className="impact-list">
                {data.impact.map((item) => (
                  <article className="impact-row" key={item.key}>
                    <div><strong>{item.name}</strong><span className="table-secondary">{item.nodeType} · distance {item.distance}</span></div>
                    <div className="path-list" aria-label={`Path to ${item.name}`}>{item.path.map((step, index) => <span key={`${step}-${index}`}>{step}</span>)}</div>
                  </article>
                ))}
              </div>
            )}
          </Section>
        </>
      )}
    </>
  );
}

export default async function LineagePage() {
  const data = await getLineage("hourly-weather");
  return (
    <main className="shell" id="main-content">
      <PageHeader
        title="Operational lineage"
        description="Trace the selected public-data dataset through its deterministic process, read-only API, and downstream dashboard surface."
        actions={<Link className="secondary-link" href="/">Overview</Link>}
        meta={<span className="page-meta">Provider-neutral dependency map</span>}
      />
      <nav className="dataset-selector" aria-label="Lineage dataset selector">
        <span className="selector-label">Dataset</span>
        <Link className={data.dataset === "hourly-weather" ? "is-selected" : ""} href="/lineage">Hourly weather <code>hourly-weather</code></Link>
        <Link className={data.dataset === "earthquake-events" ? "is-selected" : ""} href="/lineage/earthquake-events">Earthquake events <code>earthquake-events</code></Link>
      </nav>
      <LineageView data={data} />
      <p className="page-footnote"><Icon name="info" size={15} />Lineage is a persisted snapshot; it does not infer dependencies that are not recorded.</p>
    </main>
  );
}
