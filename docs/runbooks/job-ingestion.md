# Operate scheduled job ingestion

Hire Journey refreshes its global catalog from every supported ATS feed stored
in `companies.careers_url`. Celery Beat publishes the scan twice daily, Redis
delivers it, and a Celery worker executes the existing globally locked ingestion
Module.

Ingestion is operator-controlled. There is no HTTP endpoint that lets an
application user start a scan. `scripts/ingest_jobs.py` remains available as an
immediate and recovery fallback for an operator with backend shell access.

## Runtime topology

```text
Scheduled path

Celery Beat (exactly one)
        │  07:00 and 15:00 UTC
        ▼
Redis database 0 (broker)
        │  ingestion queue
        ▼
Celery worker (one or more)
        │
        ▼
app.tasks.ingestion.ingest_jobs_task
        │
        ▼
run_scan_locked() ── PostgreSQL advisory lock ── ATS fetch and upsert
        │
        ▼
Redis database 1 (result retained for one hour)

Manual fallback

operator → python scripts/ingest_jobs.py → run_scan_locked()
```

FastAPI does not host or start Beat or the worker. Scheduled ingestion continues
when the web server and frontend are stopped, provided PostgreSQL, Redis, Beat,
and a worker remain available.

## Prerequisites

All of the following must be true before the schedule can succeed:

1. Python 3.13 is installed and the backend virtual environment was prepared
   with `pip install -r requirements-dev.txt`. That file includes the runtime
   requirements, including `celery[redis]`.
2. PostgreSQL is reachable through `DATABASE_URL`, migrations are at the current
   head, and the database contains companies whose `careers_url` is non-null.
3. Redis is reachable through both `CELERY_BROKER_URL` and
   `CELERY_RESULT_BACKEND`. The defaults use logical databases 0 and 1 on the
   same local Redis instance.
4. At least one worker consumes the dedicated `ingestion` queue.
5. Exactly one Beat process publishes the schedule. Multiple Beat processes can
   publish duplicate messages; the PostgreSQL lock prevents overlap but does not
   justify redundant schedules.
6. The worker can make outbound HTTPS requests to the registered Greenhouse,
   Ashby, and Lever feed hosts.
7. The worker and Beat start from `backend/`, or otherwise receive all required
   environment variables explicitly. `Settings(env_file=".env")` resolves the
   file relative to the process working directory.
8. The host clock is synchronized. Celery evaluates this schedule in UTC.

The AI provider keys are not required for job ingestion.

## One-time local setup

### 1. Start PostgreSQL

If the existing container has already been created:

```bash
docker start career-engine-db
```

Otherwise follow the database setup in the root `README.md`.

### 2. Start Redis

Create the development container once:

```bash
docker run -d \
  --name hire-journey-redis \
  -p 127.0.0.1:6379:6379 \
  -v hire-journey-redis-data:/data \
  redis:8-alpine \
  redis-server --appendonly yes
```

On later sessions:

```bash
docker start hire-journey-redis
```

Verify Redis before starting Celery:

```bash
docker exec hire-journey-redis redis-cli ping
# PONG
```

The loopback-only port binding is appropriate for local development. Do not
expose an unauthenticated production Redis server to the public network.

### 3. Prepare the backend

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
```

Do not overwrite an existing `.env`. At minimum it must contain:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/career_engine
SECRET_KEY=replace-with-a-local-secret
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### 4. Seed or refresh company feed URLs

Edit `backend/config/companies.yaml` with supported provider slugs:

```yaml
companies:
  - name: Example Company
    source: greenhouse
    slug: example-company
