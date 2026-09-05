# Deployment

## Intended architecture

- Next.js web/API: Vercel Hobby.
- PostgreSQL: Neon Free through `DATABASE_URL`.
- Scheduled ingestion and quality evaluation: GitHub Actions every six hours, with `DATABASE_URL` supplied as an Actions secret.
- Local development: Docker Compose PostgreSQL.

The web app and Python pipeline may use different lightweight PostgreSQL drivers, but SQL migrations remain the single schema authority. The database URL is never committed, logged, or returned by an endpoint.

The Phase 1.5 production deployment is independently verified at the public project URL. Phase 2 migration, quality evaluation, scheduled ingestion-plus-quality, and Vercel deployment are also verified against the real Neon database. Cloudflare is forbidden for this project.

