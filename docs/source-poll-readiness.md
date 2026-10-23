# Source poll readiness

The public read-only `GET /api/readiness` endpoint evaluates the age of each
enabled source's latest persisted **successful poll** (status `SUCCESS` or
`NO_CHANGE`). It is separate from `GET /api/health`, which checks database
reachability only.

## Interpretation

- `CURRENT`: last successful poll is at most 12 hours old.
- `STALE`: the last successful poll is older than 12 hours.
- `NO_HISTORY`: no successful poll is recorded.
- `DISABLED`: excluded from enabled-source readiness.
- `INVALID_TIME`: stored timestamp is invalid or more than five minutes in the future.
- No enabled sources: `degraded` rather than falsely healthy.
- Database or source lookup unavailable: `unavailable`.

HTTP 200 means all enabled sources are `CURRENT`. HTTP 503 means `degraded`
or `unavailable`; responses are not cached. This is a **poll-recency**
health signal, not a data-quality or event-time freshness assessment.
A `NO_CHANGE` poll can be current while the dataset remains stale under
the data-quality rules.

The 12-hour threshold provides headroom for a six-hour GitHub Actions
scheduler, including typical queue delays. Consider alerting on sustained
`degraded` results from an external observer; no provider credentials,
notifications, mutations, or new billable monitoring service are introduced.

This endpoint does not change the existing SLO history query or claim
continuous uptime measurement. It is an on-demand assessment.