```

Then run from `backend/`:

```bash
python scripts/seed_companies.py
```

The seed command validates slugs, builds authoritative feed URLs, and upserts
matching companies. The runtime scan reads `companies.careers_url` from
PostgreSQL; it never reads the YAML catalog directly. Supported providers are
`greenhouse`, `ashby`, and `lever`.

Confirm that at least one company is scannable:

```sql
SELECT id, name, careers_url
FROM companies
WHERE careers_url IS NOT NULL
ORDER BY name;
```

## Start automatic scheduling locally

Use two terminals in addition to PostgreSQL and Redis. Run both commands from
`backend/` with `.venv` active.

### Terminal 1: ingestion worker

```bash
celery \
  -A app.celery_app:celery_app \
  worker \
  --loglevel=INFO \
  --queues=ingestion \
  --pool=solo
```

`--pool=solo` is the simplest local development pool and executes one task at a
time in the worker process.

### Terminal 2: Celery Beat

```bash
celery -A app.celery_app:celery_app beat --loglevel=INFO
```

Run exactly one Beat process. Its local `celerybeat-schedule` state file is
ignored by Git and must be writable by the Beat process.

The configured schedule is:

| UTC time | Pakistan Standard Time (UTC+05:00) |
| --- | --- |
| `07:00` | `12:00` |
| `15:00` | `20:00` |

This is twice per calendar day, with an 8-hour gap followed by a 16-hour gap.
Beat waits for the next scheduled time after startup; it does not enqueue an
immediate first scan.

## Verify the scheduler before waiting for a scan

With the worker running:

```bash
celery -A app.celery_app:celery_app inspect ping
celery -A app.celery_app:celery_app inspect registered
celery -A app.celery_app:celery_app inspect active
```

Expected checks:

- `inspect ping` reports at least one online worker;
- `inspect registered` includes `hire_journey.ingest_jobs`; and
- the worker startup log shows it is consuming the `ingestion` queue.

Beat logs a line containing `Sending due task` at each configured time. The
worker then logs either a completed result or a lock-held skip.

## Run an immediate operator scan

Use the broker-independent CLI fallback when initial data is needed before the
next scheduled slot, while troubleshooting Beat, or during recovery:

```bash
cd backend
source .venv/bin/activate
python scripts/ingest_jobs.py
```

A successful command ends with output similar to:

```text
Done — jobs fetched and upserted: 20341
```

If the scheduled worker already owns the advisory lock:

```text
Skipped — another job-ingestion run already holds the lock
```

The CLI and Celery worker both call `run_scan_locked()`, so manual and scheduled
execution have identical fetching and persistence behavior. Repeated scans are
safe: the unique `jobs.url` key turns a repeated posting into an update.

## Inspect stored jobs

Open PostgreSQL:

```bash
docker exec -it career-engine-db psql -U postgres -d career_engine
```

Check the total inventory:

```sql
SELECT COUNT(*) AS total_jobs FROM jobs;
```

Check counts by company:

```sql
SELECT c.name, COUNT(j.id) AS jobs
FROM companies AS c
LEFT JOIN jobs AS j ON j.company_id = c.id
WHERE c.careers_url IS NOT NULL
GROUP BY c.id, c.name
ORDER BY jobs DESC, c.name;
```

Inspect recently refreshed rows:

```sql
SELECT
    j.title,
    c.name AS company,
    j.location,
    j.salary_min,
    j.salary_max,
    j.posted_at,
    j.deadline,
    j.url
FROM jobs AS j
JOIN companies AS c ON c.id = j.company_id
ORDER BY j.updated_at DESC
LIMIT 20;
```

Exit `psql` with `\q`.

## Verify idempotency manually

Run the CLI twice without changing provider data, then compare:

```sql
SELECT COUNT(*) FROM jobs;
SELECT COUNT(DISTINCT url) FROM jobs;
```

The values must be equal because `jobs.url` is unique. The total count should
remain stable unless an ATS publishes or removes URLs between runs.

## Run ingestion and scheduler tests

The complete suite requires the configured local PostgreSQL database:

```bash
cd backend
source .venv/bin/activate
pytest \
  tests/test_celery_app.py \
  tests/test_ingestion_task.py \
  tests/test_search_ingestion_access.py \
  tests/test_provider_ingestion.py \
  tests/test_job_ingestion.py \
  tests/test_fetch_json.py \
  tests/test_fetch_service.py \
  tests/test_sources.py \
  tests/test_ats_config.py \
  tests/test_html_sanitizer.py
