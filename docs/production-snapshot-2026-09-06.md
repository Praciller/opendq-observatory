# Production usage snapshot

Captured 2026-09-06 from the canonical production database through a secret-safe Vercel environment pull. Counts are evidence for this release candidate and should not be treated as live documentation after the snapshot date.

| Measure | Observed |
| --- | ---: |
| Sources | 2 |
| Datasets | 2 |
| Raw observations | 323 |
| Quality rules, including drift rules | 24 |
| Drift rules | 8 |
| Lineage nodes / edges | 8 / 8 |
| Deterministic RCA analyses | 27 |
| AI analyses | 7 |
| Open incidents | 6 |
| Acknowledged incidents | 0 |
| Resolved incidents | 2 |

Incident groups: `OPEN/DATA_DRIFT=6`, `RESOLVED/DATA_DRIFT=2`.

AI groups: `groq/SUCCESS=1`, `deterministic-fallback/FALLBACK=6`.

Ingestion history in the snapshot: Open-Meteo `SUCCESS=2`, `NO_CHANGE=7`; USGS Earthquakes `SUCCESS=8`, `NO_CHANGE=1`. The scheduled workflow cadence is every six hours (`17 */6 * * *`).

All six open incidents are drift incidents in this snapshot. The AI row counts include one bounded Groq production smoke and six deterministic fallbacks; Gemini was not live-verified.
