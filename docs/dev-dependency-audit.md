# Development dependency audit — 2026-10-23

This document tracks known **development-only** dependency advisories independently
from the production runtime audit. It is a review record, not a security
exception approval.

## Tested compatibility refresh

- `eslint-config-next` 16.3.4 → 16.4.2, aligned with Next.js 16.4.2.
- `tsx` 4.20.6 → 4.23.15.
- `eslint` 9.39.2 → 9.39.5; keep on ESLint 9 until the bundled
  `eslint-plugin-react` supports ESLint 10.
- Resolved patched `brace-expansion` versions (1.1.21 and 5.0.12)
  by running `npm audit fix --package-lock-only` **without** `--force`.

## Outstanding findings

`npm audit --audit-level=high` still reports **five HIGH findings** in
the development-only lint toolchain:
`eslint-config-next` → `@next/eslint-plugin-next` → `fast-glob`
→ `micromatch` → `braces`. The reported braces advisory is
[GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm).

The npm-recommended `npm audit fix --force` would downgrade
`eslint-config-next` to 14.2.35, diverging from Next.js 16.4.2.
**Do not make this forced downgrade.** Dependabot's ESLint 10-only
PR also failed lint due to a missing API in `eslint-plugin-react`.
The advisories remain open and are **not** marked accepted or remediated.

The runtime-only CI guard remains:
```sh
npm audit --omit=dev --audit-level=high
```
At this review it reported **zero runtime vulnerabilities**. This guard
does not prove safety of lint-time processing, CI PR checks, supply-chain
dependencies, or future advisories.

## Follow-up controls

- Review upstream `eslint-config-next` / `@next/eslint-plugin-next`
  dependencies for patched `fast-glob` / `micromatch` / `braces`.
- Keep third-party PR CI permissions at `contents: read` and avoid
  passing production credentials to lint/test jobs.
- Do not override nested package constraints without compatibility testing.
- Recheck full npm audit on subsequent dependency updates; triage
  remaining advisories with actual exploitability and affected paths.
