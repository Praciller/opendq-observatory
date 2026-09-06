# Deployment

## Intended architecture

- Next.js web/API: Vercel Hobby.
- PostgreSQL: Neon Free through `DATABASE_URL`.
- Scheduled ingestion and quality evaluation: GitHub Actions every six hours, with `DATABASE_URL` supplied as an Actions secret.
- Local development: Docker Compose PostgreSQL.

The web app and Python pipeline may use different lightweight PostgreSQL drivers, but SQL migrations remain the single schema authority. The database URL is never committed, logged, or returned by an endpoint.

The production deployment is independently verified at the public project URL. Data quality, drift, incidents, lineage, deterministic RCA, and the optional AI explanation layer all read persisted Neon state. Cloudflare remains forbidden for this project.

## Post-deploy UI contract

A Vercel deployment reporting `READY` is not sufficient evidence that the rendered console is correct. The v1.0.1 guard fetches the deployed HTML and every referenced stylesheet, then requires the OpenDQ shell selectors to be present.

Run after each production deployment:

```powershell
cd apps/web
npm run verify:production-ui -- https://opendq-observatory.vercel.app
```

The guard requires at least:

```text
.sidebar
.mobile-header
.mobile-nav
.app-frame
.section-card
```

A manual GitHub Actions workflow, `Verify production UI`, runs the same contract against a supplied deployment URL.

## Vercel cache recovery

If production HTML is current but the deployed stylesheet is missing OpenDQ selectors, redeploy the same verified source without restoring the Vercel build cache. Do not change application CSS merely to compensate for a stale or mismatched deployment artifact.

## Browser QA

Before closing a release, verify the production console at desktop and mobile widths.

Desktop expectations:
- sidebar visible;
- mobile header/navigation hidden;
- content offset from the 240px sidebar;
- cards and status badges styled.

Mobile expectations at 390px:
- sidebar hidden;
- mobile header/navigation visible;
- `document.documentElement.scrollWidth === clientWidth`;
- no page-level horizontal overflow.
