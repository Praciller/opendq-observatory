# Deployment

## Intended architecture

- Next.js web/API: Vercel Hobby.
- PostgreSQL: Neon Free through `DATABASE_URL`.
- Scheduled ingestion: GitHub Actions every six hours, with `DATABASE_URL` supplied as an Actions secret.
- Local development: Docker Compose PostgreSQL.

The web app and Python pipeline may use different lightweight PostgreSQL drivers, but SQL migrations remain the single schema authority. The database URL is never committed, logged, or returned by an endpoint.

Vercel and Neon deployment are owner-authenticated operations. This repository prepares the interfaces and workflows but does not claim a production deployment unless independently authorized and verified. Cloudflare is forbidden for this project.

