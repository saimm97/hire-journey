# Job ingestion architecture

This document describes the current, schema-free job-ingestion Module. For the
commands used to operate it locally, see the
[job-ingestion runbook](../runbooks/job-ingestion.md). For planned ingestion and
matching work, see the [ingestion and matching roadmap](ingestion-matching-roadmap.md).

## Purpose and scope

Ingestion builds a shared catalog of public jobs before any user-specific
filtering or scoring takes place. A posting that is irrelevant to one user can
still be relevant to another, so preferences must never discard jobs on the
global write path.

The current Module:

- reads configured ATS feed URLs from the `companies` table;
- schedules global scans twice daily through Celery Beat and Redis;
- fetches Greenhouse, Ashby, and Lever public job boards;
- converts provider payloads into one `RawJob` representation;
- preserves useful provider formatting while removing unsafe HTML;
- stores jobs idempotently using the existing unique URL constraint; and
- isolates provider and persistence failures by company.

It does not yet record durable scan history, determine whether a missing posting
has closed, or calculate personalized recommendations.

## Execution interfaces

The normal execution path is operator-controlled infrastructure:

```text
Celery Beat ── publishes at 07:00 and 15:00 UTC ──► Redis broker
                                                        │
                                                        ▼
                                         ingestion-queue Celery worker
                                                        │
                                                        ▼
                                                run_scan_locked()
```

Beat publishes `hire_journey.ingest_jobs` twice daily. A dedicated worker
consumes the `ingestion` queue and invokes `run_scan_locked()`. The FastAPI
process does not schedule or execute scans, and there is no user-facing HTTP
endpoint for starting ingestion. Starting Beat does not trigger an immediate
scan; the first run occurs at the next configured schedule slot.

The schedule uses UTC explicitly, so the two slots are `07:00` and `15:00` UTC
regardless of the host timezone. Exactly one Beat process must run for this
application. Multiple Beat instances can publish duplicate tasks.

Redis database `0` is the default broker and Redis database `1` is the default
result backend. Separating the logical databases prevents result keys from
sharing the broker namespace, but both defaults still use the same Redis
server. Task results expire after one hour.

The operator-facing fallback interface is:

```bash
cd backend
python scripts/ingest_jobs.py
```

The script calls `run_scan_locked()`. That function owns the process-independent
PostgreSQL advisory lock, creates its own database session, and calls
`run_scan()`. Callers therefore do not need to know about individual providers,
HTTP clients, concurrency controls, parsing, sanitization, or upsert behavior.
The Celery task is a thin adapter around the same function, so scheduled and
manual scans share one ingestion implementation and one locking policy.

`run_scan_locked()` currently returns one integer: the number of jobs fetched
and successfully upserted during the run. It does not distinguish new rows from
existing rows that were refreshed.

## Processing flow

```text
companies.careers_url
        │
        ▼
source registry ── selects exactly one provider Adapter
        │
        ▼
shared bounded HTTP fetching
        │
        ▼
provider payload ── Adapter parsing ── RawJob
        │
        ▼
HTML sanitization and field normalization
        │
        ▼
URL-keyed PostgreSQL upsert into jobs
```

The runtime reads every company whose `careers_url` is non-null. It does not
read `companies.yaml` during a scan. That file is only an input to the current
seed/import command and can be replaced later without changing ingestion.

Fetching is concurrent. The implementation first waits for a provider permit
and then a global permit, so a saturated provider does not occupy global
capacity needed by another provider. All fetch results are currently collected
before company snapshots are persisted sequentially and committed separately.

## Provider Adapters

Every provider Adapter satisfies the `JobSource` interface and is registered in
the single `SOURCE_REGISTRY`. The registration contains both the Adapter and its
provider concurrency limit. Host routing and compatibility lookups are derived
from this registry, preventing provider policy from drifting across files.

| Provider | Feed shape | Current extraction behavior |
| --- | --- | --- |
| Greenhouse | `{ "jobs": [...] }` with `content=true` | Description HTML, title, URL, location, first-published date, application deadline, and structured or textual salary |
| Ashby | `{ "jobs": [...] }` with `includeCompensation=true` | Listed jobs, description HTML, primary and secondary locations, publication date, and annual structured or textual salary |
| Lever | Root JSON array | Description sections, primary and additional locations, millisecond creation timestamp, and annual structured or textual salary |

Adding another provider requires a new Adapter and one registry entry. The new
Adapter owns only provider-specific URL construction and response parsing;
shared fetching, safety, retry, concurrency, and persistence behavior stays
behind the existing interfaces.

## Feed and network safety

Every feed and redirect target must satisfy the shared URL policy:

- HTTPS only;
- no embedded credentials;
- no nonstandard port; and
- a hostname explicitly claimed by the selected provider Adapter.

The shared HTTP implementation:

