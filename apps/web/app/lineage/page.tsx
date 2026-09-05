import Link from "next/link";

import { getLineage, type LineageResponse } from "../../lib/lineage";

export const dynamic = "force-dynamic";

function LineageView({ data }: { data: LineageResponse }) {
  return (
    <>
      {data.nodes.length === 0 ? <section className="panel empty-state"><strong>{data.message ?? "No lineage recorded."}</strong></section> : <>
        <section className="panel"><div className="section-heading"><h2>Implemented flow</h2><span className="count-label">{data.nodes.length} nodes · {data.edges.length} edges</span></div><div className="lineage-flow">{["SOURCE", "DATASET", "PROCESS", "API", "DASHBOARD"].map((type) => <div className="lineage-stage" key={type}><span className="eyebrow">{type}</span>{data.nodes.filter((node) => node.nodeType === type).map((node) => <div className="lineage-node" key={node.key}><strong>{node.name}</strong><small>{node.key}</small></div>)}</div>)}</div></section>
        <section className="panel"><div className="section-heading"><h2>Downstream impact</h2><span className="count-label">{data.impact.length} reachable assets</span></div>{data.impact.length === 0 ? <div className="empty-state"><span>No downstream assets found.</span></div> : <div className="impact-list">{data.impact.map((item) => <div className="impact-row" key={item.key}><strong>{item.name}</strong><span className="muted">{item.nodeType} · distance {item.distance} · {item.path.join(" → ")}</span></div>)}</div>}</section>
      </>}
    </>
  );
}

export default async function LineagePage() {
  const data = await getLineage("hourly-weather");
  return <main className="shell"><header className="hero quality-hero"><p className="eyebrow">Phase 3 · Lineage</p><h1>Operational lineage</h1><p className="intro">A small provider-neutral graph of the source, normalized dataset, deterministic process, read-only API, and dashboard.</p><nav className="page-nav"><Link className="text-link" href="/">← System status</Link><Link className="text-link" href="/lineage/earthquake-events">View USGS lineage →</Link></nav></header><LineageView data={data} /></main>;
}
