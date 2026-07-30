# Job ingestion architecture

This document describes the current, schema-free job-ingestion Module. For the
commands used to operate it locally, see the
[job-ingestion runbook](../runbooks/job-ingestion.md). For planned ingestion and
matching work, see the [ingestion and matching roadmap](ingestion-matching-roadmap.md).
The normative machine-readable reporting interface is defined by the
[Ingestion Run Report contract](../contracts/ingestion-run-report.md).

## Purpose and scope

Ingestion builds a shared catalog of public jobs before any user-specific
filtering or scoring takes place. A posting that is irrelevant to one user can
still be relevant to another, so preferences must never discard jobs on the
global write path.

The current Module:

- reads configured ATS feed URLs from the `companies` table;
- fetches Greenhouse, Ashby, and Lever public job boards;
- converts provider payloads into one `RawJob` representation;
- preserves useful provider formatting while removing unsafe HTML;
- stores jobs idempotently using the existing unique URL constraint; and
- isolates provider and persistence failures by company.

It does not yet schedule itself, record durable scan history, determine whether
a missing posting has closed, or calculate personalized recommendations.

## Primary interface

The operator-facing interface is:

```bash
cd backend
python scripts/ingest_jobs.py
```

The script calls `run_scan_locked()`. That function owns the process-independent
PostgreSQL advisory lock, creates its own database session, and calls
`run_scan()`. Callers therefore do not need to know about individual providers,
HTTP clients, concurrency controls, parsing, sanitization, or upsert behavior.

`run_scan_locked()` returns an ephemeral `IngestionRunReport`. The report carries
a correlation ID, timing, run status, provider ingestion health, aggregate
counts, empty-feed warnings, and safe company-level errors. Its summaries and
issues are emitted to operator logs, and no scan-history row is persisted.

The JSON form is a compatibility-managed internal operational contract. It is
intended for backend operators, automation, and future administrative tooling;
it is not returned to job seekers. Human CLI output is a convenience view, not
the contract.

The report distinguishes jobs fetched from jobs successfully upserted, but it
does not distinguish new rows from existing rows that were refreshed.

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
| `ATS_HTTP_TIMEOUT_SECONDS` | `10` | HTTP timeout per operation |
| `ATS_MAX_RESPONSE_MB` | `50` | Maximum decoded response body per company feed |
| `ATS_MAX_ATTEMPTS` | `3` | Maximum attempts for retry-eligible failures |
| `ATS_GLOBAL_CONCURRENCY` | `12` | Maximum active ATS requests across providers |
| `ATS_HTTP_MAX_CONNECTIONS` | `20` | Shared HTTP connection-pool limit |
| `ATS_HTTP_MAX_KEEPALIVE_CONNECTIONS` | `10` | Reusable idle connections retained in the pool |

Provider concurrency limits, retry-eligible statuses, redirect bounds, and
parsing rules remain code-level policy rather than deployment configuration.

## Failure isolation

One company fetch failure returns a failed company result and does not cancel
other provider work. During persistence, each successful company snapshot is
committed independently. If one upsert fails, that transaction is rolled back
and later company results continue.

The advisory lock prevents two application processes from running global
ingestion simultaneously against the same PostgreSQL database. It complements
the in-process concurrency controls; it does not replace them.

Completed runs use one of four statuses: `completed`,
`completed_with_errors`, `failed`, or `skipped`. Provider ingestion health is
derived independently as `healthy`, `warning`, `degraded`, or `unavailable`.
It summarizes Hire Journey's configured feed outcomes, not ATS platform uptime.
Persistence failures degrade the run without falsely marking an external source
as unhealthy.

Error reports use stable provider-independent codes and safe messages. They can
include a sanitized feed URL, exception type, HTTP status, and retry-policy
eligibility, but never provider response bodies, job descriptions, database
parameters, raw URLs, or raw exception messages. See the contract document for
the complete schema, status semantics, taxonomy, and compatibility rules.

## Verification

The ingestion tests cover:

- realistic Greenhouse, Ashby, and Lever fixtures through HTTP, parsing,
  sanitization, persistence, and the public jobs read path;
- repeated-feed URL idempotency;
- response streaming, size limits, redirects, retries, and connection cleanup;
- provider registration and host routing;
- provider fetch and persistence failure isolation;
- run status, provider ingestion health, safe error taxonomy, and empty-feed
  warnings;
- sanitized diagnostic feed URLs and report-field compatibility;
- advisory-lock skip and fatal-run behavior;
- human-readable and JSON operator output;
- nonzero exit behavior for partial and fatal failures;
- preservation of the public `/search/run` response contract;
- salary extraction and successful-snapshot replacement;
- bulk-upsert chunking; and
- persistence failure isolation.

See `backend/tests/test_provider_ingestion.py`, `test_job_ingestion.py`,
`test_ingestion_cli.py`, `test_ingestion_report.py`,
`test_search_run_reporting.py`, `test_fetch_json.py`, `test_fetch_service.py`,
and `test_sources.py`.

## Known gaps

The current implementation intentionally leaves these items open:

- twice-daily scheduling (HIJ-15);
- bounded incremental fetch-and-persist workers instead of retaining every
  company result until all fetching completes;
- repeatable company-feed health reporting (HIJ-16);
- URL canonicalization before uniqueness checks (HIJ-17);
- per-field payload limits and richer malformed-record counters (HIJ-18);
- closed-job/staleness treatment on read paths; and
- cross-provider duplicate presentation on read paths.

Do not merge the old `feat/pipeline-scheduler` implementation into this Module.
That branch targets removed database models and older ingestion interfaces. Its
APScheduler pattern can be reimplemented against `run_scan_locked()` when the
scheduling ticket is taken up.
