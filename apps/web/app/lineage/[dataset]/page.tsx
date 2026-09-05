import Link from "next/link";

import { getLineage } from "../../../lib/lineage";

export const dynamic = "force-dynamic";

export default async function DatasetLineagePage({ params }: { params: Promise<{ dataset: string }> }) {
  const { dataset } = await params;
  const data = await getLineage(dataset);
  return <main className="shell"><header className="hero quality-hero"><p className="eyebrow">Phase 3 · Lineage</p><h1>{data.dataset}</h1><p className="intro">Selected dataset lineage and deterministic downstream impact.</p><nav className="page-nav"><Link className="text-link" href="/lineage">← Weather lineage</Link><Link className="text-link" href="/incidents">View incidents →</Link></nav></header><section className="panel"><div className="section-heading"><h2>Graph</h2><span className="count-label">{data.nodes.length} nodes · {data.edges.length} edges</span></div>{data.nodes.length === 0 ? <div className="empty-state"><strong>{data.message ?? "No lineage recorded."}</strong></div> : <div className="lineage-flow">{data.nodes.map((node) => <div className="lineage-node" key={node.key}><span className="eyebrow">{node.nodeType}</span><strong>{node.name}</strong><small>{node.key}</small></div>)}</div>}</section><section className="panel"><div className="section-heading"><h2>Blast radius</h2><span className="count-label">{data.impact.length} assets</span></div>{data.impact.map((item) => <div className="impact-row" key={item.key}><strong>{item.name}</strong><span className="muted">distance {item.distance} · {item.path.join(" → ")}</span></div>)}</section></main>;
}
