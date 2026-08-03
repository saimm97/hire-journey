# ADR-0004: Schedule ingestion with Celery and Redis

- Status: Accepted
- Date: 2026-08-03

## Context

Job ingestion is a global catalog-maintenance operation. It fetches every
configured company feed and writes shared job records, so it must not be
triggerable by ordinary users or coupled to the lifecycle of an HTTP request.

The system already exposes `run_scan_locked()` as the process-independent entry
point. Its PostgreSQL advisory lock prevents scheduled and manual callers from
running global scans concurrently. The remaining requirement is to start scans
twice daily through operator-owned infrastructure while retaining a simple
recovery path.

Running a scheduler inside FastAPI would tie scan delivery to web-process
restarts and replicas. In a multi-replica deployment, every web process could
start its own scheduler unless additional leader-election infrastructure were
added.

## Decision

Use Celery with Redis to schedule and execute ingestion:

- Celery Beat is the scheduler and publishes `hire_journey.ingest_jobs` at
  `07:00` and `15:00` UTC.
- Exactly one Beat process runs for the application.
- Redis database `0` is the default task broker. Redis database `1` is the
  default result backend, and task results expire after one hour.
- A dedicated Celery worker consumes only the `ingestion` queue. Local
  development uses the `solo` pool; production should use a supervised worker
  with concurrency `1`.
- The task is a thin synchronous adapter around `run_scan_locked()`. Scheduled
  execution and `backend/scripts/ingest_jobs.py` therefore share the same scan
  behavior and PostgreSQL advisory lock.
- Tasks use late acknowledgement, reject-on-worker-loss, prefetch `1`, and
  started-state tracking. The advisory lock remains the final protection
  against concurrent global scans and duplicate delivery.
- The worker closes the shared HTTP client and disposes the asynchronous
  database engine before its task event loop closes.
- FastAPI neither schedules nor runs ingestion. There is no user-facing HTTP
  endpoint that triggers a global scan.
- Starting Beat does not enqueue an immediate scan. It waits for the next fixed
  UTC slot. An operator uses the CLI fallback when an immediate scan is needed.

Redis, the worker, and Beat are independently operated processes. The web API
and frontend do not need to be running for scheduled ingestion to succeed.

## Consequences

The scheduler is independent of HTTP traffic and web-server replica count.
Operators can restart or scale the API without creating additional schedulers,
and failed web requests cannot interrupt a scan.

Deployments now require durable Redis connectivity plus supervised Beat and
worker processes. Monitoring must cover all three components, not only the API.
Running more than one Beat instance can publish duplicate tasks; the database
lock prevents concurrent scans but does not eliminate the duplicate delivery.

The fixed UTC schedule is predictable across hosts and daylight-saving changes,
but its local wall-clock time varies by region. The two daily gaps are eight and
sixteen hours rather than evenly spaced twelve-hour intervals.

Celery task results are available briefly for operational inspection, but they
are not durable scan history. Provider-level counters and long-term run auditing
remain future work.

## Alternatives considered

### APScheduler inside FastAPI

Rejected because scheduling would depend on the web process and require
coordination across API replicas. It also makes a deployment or autoscaling
event part of the ingestion scheduling model.

### System cron running the CLI directly

Viable for a single host, but it offers weaker portability, task visibility,
and worker supervision than the selected queue-based topology. The CLI remains
the manual recovery path.

### User-triggered HTTP ingestion

Rejected because global ingestion is an operator responsibility, is expensive,
and should not consume the lifecycle of an HTTP request or be available to
ordinary authenticated users.