- reuses a bounded keep-alive connection pool;
- applies the configured HTTP timeout;
- retries transport errors and HTTP `429`, `500`, `502`, `503`, and `504`;
- validates every redirect hop;
- reads response bodies as a stream; and
- stops reading once the decoded response-size limit is exceeded.

A malformed response envelope fails that company fetch. A malformed individual
record is skipped so healthy sibling records can still be ingested. Errors do
not include response bodies or job descriptions in logs.

## Persistence and idempotency

`jobs.url` is the current identity key. Before database work, duplicate URLs in
one provider response are collapsed. PostgreSQL then performs
`ON CONFLICT (url) DO UPDATE`, so repeating a scan refreshes an existing row
instead of inserting another one.

Current successful-snapshot merge rules are:

- title always uses the latest valid value;
- description, location, posting date, and deadline retain the stored value
  when the new value is null;
- salary is authoritative and can be cleared by a successful snapshot; and
- `updated_at` moves on every successful sighting.

A failed fetch never reaches the upsert and therefore cannot clear stored
fields. URL normalization beyond trimming whitespace is tracked separately and
has not been implemented yet.

Provider descriptions are sanitized before persistence. Semantic tags such as
headings, paragraphs, and lists are retained, while scripts, embedded content,
event handlers, provider styling, and unsafe link protocols are removed.

## Configuration

Operational values come from environment variables through `app/config.py`.
The checked-in defaults are suitable for local development.

| Environment variable | Default | Meaning |
| --- | ---: | --- |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis connection used to publish and consume tasks |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/1` | Redis connection used for task state and short-lived results |
| `ATS_HTTP_TIMEOUT_SECONDS` | `10` | HTTP timeout per operation |
| `ATS_MAX_RESPONSE_MB` | `50` | Maximum decoded response body per company feed |
| `ATS_MAX_ATTEMPTS` | `3` | Maximum attempts for retryable failures |
| `ATS_GLOBAL_CONCURRENCY` | `12` | Maximum active ATS requests across providers |
| `ATS_HTTP_MAX_CONNECTIONS` | `20` | Shared HTTP connection-pool limit |
| `ATS_HTTP_MAX_KEEPALIVE_CONNECTIONS` | `10` | Reusable idle connections retained in the pool |

The twice-daily schedule, task routing, acknowledgement policy, result expiry,
provider concurrency limits, retryable statuses, redirect bounds, and parsing
rules remain code-level policy rather than deployment configuration. Changing
the schedule therefore requires a code change and a Beat restart.

## Failure isolation

One company fetch failure returns a failed company result and does not cancel
other provider work. During persistence, each successful company snapshot is
committed independently. If one upsert fails, that transaction is rolled back
and later company results continue.

The advisory lock prevents two application processes from running global
ingestion simultaneously against the same PostgreSQL database. It complements
the in-process concurrency controls; it does not replace them. The lock applies
across scheduled workers and the manual CLI fallback. A second task that reaches
the lock while a scan is active exits as skipped rather than starting another
global scan.

The Celery worker acknowledges ingestion tasks after execution, rejects tasks
when a worker is lost, prefetches one task at a time, and tracks the started
state. Production deployments should use a dedicated `ingestion` worker with
concurrency `1`; the PostgreSQL advisory lock remains the final cross-process
safety mechanism.

## Verification

The ingestion tests cover:

- realistic Greenhouse, Ashby, and Lever fixtures through HTTP, parsing,
  sanitization, persistence, and the public jobs read path;
- repeated-feed URL idempotency;
- response streaming, size limits, redirects, retries, and connection cleanup;
- provider registration and host routing;
- provider fetch and persistence failure isolation;
- salary extraction and successful-snapshot replacement;
- bulk-upsert chunking; and
- persistence failure isolation;
- Celery task discovery, schedule, and `ingestion` queue routing;
- task success, lock-contention, error, and resource-cleanup behavior; and
- absence of a user-triggerable ingestion route.

See `backend/tests/test_celery_app.py`, `test_ingestion_task.py`,
`test_search_ingestion_access.py`, `test_provider_ingestion.py`,
`test_job_ingestion.py`, `test_fetch_json.py`, `test_fetch_service.py`, and
`test_sources.py`.

## Known gaps

The current implementation intentionally leaves these items open:

- structured run outcomes and provider-level counters (HIJ-14);
- bounded incremental fetch-and-persist workers instead of retaining every
  company result until all fetching completes;
- repeatable company-feed health reporting (HIJ-16);
- URL canonicalization before uniqueness checks (HIJ-17);
- per-field payload limits and richer malformed-record counters (HIJ-18);
- closed-job/staleness treatment on read paths; and
- cross-provider duplicate presentation on read paths.

The scheduling decision and operational tradeoffs are recorded in
[ADR-0004](../adr/0004-celery-redis-ingestion-scheduling.md). The previous
in-process APScheduler proposal is superseded: scheduling now remains outside
the FastAPI lifecycle and uses Celery Beat, Redis, and a dedicated worker.
