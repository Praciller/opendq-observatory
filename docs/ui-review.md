# UI and accessibility review

Reviewed 2026-09-06 against the local deterministic demo database with the Phase 6 reliability route enabled.

## Information architecture

The recruiter path is now visible from the home page: system health → sources → quality → incidents → drift → lineage → reliability. Existing route labels retain their domain meaning; reliability explicitly explains that execution status is separate from data outcomes.

## Browser evidence

- Desktop viewport: 1440px; home, quality, drift, incidents, incident detail, lineage, and reliability rendered.
- Tablet viewport: 768px; reliability rendered with a two-column execution grid and no horizontal overflow.
- Mobile viewport: 390px; home and incident detail rendered with stacked content and no horizontal overflow.
- `document.documentElement.scrollWidth` equaled `innerWidth` at all checked viewports.
- `agent-browser a11y` reported zero axe violations on home, reliability, and incidents. Axe reported one incomplete contrast check because the background gradient prevents automated background-color determination; this is not an asserted violation and was manually inspected in the captured screenshots.
- Browser console and page-error checks were clear after navigation.

## Status semantics

Status badges include text labels as well as color. `DRIFT`, runtime `ERROR`, `PASS`, `WARN`, `FAIL`, `OPEN`, `RESOLVED`, and fallback states use distinct labels and styling. Reliability copy explicitly prevents a data-quality outcome from being read as infrastructure uptime.

## Screenshot set

The intentional safe-demo captures are in `docs/screenshots/phase6/`:

- `home-desktop.png`
- `home-mobile.png`
- `reliability-tablet.png`
- `quality-desktop.png`
- `drift-desktop.png`
- `incidents-desktop.png`
- `incident-detail-desktop.png`
- `incident-detail-mobile.png`
- `lineage-desktop.png`

These are deterministic local-demo screenshots, not claims about the pre-deployment production UI. No credentials or database connection values are present.
