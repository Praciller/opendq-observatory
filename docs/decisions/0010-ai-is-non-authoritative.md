# ADR 0010: Keep AI explanations non-authoritative

## Decision

AI output is an optional, persisted explanation of deterministic OpenDQ
evidence. It cannot change incident state, deterministic RCA cause/confidence,
quality/drift results, lineage, or remediation state. The public web surface
only reads persisted analyses; inference runs in the trusted pipeline/CLI.

## Rationale

The project must remain explainable and safe when an AI provider is disabled,
unavailable, rate-limited, or wrong. Deterministic evidence is the source of
truth and remains useful without credentials or paid provider access.

## Consequences

The UI labels AI content as explanatory and keeps deterministic RCA above it.
Provider output is schema-validated, evidence-grounded, bounded, and stored
with a prompt version and deterministic RCA reference. Notifications,
automated remediation, and agentic actions remain outside this phase.
