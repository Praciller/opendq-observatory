# ADR 0004: Neon PostgreSQL

## Context

Production storage needs PostgreSQL compatibility without a provider-specific API.

## Decision

Target Neon through standard PostgreSQL `DATABASE_URL` and keep SQL migrations visible.

## Consequences

Local Docker PostgreSQL and Neon share the same schema path. Neon project creation and credentials remain owner-authorized deployment work.

## Alternatives

Supabase-specific APIs, SQLite production persistence, and Cloudflare D1 were rejected for portability or project-scope reasons.

