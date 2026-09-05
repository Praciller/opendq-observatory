import { buildHealthResponse, getSourceStatuses, type HealthResponse } from "../lib/status";

export const dynamic = "force-dynamic";

function StatusPill({ healthy }: { healthy: boolean }) {
  return (
    <span className={healthy ? "status-pill status-pill-good" : "status-pill status-pill-muted"}>
      {healthy ? "Healthy" : "Unavailable"}
    </span>
  );
}

function HealthSummary({ health }: { health: HealthResponse }) {
  return (
    <section className="panel health-panel" aria-labelledby="system-heading">
      <div>
        <p className="eyebrow">System</p>
        <h2 id="system-heading">{health.status === "healthy" ? "Operational" : "Degraded"}</h2>
        <p className="muted">Application availability is separate from database reachability.</p>
      </div>
      <div className="health-checks">
        <div>
          <span className="muted">Application</span>
          <StatusPill healthy />
        </div>
        <div>
          <span className="muted">Database</span>
          <StatusPill healthy={health.database === "healthy"} />
        </div>
      </div>
    </section>
  );
}

export default async function Home() {
  const health = await buildHealthResponse();
  const sources = await getSourceStatuses();

  return (
    <main className="shell">
      <header className="hero">
        <p className="eyebrow">Open source observability foundation</p>
        <h1>OpenDQ Observatory</h1>
        <p className="tagline">Data Reliability <span>•</span> Quality <span>•</span> Drift <span>•</span> Lineage <span>•</span> Incident Intelligence</p>
        <p className="intro">A deterministic-first home for public data ingestion, contracts, and trustworthy operational evidence.</p>
      </header>

      <HealthSummary health={health} />

      <section className="panel" aria-labelledby="sources-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Public inputs</p>
            <h2 id="sources-heading">Sources</h2>
          </div>
          <span className="count-label">{sources.sources.length} recorded</span>
        </div>
        {sources.sources.length === 0 ? (
          <div className="empty-state">
            <strong>{sources.message ?? "No source status available."}</strong>
            <span>Run the migration and an ingestion command to record the first source state.</span>
          </div>
        ) : (
          <div className="source-list">
            {sources.sources.map((source) => (
              <article className="source-row" key={source.slug}>
                <div>
                  <h3>{source.name}</h3>
                  <p className="muted">{source.slug}</p>
                </div>
                <div className="source-meta">
                  <StatusPill healthy={source.enabled && source.hasIngestion} />
                  <span className="muted">
                    {source.lastSuccessfulIngestion
                      ? `Last run ${new Date(source.lastSuccessfulIngestion).toLocaleString()}`
                      : "No successful ingestion yet"}
                  </span>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <footer>Phase 0–1 · Public data only · No fabricated operational metrics</footer>
    </main>
  );
}

