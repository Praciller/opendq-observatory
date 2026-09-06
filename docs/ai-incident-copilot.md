# Optional AI Incident Copilot

The AI Incident Copilot is an optional explanation layer over persisted OpenDQ
evidence. It does not open, resolve, acknowledge, reclassify, or remediate an
incident. Deterministic quality, drift, incident lifecycle, lineage, and RCA
results remain authoritative.

## Data boundary

Only `PUBLIC_ONLY` data is eligible for provider calls. The bounded input
contains incident kind/severity/status, dataset slug, deterministic RCA cause
and confidence, selected quality/drift evidence, lineage impact names, and a
20-event timeline. Raw observations, database URLs, API keys, authentication
tokens, and unrestricted source payloads are excluded. Inputs and outputs are
bounded and sanitized before persistence or transport.

The prompt is versioned as `incident-copilot-v1`. Provider output must match a
strict JSON schema, and every highlighted evidence ID must exist in the input.
Provider responses are explanatory text only; they cannot change deterministic
state or cause.

## Providers and routing

Groq is the primary adapter using `openai/gpt-oss-20b` and its OpenAI-compatible
structured-output endpoint. Gemini is the secondary adapter using
`gemini-3.5-flash-lite` and its JSON response schema. The router makes at most
one request per configured provider, in Groq-then-Gemini order, with no
aggressive retry loop. A provider failure is recorded as a bounded error code
without storing the response body.

When providers are disabled, credentials are absent, a provider fails, or the
output cannot be validated, the service persists a deterministic explanation
with status `FALLBACK`. The deterministic pipeline continues successfully.

## Persistence and quotas

`ai_incident_analyses` stores the explanation, provider/model, prompt version,
input fingerprint, deterministic RCA reference, bounded metrics, attempts, and
safe error metadata. It does not store raw prompts or raw provider responses.
The same incident/context/prompt fingerprint is served from cache. Defaults
are eight seconds per request, 3 AI calls per run, 1 call per incident, and
bounded input/output token settings. The scheduled workflow processes at most
three pending active incidents.

## Interfaces

Trusted operators can use:

```powershell
python -m opendq ai pending --limit 10
python -m opendq ai analyze <incident-id>
python -m opendq ai analyze-open --limit 3
python -m opendq ai show <incident-id>
```

The public `GET /api/incidents/<id>/ai` route only reads persisted analyses.
There is no public inference trigger. Incident detail renders the AI section
after deterministic RCA and clearly identifies fallback output and uncertainty.

## Provider references

- [Groq structured outputs](https://console.groq.com/docs/structured-outputs)
- [Groq models](https://console.groq.com/docs/models)
- [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output)
- [Gemini models](https://ai.google.dev/gemini-api/docs/models)
