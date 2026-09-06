# ADR 0011: Route providers with bounded fallback

## Decision

Use Groq as the primary provider and Gemini as the secondary provider, with one
bounded request per provider and deterministic fallback when both are
unavailable. Default models are `openai/gpt-oss-20b` and
`gemini-3.5-flash-lite`. Provider credentials are optional and disabled by
default.

## Rationale

The portfolio deployment targets free-tier operation and must not make
provider availability a prerequisite for deterministic ingestion, RCA, or the
public dashboard. Explicit model defaults, timeouts, call quotas, and
fingerprint caching make cost and failure behavior reviewable.

## Consequences

The service can report `SUCCESS` for a validated provider explanation or
`FALLBACK` for deterministic output. Rate limits and provider failures are
recorded as safe codes without response bodies. Streaming, agents, tool use,
RAG, vector storage, and automatic retries are intentionally deferred.
