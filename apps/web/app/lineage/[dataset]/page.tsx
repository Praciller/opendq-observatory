import Link from "next/link";

import { Icon } from "../../../components/icon";
import { LineageFlow } from "../../../components/lineage-flow";
import { PageHeader } from "../../../components/page-header";
import { Section } from "../../../components/section";
import { getLineage } from "../../../lib/lineage";

export const dynamic = "force-dynamic";

function datasetName(slug: string): string {
  return slug === "hourly-weather" ? "Hourly weather" : slug === "earthquake-events" ? "Earthquake events" : slug;
}

export default async function DatasetLineagePage({ params }: { params: Promise<{ dataset: string }> }) {
  const { dataset } = await params;
  const data = await getLineage(dataset);
  const name = datasetName(data.dataset);

  return (
    <main className="shell" id="main-content">
      <PageHeader
        title={`${name} lineage`}
        description="Follow the selected dataset through each recorded dependency and inspect its downstream impact."
        actions={<Link className="secondary-link" href="/lineage"><Icon name="arrow-right" size={15} className="icon-back" />All lineage</Link>}
        meta={<span className="page-meta"><code>{data.dataset}</code> · selected dataset</span>}
      />
      <nav className="dataset-selector" aria-label="Lineage dataset selector">
        <span className="selector-label">Dataset</span>
        <Link className={data.dataset === "hourly-weather" ? "is-selected" : ""} href="/lineage">Hourly weather <code>hourly-weather</code></Link>
        <Link className={data.dataset === "earthquake-events" ? "is-selected" : ""} href="/lineage/earthquake-events">Earthquake events <code>earthquake-events</code></Link>
      </nav>

      {data.nodes.length === 0 ? (
        <Section title="Dependency flow unavailable" description="No persisted lineage nodes were returned for this dataset.">
          <div className="empty-state"><strong>{data.message ?? "No lineage recorded."}</strong><span>Return to the lineage index or choose another dataset.</span></div>
        </Section>
      ) : (
        <div className="section-stack">
          <Section title="Dependency flow" description="Each connector means the stage to its left feeds the stage to its right." action={<span className="section-note">{data.nodes.length} nodes · {data.edges.length} edges</span>}>
            <LineageFlow nodes={data.nodes} />
          </Section>
          <Section title="Blast radius" description="Downstream assets reachable from this dataset in the captured lineage graph." action={<span className="section-note">{data.impact.length} asset{data.impact.length === 1 ? "" : "s"}</span>}>
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
        </div>
      )}
    </main>
  );
}
