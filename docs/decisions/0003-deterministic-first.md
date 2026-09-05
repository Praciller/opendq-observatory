# ADR 0003: Deterministic first

## Context

Public APIs change and are not appropriate dependencies for repeatable CI.

## Decision

Use compact checked-in fixtures and injected HTTP transports in tests; keep live source smokes separate.

## Consequences

CI is reproducible and failure paths are testable. Live availability must be reported separately from automated test status.

## Alternatives

Calling public APIs in CI was rejected because it creates flaky, rate-sensitive tests.

