# OpenDQ Observatory design contract

## Product, audience, and job

OpenDQ Observatory is a public, read-only operational console for deterministic data reliability evidence. Its primary audience is a recruiter or engineer evaluating whether a data pipeline can be trusted and investigated. The core job is to answer, in order: is the platform available, is the data healthy or drifting, what needs attention, and what evidence explains the next action?

The console is not a marketing landing page, an uptime dashboard, or an incident mutation surface. It presents persisted quality, drift, incident, lineage, RCA, optional AI explanation, and execution-reliability evidence without changing the underlying semantics. Missing evidence remains visibly missing; the UI never creates a trend, percentage, incident, or live signal that the data layer did not provide.

## Visual thesis

OpenDQ is a restrained engineering workspace: graphite canvas, cool slate surfaces, quiet borders, compact navigation, and one controlled teal accent. The visual language should feel like a calm operations room—dense enough to investigate, ordered enough to scan, and explicit enough to trust.

The page composition follows operational priority rather than equal-weight cards. A shared shell establishes orientation, a page header names the question, sections establish evidence boundaries, and tables/lists expose the next useful detail. Decoration is subordinate to labels, states, measurements, and links.

Anti-patterns: no glassmorphism, gradients, giant hero headlines, blobs, equal-weight KPI walls, excessive shadows, neon glow, purple SaaS styling, fake charts, invented metrics, development-phase language, or raw JSON as the first explanation of human-readable evidence.

## Semantic tokens

Tokens are semantic so components can change theme without changing meaning. Status is always represented by text plus a shape or icon treatment; color is never the only cue.

| Token | Value | Use |
| --- | --- | --- |
| `--canvas` | `#0b1117` | App background |
| `--canvas-raised` | `#101820` | Header and selected navigation layer |
| `--surface` | `#151f28` | Sections and data surfaces |
| `--surface-subtle` | `#1a2731` | Nested rows and hover layer |
| `--border` | `#2a3a46` | Structural dividers |
| `--border-strong` | `#3b5260` | Focus, active, and emphasized boundaries |
| `--text` | `#e7eef2` | Primary text |
| `--text-secondary` | `#b2c0c8` | Supporting copy and table metadata |
| `--text-muted` | `#81939f` | Tertiary metadata; not for essential content |
| `--accent` | `#67d4c1` | Links, selection, navigation mark, primary emphasis |
| `--accent-soft` | `#163a3c` | Accent background layer |
| `--success` | `#67d4c1` | Healthy, pass, stable, resolved |
| `--warning` | `#e6b65c` | Warn, acknowledged, partial |
| `--danger` | `#f07979` | Fail, drift, open, failed |
| `--info` | `#7eb8e6` | Informational and neutral investigation context |
| `--unknown` | `#a7b5bd` | Unavailable, skipped, insufficient history |

All text and state treatments must remain WCAG-aware: body text targets at least 4.5:1 contrast, large text at least 3:1, focus indicators are visible against both canvas and surfaces, and status backgrounds are never the sole signal.

## Typography and density

Use one familiar system sans for interface text and a restrained monospace only for IDs, slugs, timestamps, code, and measured values where tabular alignment helps. Do not use monospace as a costume. Use fixed product-ui steps: `0.6875rem` metadata, `0.75rem` labels, `0.8125rem` supporting text, `0.9375rem` body, `1.0625rem` section title, `1.375rem` page title, and `1.75rem` top-level emphasis. Headings use tight but readable tracking (never below `-0.03em`) and body copy stays around 65–75 characters where prose is present.

The density target is compact operational reading: 12px–16px section padding, 12px row gaps, 16px–24px between sections, and a clear separation between labels and values. A number is prominent only when it answers the page question; a large metric never replaces its label or evidence context.

## Rhythm, shape, and depth

Use a 4/8px rhythm. Preferred spacing values are 4, 8, 12, 16, 20, 24, 32, and 40px. Use 8px for compact control gaps and 16px/24px for section boundaries.

Use 8px for controls and data rows, 10px for larger sections, and 999px only for small badges. Prefer 1px borders and surface layers to shadows. Shadows are rare and may only support a floating mobile navigation layer; no card should combine a strong border with a decorative heavy shadow.

## App shell geometry

`AppShell` owns the persistent desktop navigation and the mobile navigation. On desktop, the sidebar is 240px wide, fixed to the viewport, with a 1px right border and a compact identity block. Main content starts after the sidebar and uses `width: min(100% - 48px, 1280px)` with 24px/32px gutters. The usable content area is intentionally wider than the former 980px shell so tables and evidence rows do not collapse into marketing cards.

The shell contains a skip link, one `main` landmark per page, a navigation landmark with a visible active state, and a small read-only/environment marker sourced only from truthful app context. Footer copy is quiet and never contains development phase names.

Desktop navigation order: Overview (`/`), Quality (`/quality`), Drift (`/drift`), Incidents (`/incidents`), Lineage (`/lineage`), Reliability (`/reliability`). Active route is conveyed with a filled surface, accent rule/icon, text weight, and `aria-current="page"`.

Mobile hides the sidebar and shows a sticky top bar with identity and a horizontally scrollable, touch-sized navigation row. The row is usable with keyboard and touch, never depends on hover, and exposes the active route with text, icon, and background. The content reading order remains header → status/current state → evidence → investigation links.

## Component rules

### AppShell

Renders the skip link, shell landmarks, identity, navigation, mobile top bar, and read-only marker. It is the only owner of global navigation. Route-aware active state may use a small client component; page content remains server-rendered.

