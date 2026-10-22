# Browser E2E smoke

The CI `browser-e2e` job runs pinned Playwright Chromium against the **built
Next.js application** and a disposable PostgreSQL 16 database with OpenDQ's
SQL migrations applied. It is intentionally independent from production,
credentials and any live Vercel deployment.

Coverage:

- All six main read-only routes at 360, 390, 768, and 1440 px.
- Real browser visibility of desktop sidebar and mobile header/navigation.
- Correct page heading and active navigation indicator.
- No page-level horizontal overflow at these viewports.
- Keyboard skip link and a primary navigation transition.

Install and run locally from `apps/web` with a disposable PostgreSQL database
and a valid `DATABASE_URL` (run `uv run python -m opendq migrate` from
`pipeline` first):

```sh
npm ci
npx playwright install chromium
npm run build
npm run test:e2e
```

Playwright boots `next start` on 127.0.0.1:3000 automatically. To point
the browser suite at an already running **local/test** server, set
`E2E_BASE_URL`. Never put sensitive production data, auth state,
browser traces or credentials into published CI artifacts.

This suite is a structural smoke guard, **not** a full accessibility,
functional, cross-browser, or visual-regression audit. It does not claim
to test the production deployment. Release verification must still check
the deployed domain separately.
