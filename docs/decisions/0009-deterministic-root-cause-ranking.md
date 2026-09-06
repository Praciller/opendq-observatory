# ADR 0009: Rank root causes from persisted evidence deterministically

## Decision

RCA uses a small controlled taxonomy, explicit weights, stable tie ordering, confidence categories, and an algorithm version. It persists each supporting evidence signal and a semantic fingerprint; it does not call an AI provider.

## Rationale

The platform needs explainable incident context before an optional AI copilot. A deterministic layer is cheap, testable, reviewable, and honest about uncertainty. Lineage supplies upstream context and downstream impact, not automatic causality.

## Consequences

The result is a probable cause ranking rather than a proof. Changing scoring logic requires a new algorithm version. Identical semantic evidence does not create duplicate RCA history, while changed evidence remains auditable.