### PageHeader

Uses a concise title, one sentence of operational context, and optional contextual links. No eyebrow is required; if a label is useful it must be short and subordinate. The title answers the surface question, not an implementation phase. A header may include a compact status summary, but never a hero block or marketing claim.

### StatusBadge

Accepts the persisted status vocabulary and renders readable text plus a status glyph/shape. Variants include healthy/success, warning/partial, danger/failure, info, and unknown. Status badges are compact, never used as unlabeled color dots, and preserve the raw status when it is meaningful.

### Metric / Stat

Shows one value, a plain-language label, and the evidence window or qualifier when needed. Null values render as `Not available` or `Insufficient history`, never a made-up zero. Use a metric only when it helps answer the page question; prefer a summary strip or table context to isolated marketing tiles.

### Section

Groups one evidence concern with a heading, optional count/status, and a predictable body. Use a border and surface layer, not a floating card aesthetic. Section headings have more space above than below. Nested sections are avoided unless they reveal a meaningful evidence hierarchy.

### Table / List

Use semantic `<table>` for multi-column evidence and a semantic list/article pattern for incident rows or grouped flows. Put failed/warned/open items first when the data supports it; healthy/resolved details are visually subordinate, never hidden. Every row has a readable primary label and secondary IDs only when useful. On mobile, tables either become stacked labeled rows or scroll inside an explicitly bounded region without causing page-wide horizontal overflow.

### EmptyState

States what is absent, why that is honest, and what the visitor can inspect next. Copy is user-facing; pipeline commands and migration instructions belong in documentation. Empty states distinguish unavailable data, insufficient baseline/history, and genuinely empty healthy results.

### EvidenceRow

Renders a human-readable key/value pair or evidence item with label, value, and optional provenance. Keep raw JSON behind a `<details>` disclosure when retained. Evidence IDs, source tables, algorithm versions, and fingerprints are secondary metadata.

### Timeline

Renders lifecycle events in chronological order with a vertical rule, event type, message, status transition, and timestamp. The rule is structural, not decorative; each event remains legible without color.

### LineageNode

Uses a clear node label, node type, description/slug secondary line, and an explicit connector or staged flow. Source → dataset → process → API → dashboard is the default reading direction. Nodes and downstream impact links must make blast radius obvious without a graph library.

## Status vocabulary

Keep persisted vocabulary intact and translate only the display label where clarity improves it.

- Platform: `Operational`, `Degraded`, `Unavailable`.
- Quality: `PASS`, `WARN`, `FAIL`, `ERROR`, `UNKNOWN`, `SKIPPED`.
- Drift: `STABLE`, `WARN`, `DRIFT`, `ERROR`, `SKIPPED`.
- Incidents: `OPEN`, `ACKNOWLEDGED`, `RESOLVED`.
- Reliability: `SUCCESS`, `PARTIAL`, `FAILED`, `NO_BASELINE`, `UNAVAILABLE`.
- Optional AI: `SUCCESS`, `FALLBACK`, `FAILED`, `SKIPPED`; AI is explanatory and never authoritative.

Do not collapse quality, drift, incident, and execution outcomes into one score. Explain deterministic versus optional AI semantics once per relevant surface, with short detail text or disclosure rather than repeated defensive paragraphs.

## Surface hierarchy

Overview answers operational → data state → incidents → datasets → next investigation. Quality leads with dataset summary, then failed/warned rules, then passed rules. Drift groups by dataset and shows status, feature/method, observed metric versus threshold, baseline version, sample counts, and evaluation time. Incidents are a compact list/table with open items first and severity/status/dataset/rule/last seen/occurrences visible. Incident detail uses summary strip → deterministic RCA → human-readable evidence → blast radius → lifecycle → optional AI explanation, with raw JSON disclosed. Lineage makes staged dependencies and downstream impact visually legible. Reliability presents the measured window, execution evidence, latest data outcomes, and incident counts as separate operational facts.

## Responsive behavior

Breakpoints: mobile below 720px, compact desktop from 720px to 1023px, and full desktop at 1024px+. The sidebar is visible at 1024px+, while 720px–1023px uses the mobile top navigation to protect content width. At 720px and below, columns stack, action links wrap, table rows become labeled blocks, and the reading order stays operationally correct. At 390px wide there must be no page-level horizontal overflow and all interactive targets should be roughly 40–44px tall.

## Interaction and motion

Links and controls use the accent only for action/selection. Hover changes surface or underline without layout shift. `:focus-visible` uses a 2px accent outline with a 2px offset. Active navigation has a persistent non-color treatment. Interactive disclosure rows show an affordance and remain keyboard operable. Motion is optional and only communicates state/reveal; keep it within 150–250ms and honor `prefers-reduced-motion: reduce` by removing transitions.

## Accessibility contract

Use semantic landmarks, a single meaningful `h1`, ordered headings, native links and disclosure controls, explicit table headers, readable timestamps, and `aria-current` for navigation. Provide a skip link to `main`. Do not rely on hover, color, or icon shape alone. Preserve focus order and visible focus. Keep labels and values understandable when CSS is unavailable. Avoid live regions for static persisted data; use them only if a future interaction genuinely changes content.

## Do-not-touch boundary

This is a presentation contract. It does not authorize changes to Python pipeline behavior, SQL migrations, Neon schema, provider routing, incident semantics, quality/drift calculations, API response contracts, read-only boundaries, public mutation handlers, public AI inference handlers, or Cloudflare/deployment dependencies. Tests should assert UX semantics and navigation without coupling to decorative class names.
