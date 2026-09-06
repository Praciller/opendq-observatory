# Optional AI Incident Copilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a bounded, optional AI explanation layer for persisted deterministic incident evidence without changing deterministic incident or RCA authority.

**Architecture:** The pipeline will build a sanitized, bounded incident DTO, route one request through Groq and then Gemini, validate the structured response against deterministic evidence, and persist either a provider result or a deterministic fallback. Fingerprints prevent repeated calls for unchanged evidence; the public web surface only reads persisted analyses.

**Tech Stack:** Python 3.12, existing `httpx`, PostgreSQL migrations, argparse CLI, Next.js App Router, TypeScript tests, mocked HTTP transports in CI.

**Spec:** `C:/Users/pakon/.codex/attachments/e1761939-3b28-44e0-bff2-3f42a2854e10/pasted-text.txt`

## Global Constraints

- Deterministic quality, drift, incident, lineage, and RCA state remains authoritative.
- AI is optional, read-only, public-data-only, and must never block deterministic ingestion or reconciliation.
- Providers are Groq primary, Gemini fallback, then deterministic local fallback.
- No agents, tools, RAG, vector database, web search, notifications, remediation, auth, or public inference trigger.
- Provider keys remain server/operator-side and are never stored in source, prompts, or public Vercel environment variables.
- Calls are bounded per run and per incident; unchanged evidence is cached by a stable fingerprint.
- CI uses mocked provider calls only.

---

### Task 1: Configuration and sanitized contracts

**Files:**
- Modify: `pipeline/opendq/config.py`
- Modify: `.env.example`
- Create: `pipeline/opendq/ai/__init__.py`
- Create: `pipeline/opendq/ai/models.py`
- Create: `pipeline/opendq/ai/prompts.py`
- Test: `pipeline/tests/test_ai_models.py`

- [x] Add explicit AI settings, safe defaults, bounded limits, and boolean parsing.
- [x] Define sanitized input, validated output, provider-attempt, and service-result contracts.
- [x] Define prompt version `incident-copilot-v1` and JSON schema with required fields.
- [x] Add failing tests for bounds, secret exclusion, and output shape.
- [x] Run the focused tests and implement the minimal contracts.

### Task 2: Provider adapters and router

**Files:**
- Create: `pipeline/opendq/ai/providers/__init__.py`
- Create: `pipeline/opendq/ai/providers/base.py`
- Create: `pipeline/opendq/ai/providers/groq.py`
- Create: `pipeline/opendq/ai/providers/gemini.py`
- Create: `pipeline/opendq/ai/router.py`
- Create: `pipeline/opendq/ai/validation.py`
- Test: `pipeline/tests/test_ai_router.py`
- Test: `pipeline/tests/test_ai_safety.py`

- [x] Implement direct HTTP adapters with injected `httpx` transports, bounded timeout, no aggressive retry loop, and sanitized error taxonomy.
- [x] Use Groq structured JSON schema mode and Gemini JSON response schema mode.
- [x] Route Groq → Gemini → deterministic fallback without retries on auth errors or aggressive retries on 429.
- [x] Validate evidence IDs, deterministic cause/confidence, bounded lengths, and injection-like source values.
- [x] Add mocked tests for success, 429, auth, malformed output, grounding rejection, and both-provider failure.

### Task 3: Persistence and deterministic fallback

**Files:**
- Create: `db/migrations/006_ai_incident_copilot.sql`
- Create: `pipeline/opendq/ai/repository.py`
- Create: `pipeline/opendq/ai/fallback.py`
- Create: `pipeline/opendq/ai/service.py`
- Modify: `pipeline/tests/test_migrations.py`
- Create: `pipeline/tests/test_ai_persistence.py`

- [x] Add `ai_incident_analyses` with provider/model/prompt/fingerprint/RCA reference, structured output JSON, latency, sizes, cache metadata, sanitized errors, and indexes/uniqueness.
- [x] Build context only from incident, deterministic RCA, quality/drift evidence, lineage impacts, and bounded lifecycle events.
- [x] Generate deterministic fallback summaries and investigation steps from persisted RCA evidence.
- [x] Persist SUCCESS and FALLBACK states without raw prompts/responses or secrets; FAILED/SKIPPED remain schema-supported for provider/system extensions.
- [x] Implement fingerprint cache lookup and deterministic incident prioritization.
- [x] Add migration-from-empty and persistence/cache tests.

### Task 4: CLI and scheduled integration

**Files:**
- Modify: `pipeline/opendq/__main__.py`
- Modify: `.github/workflows/ingest.yml`
- Create: `pipeline/tests/test_ai_cli.py`
- Modify: `pipeline/tests/test_ingestion.py`

- [x] Add `ai analyze`, `ai show`, `ai pending`, and bounded `ai analyze-open` commands.
- [x] Ensure CLI output exposes provider/model/status/prompt version/cache/fallback without credentials.
- [x] Append optional AI analysis after deterministic RCA in the existing six-hour workflow.
- [x] Emit non-sensitive per-result status/cache/fallback output; provider failure falls back without failing deterministic ingestion.
- [x] Add parser and persistence tests covering bounded commands and unchanged-evidence cache behavior.

### Task 5: Read-only API and incident UI

**Files:**
- Create: `apps/web/lib/ai.ts`
- Create: `apps/web/app/api/incidents/[id]/ai/route.ts`
- Modify: `apps/web/app/incidents/[id]/page.tsx`
- Modify: `apps/web/app/globals.css`
- Modify: `apps/web/tests/status.test.ts`

- [x] Add read-only latest-analysis mapping with honest empty/unavailable states.
- [x] Render AI Copilot below deterministic RCA with provider/model/time/fallback labels and evidence highlights.
- [x] Keep GET routes read-only and make no provider calls.
- [x] Add web tests for success/fallback mapping and invalid-ID empty analysis.

### Task 6: Documentation and ADRs

**Files:**
- Create: `docs/ai-incident-copilot.md`
- Create: `docs/decisions/0010-ai-is-non-authoritative.md`
- Create: `docs/decisions/0011-provider-fallback-and-free-tier.md`
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/incidents.md`
- Modify: `docs/root-cause-analysis.md`
- Modify: `docs/data-model.md`

- [x] Document public-only input, deterministic authority, provider routing, fallback, cache, quota, prompt version, validation, and no-inference GET behavior.
- [x] Position the project as deterministic observability with optional AI explanations.

### Task 7: Verification, commit, CI, production, and release

- [ ] Run all local Python/web/security gates with mocked providers.
- [ ] Commit and push `feat/ai-incident-copilot`; wait for feature CI.
- [ ] Merge to `main`; wait for merged CI.
- [ ] Apply migration 006 to Neon through the repository migration command.
- [ ] Generate fallback or provider-backed analyses for at most three real active incidents.
- [ ] Run one controlled remote workflow dispatch and record bounded AI counts.
- [ ] Deploy only the canonical Vercel project and verify all APIs/UI.
- [ ] Run tiny provider live smoke only when configured; otherwise record `NOT_CONFIGURED`.
- [ ] Re-run security/cost checks and produce the required Phase 5 report.
