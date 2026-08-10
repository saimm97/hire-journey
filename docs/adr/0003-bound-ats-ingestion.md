# ADR-0003: Bound and isolate ATS ingestion

- Status: Accepted
- Date: 2026-07-28
- Decision scope: public ATS fetching and job snapshot persistence
- Related roadmap: [Ingestion and matching](../architecture/ingestion-matching-roadmap.md)

## Context

Hire Journey ingests complete public boards before applying user-specific
matching. The first implementation had the right adapter boundary and URL-keyed
upsert, but several operational rules were distributed across modules. HTTPX
buffered a response before checking its configured size, provider concurrency
was a second registry that could drift from the adapters, provider waiters could
occupy global capacity, and URL safety checks were duplicated.

The jobs table already supports this ingestion phase. These safeguards must not
introduce a migration or make runtime scanning depend on the temporary YAML seed
catalog.

## Decision

1. Read scannable companies and their exact `careers_url` values from the
  database. Route each HTTPS feed to exactly one adapter through an allowlisted
   feed hostname. YAML remains an optional seed/import source only.
2. Maintain one source registration containing the adapter and its provider
  concurrency limit. Derive adapter and hostname indexes from it and fail fast
   on invalid names, limits, or duplicate hosts.
3. Bound company fetches with provider and global semaphores, acquired in that
  order. A running fetch retains both permits during retry backoff so a degraded
   provider remains conservatively bounded.
4. Share one URL policy for feed routing, initial requests, and every redirect:
  HTTPS, no credentials, default/443 port, and an explicit provider allowlist at
   fetch time.
5. Stream response bodies and stop once the decoded-byte limit is crossed.
  Inspect declared length before reading, close every response on all exit
   paths, and retry transport failures that occur during connection or body read.
6. Keep timeout, response size, attempts, global concurrency, and connection-pool
  limits in validated application settings. Retry statuses, redirect bounds,
   parsing expressions, and per-provider policy remain code.
7. Treat a successful feed as authoritative for salary. Incoming `NULL` clears
  prior salary, while a failed fetch performs no upsert and preserves it.



## Consequences



### Positive

- A missing or dishonest `Content-Length` cannot make one response grow the
application buffer without bound.
- Adding an adapter cannot omit a separate concurrency entry and fail every
company as an apparent remote error.
- A saturated provider does not reserve otherwise available global fetch slots.
- Feed routing and redirect protection cannot drift independently.
- Operators can tune resource limits without changing parsing code.
- The runtime can outlive and eventually remove `companies.yaml` unchanged.



### Tradeoffs

- The decoded response still occupies memory up to the configured cap, plus JSON
object overhead, for each active fetch.
- Retry backoff retains concurrency permits and can reduce throughput during a
provider incident; releasing them would require attempt-level scheduling.
- Semaphor.......es limit concurrent operations, not requests per second.
- Eager task creation is acceptable for the current company catalog but should
become a bounded worker queue at materially larger scale.
- `NULL` salary cannot yet distinguish authoritative absence from a parser miss.



## Alternatives considered



### Check response size after `client.get()`

Rejected. HTTPX has already buffered the complete body at that point, so the
check rejects oversized content without protecting process memory.

### Keep one concurrency dictionary per service

Rejected. It makes adapter registration a multi-file operation and turns a
missing entry into a repeated runtime failure instead of a startup error.

### Coalesce salary with the stored value

Deferred until salary has explicit presence/provenance state. Coalescing now
would preserve employer-removed and parser-corrected false values indefinitely.

### Add ingestion lifecycle columns or tables

Deferred. Scan observability, provider IDs, and field provenance deserve a
separate schema decision; none is necessary to bound the current ingestion path.