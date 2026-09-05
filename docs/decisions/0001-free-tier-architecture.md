# ADR 0001: Free-tier architecture

## Context

OpenDQ Observatory is a public portfolio project that should remain useful without paid trials or an always-on backend.

## Decision

Use Vercel Hobby, Neon Free, and scheduled GitHub Actions micro-batches, with Docker Compose PostgreSQL locally.

## Consequences

The design is inexpensive and portable, but ingestion is periodic rather than continuous and production credentials remain owner-managed.

## Alternatives

Always-on workers and paid managed services were rejected for this phase.

