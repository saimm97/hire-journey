# Run job ingestion locally

Use this runbook to populate or refresh the local `jobs` table from every
supported ATS feed stored in `companies.careers_url`.

The current process is manual. It does not require the frontend or a running
FastAPI server, but it does require PostgreSQL and outbound internet access.

## One-time setup

From the repository root, start the existing PostgreSQL container:

```bash
docker start career-engine-db
```

If the container has not been created yet, follow the database setup in the
root `README.md` first.

Prepare the backend environment:

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
```

Do not overwrite an existing `.env`. At minimum it must contain working
`DATABASE_URL` and `SECRET_KEY` values. ATS ingestion itself does not use an AI
provider key.

## Seed or refresh company feed URLs

For the current catalog, edit `backend/config/companies.yaml` with the company
name, supported provider, and provider board slug:

```yaml
companies:
  - name: Example Company
    source: greenhouse
    slug: example-company
```

Then run, from `backend/` with the virtual environment active:

```bash
python scripts/seed_companies.py
```

The seed command validates all slugs and constructs the authoritative feed URLs
before it writes any rows. It is idempotent: rerunning it updates matching
companies instead of creating duplicates.

Supported providers are `greenhouse`, `ashby`, and `lever`. Entries for an
unsupported provider can remain in the seed catalog, but they receive a null
`careers_url` and are not scanned until an Adapter is registered.

`companies.yaml` is not used by the runtime scan. If company rows and valid feed
URLs already exist in PostgreSQL, skip this step.

The legacy `title_filter` and `location_filter` blocks in the YAML file are not
read by ingestion. The global catalog stores all valid public postings;
user-specific filtering happens later on the read path.

## Run one complete ingestion pass

From `backend/`:

```bash
source .venv/bin/activate
python scripts/ingest_jobs.py
```

The command scans every company with a non-null `careers_url`. There is not yet
a supported command-line option for one company or one provider.

`POST /api/v1/search/run` currently reaches the same locked scan, but it waits
for the complete run and is exposed to every authenticated user. Use the script
for operator-driven scans until that endpoint is restricted or removed as part
of scheduled ingestion.

A successful command prints an operator report similar to:

```text
Run: 00000000-0000-4000-8000-000000000001
Status: completed
Duration: 12s
Companies: 6 attempted, 6 succeeded, 0 failed, 1 empty
Jobs: 36 fetched, 36 upserted

Provider summary:
  greenhouse: health=healthy, feeds=3, jobs=24, feed_failures=0, persistence_failures=0
  ashby: health=warning, feeds=2, jobs=8, feed_failures=0, persistence_failures=0
  lever: health=healthy, feeds=1, jobs=4, feed_failures=0, persistence_failures=0
```

The upserted count is not the number of newly inserted jobs: existing URL
matches are included when they are refreshed.

For the complete machine-readable report, including every warning and error:

```bash
python scripts/ingest_jobs.py --json
```

JSON is the standard internal operational contract. Its complete field
reference, compatibility policy, status rules, and fabricated example are in
the [Ingestion Run Report contract](../contracts/ingestion-run-report.md).
Human output is for operator readability only.

`completed` and `skipped` exit with status `0`. `completed_with_errors` and
fatal `failed` runs print their reports and exit with status `1`, allowing shell
automation to detect an unhealthy run.

It is safe to run the command again. A repeated provider URL updates the
existing job row through the unique `jobs.url` constraint. It does not insert a
second row unless the provider returns a materially different URL; broader URL
normalization is still outstanding.

If another process already owns the database advisory lock, the command returns
a report with `Status: skipped` and exits without contacting providers.

Reports and run IDs are not stored in PostgreSQL. They remain available only in
the command output and whatever retention is configured for backend logs.

Company issues include a sanitized feed URL in JSON, human output, and failure
logs. It retains the provider hostname and board path for diagnosis while
removing credentials, query parameters, and fragments.

## Inspect the result

Open PostgreSQL in the Docker container:

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

If the FastAPI server is running and you have an authenticated browser session,
the same catalog is available through `GET /api/v1/jobs`.

## Verify idempotency manually

Run the ingestion command twice without changing provider data, then compare:

```sql
SELECT COUNT(*) FROM jobs;
SELECT COUNT(DISTINCT url) FROM jobs;
```

The two values must be equal because `jobs.url` is unique. The total count
should remain stable unless an ATS publishes a new URL between runs.

## Run the ingestion tests

The tests require the configured local PostgreSQL database:

```bash
cd backend
source .venv/bin/activate
pytest \
  tests/test_provider_ingestion.py \
  tests/test_job_ingestion.py \
  tests/test_ingestion_cli.py \
  tests/test_ingestion_report.py \
  tests/test_search_run_reporting.py \
  tests/test_fetch_json.py \
  tests/test_fetch_service.py \
  tests/test_sources.py \
  tests/test_ats_config.py \
  tests/test_html_sanitizer.py
```

The provider fixture tests do not contact real ATS hosts. They replace only the
external HTTP transport and still exercise the real Adapters and database
persistence.

## Troubleshooting

### PostgreSQL connection refused

Confirm the container is running and that `.env` points to the exposed port:

```bash
docker ps --filter name=career-engine-db
```

The default local URL is:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/career_engine
```

### The command reports zero jobs

Confirm that scannable companies exist:

```sql
SELECT id, name, careers_url
FROM companies
WHERE careers_url IS NOT NULL
ORDER BY name;
```

Then check the backend output for unsupported URLs, HTTP failures, malformed
responses, or persistence errors. A healthy provider can also legitimately
return an empty board. The report classifies that outcome as a warning and
lists the affected company without failing the run.

### The command exits with status 1 after upserting jobs

`completed_with_errors` means usable company results were committed while one
or more company issues require attention. It deliberately exits with status
`1`; it does not mean the successful results were rolled back. Inspect the
grouped issue codes and sanitized feed URLs before deciding whether a later run
may recover automatically or the company configuration needs correction.

`retry_eligible: true` means the failure category qualified for automatic retry
during this run. The configured attempts have already completed; the flag does
not instruct an operator to rerun immediately.

### A company is not scanned

The scan ignores rows whose `careers_url` is null. Rerun the seed command for a
supported provider, or inspect whether the provider and slug in
`companies.yaml` are correct.

### The command appears slower during provider errors

Retry-eligible transport and server failures are attempted up to
`ATS_MAX_ATTEMPTS`. Retry backoff intentionally retains the provider and global
concurrency permits so one degraded ATS cannot create an unbounded retry storm.

### Changing resource limits

Adjust the `ATS_*` values in `backend/.env`, then start a new process. See the
[architecture guide](../architecture/job-ingestion.md#configuration) for every
setting and its meaning.
