# Ingestion & Matching Roadmap

Captured 2026-07-27. Two tracks, sequenced by leverage and by whether the step needs a schema change. Every phase below was checked against that constraint before being scoped.

```
Track A (schema-free, do first)     Track B (needs schema, do later)
─────────────────────────────      ─────────────────────────────
Phase 1: Ingestion correctness  →   Phase 3: Event instrumentation
Phase 2: Structured filtering   →   Phase 5: Hybrid embeddings
Phase 4: Offline eval set       →   Phase 6: Learning to rank
```



## Phase 1 — Ingestion correctness (no migration) — IN PROGRESS

The ingestion foundation now reads exact `careers_url` values from the database,
routes each allowlisted feed to one registered adapter, stores every valid public
posting, and upserts idempotently on the existing job URL constraint. The YAML
catalog is seed input only and can be removed later without changing the runtime.

HTTP responses are streamed through a configurable decoded-body limit. Redirects
are validated and closed hop by hop, transient failures are retried, and one
company's failure cannot abort another company's persistence. Global and provider
semaphores bound concurrent company fetches; provider capacity is acquired first
so a busy provider cannot reserve idle global slots.

Every pass now returns an ephemeral structured report with a correlation ID,
timing, safe company-level warnings/errors, and Provider Ingestion Health summaries.
The CLI renders it for operators or emits complete JSON; no scan history is
persisted.

1. **Move filtering from ingestion time to read time — completed.** Ingestion
   stores the full provider inventory. User roles, skills, locations, work mode,
   and salary preferences belong to `search_service.get_results` and later
   matching phases, never the global write path.
2. **Decouple scanning from the request path.** `POST /search/run` is currently
  callable by any authenticated user and triggers a full scan. Fix: in-process
   APScheduler (`AsyncIOScheduler`) in the FastAPI lifespan, running
   `run_scan_locked()` on
   an interval (`scan_interval_hours` setting), with `max_instances=1`,
   `coalesce=True`, and an immediate first run on boot. (This exact pattern existed
   before on `feat/pipeline-scheduler`/`feat/job-search`, but those branches predate
   the 2026-07-18 ERD refactor and still reference the dropped `Source`/`JobScore`
   models — don't merge them, re-implement the pattern against the current schema.)
3. **Collapse cross-source duplicates at read time.** CLAUDE.md already documents
  the rule — read paths must collapse jobs on normalized `(company_id, title,  location)` — but `get_results` doesn't do it. Real bug, not just a nice-to-have.
   Keep the collapse *display-time only* (never merge/delete underlying rows) since
   the key is advisory — two genuinely different reqs can share title + location.
4. **Derive closure/staleness from** `updated_at`, not a new lifecycle column.
  `upsert_job` already bumps `updated_at` on every sighting. A job whose
   `updated_at` hasn't moved in N scan intervals is treated as closed at read time.
   This isn't just a workaround for the schema constraint — per live-verified
   ATS capabilities, only Greenhouse exposes a real per-job update signal; Ashby
   and Lever only have creation timestamps, so staleness-by-`updated_at` is the
   only uniform closure signal across all three providers regardless.
5. **Normalize URLs before the uniqueness check** (strip tracking params, trailing
  slash) to reduce accidental same-source duplicate rows.

### Successful-snapshot field policy

Descriptions, locations, posting dates, and deadlines currently retain an older
non-null value when a successful provider snapshot omits them. Salary is different:
a successful snapshot replaces both salary columns, including with `NULL`. This
allows employer removals and salary-parser corrections to clear stale or false
values. A failed provider fetch never reaches the upsert and therefore preserves
the stored salary.

The current `RawJob` contract cannot distinguish "explicitly absent" from
"present but unparseable." If transient omissions become common, add a three-state
salary result (`present`, `absent`, `unknown`) and provenance before changing the
SQL policy. Blindly coalescing salary would retain known bad values indefinitely.

Explicitly deferred (needs a real migration — revisit only if these become true):
a `job_sources` table / `(job_source_id, external_job_id)` identity — needed if a
company migrates ATS providers and reissues all its URLs at once; a `scan_runs`
observability table — needed if you want to answer "did a board silently return
empty for a week" (staleness-by-`updated_at` can't distinguish that from a broken
fetch).

## Phase 2 — Structured filtering on the read path (schema-light)

Replace the global `companies.yaml` title/location filter (one developer's
preferences, applied to every user) with real profile fields: desired locations,
work mode, seniority, minimum salary. Schema-free *if* those fields already exist
on `Profile` from onboarding — check before assuming. Apply as soft signals where
data is missing (no salary listed ≠ below minimum), not hard rejections.

## Phase 3 — Event instrumentation (needs schema)

Impressions, clicks, saves, hides, applies. First phase where a new table is
unavoidable — "was this job shown but ignored" can't be computed without recording
that it was shown.

## Phase 4 — Offline evaluation set (schema-free)

Hand-label representative profile/job pairs; score keyword-only vs. structured vs.
(eventually) hybrid retrieval with Recall@K / NDCG@K. Pure offline scripting. This
is what tells you whether Phase 5 is worth its complexity, instead of adding
embeddings on faith.

## Phase 5 — Hybrid embeddings (needs schema + infra)

pgvector + embedding columns. Split `intent` (desired roles/seniority/career
direction) from `experience` (employment/projects/skills) embeddings rather than
one undifferentiated profile vector — otherwise a person's work history
over-recommends their previous profession instead of where they want to go next.
Compare intent↔role and experience↔requirements separately. Only pursue if Phase 4
shows keyword+structured isn't enough.

## Phase 6 — Learning to rank (needs Phase 3's data)

Train a small ranker on real interaction outcomes once there's enough of them.
Optimize toward completed/qualified applications, not raw clicks.

## Comparable-platform takeaways (for later phases, not gospel)

- **LinkedIn**: separates retrieval from ranking; multi-objective (engagement,
qualification, employer value), not one similarity score.
- **Indeed**: hard-filters obvious mismatches first; behavioral embeddings are one
*feature* in a ranker, not a replacement for structured signals.
- **ZipRecruiter**: normalized title taxonomy is reportedly one of their highest-
value features — worth prioritizing title normalization whenever Phase 2/5 land.
- Vendor-reported metrics only, not independently audited — treat as directional,
not a target to hit.