```

Celery configuration and task-adapter tests do not require a live Redis server.
The provider fixture tests replace external HTTP transport and do not contact
real ATS hosts.

## Production process checklist

Treat the scheduler as infrastructure separate from FastAPI:

1. Provision a private, durable Redis deployment. Supply authenticated or TLS
   URLs through `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`.
2. Run migrations and seed scannable companies before enabling Beat.
3. Run at least one worker dedicated to the `ingestion` queue. Start with the
   default prefork pool and concurrency one:

   ```bash
   celery \
     -A app.celery_app:celery_app \
     worker \
     --loglevel=INFO \
     --queues=ingestion \
     --concurrency=1
   ```

4. Run exactly one supervised Beat replica:

   ```bash
   celery -A app.celery_app:celery_app beat --loglevel=INFO
   ```

5. Configure the platform or process supervisor to restart both processes after
   failure and deploy task or environment changes to both.
6. Use graceful termination so an active worker can finish or return its
   late-acknowledged task to Redis.
7. Monitor Redis reachability, worker availability, Beat logs, task failures,
   scan duration, and the recency of `jobs.updated_at`.

When all processes run in containers, `localhost` points back to the individual
container. Use the Redis network hostname, for example
`redis://redis:6379/0`, rather than `redis://localhost:6379/0`.

## Troubleshooting

### Redis connection refused

```bash
docker ps --filter name=hire-journey-redis
docker exec hire-journey-redis redis-cli ping
```

Confirm the worker and Beat use the same `CELERY_BROKER_URL`. Inside a container,
replace `localhost` with the Redis service hostname.

### Worker reports an unregistered task

Restart the worker after deploying code, then verify:

```bash
celery -A app.celery_app:celery_app inspect registered
```

It must include `hire_journey.ingest_jobs`.

### Beat sends tasks but no scan starts

Confirm a worker is online and consuming `ingestion`, not only Celery's default
queue:

```bash
celery -A app.celery_app:celery_app inspect ping
celery -A app.celery_app:celery_app inspect active_queues
```

### Nothing happens when Beat starts

This is expected between scheduled slots. Beat runs at `07:00` and `15:00` UTC
and does not send an immediate startup task. Use the CLI fallback for an
immediate scan.

### The schedule fires at an unexpected local time

Celery is configured with `timezone="UTC"`. Convert `07:00` and `15:00` from UTC
to the deployment's local time; do not assume the host timezone controls Beat.

### Duplicate scheduled messages appear

Check that only one Beat replica is running. Multiple workers are safe, but only
one scheduler should publish the schedule. The PostgreSQL lock prevents two
scans from overlapping; an extra message that arrives later can still cause an
unnecessary additional scan.

### A scan is skipped because the lock is held

Another worker or the CLI is already scanning. This is expected protection, not
a Redis failure. Inspect active workers and wait for the existing scan to finish.

### PostgreSQL connection refused

Confirm the container is running and `DATABASE_URL` points to the exposed port:

```bash
docker ps --filter name=career-engine-db
```

### A scan reports zero jobs

Confirm scannable companies exist, then inspect worker logs for unsupported
URLs, HTTP failures, malformed responses, or persistence errors. A healthy
provider can also legitimately return an empty board.

### A company is not scanned

The scan ignores companies whose `careers_url` is null. Correct the provider and
slug in `companies.yaml`, then rerun `python scripts/seed_companies.py`.

### Provider errors make the scan slower

Retryable transport and server failures are attempted up to `ATS_MAX_ATTEMPTS`.
Retry backoff retains provider and global concurrency permits to prevent an
unbounded retry storm.

### Changing resource limits

Adjust `ATS_*` values in `backend/.env`, then restart the worker. See the
[architecture guide](../architecture/job-ingestion.md#configuration) for all
controls.
