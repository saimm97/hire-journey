# Ingestion Run Report contract

The Ingestion Run Report is Hire Journey's stable internal operational contract
for the outcome of one job-ingestion run. It is consumed by backend operators,
CLI automation, and future scheduling or administrative tooling. It is not a
user-facing API and must never be exposed through job-seeker responses.

The JSON emitted by `python scripts/ingest_jobs.py --json` is the normative
serialized representation. Human CLI output is a presentation layer for
operator readability and may be reformatted without changing this contract.

## Compatibility and lifetime

The contract is currently unversioned because no independent deployed service
consumes it. Changes follow these rules:

- new fields may be added;
- existing field names, types, enum values, and meanings remain stable;
- a rename, removal, or semantic change is breaking and must update every
  internal consumer and contract test together; and
- a `schema_version` should be introduced before reports cross an independent
  deployment boundary.

Every documented field is present in serialized JSON. Optional values use
explicit `null` rather than disappearing from the object.

Reports are ephemeral. They are not stored in PostgreSQL and have no
application-level retention guarantee. A report remains available only through
the caller, command output, and the deployment's log-retention system.

## Top-level report

| Field | Type | Meaning |
| --- | --- | --- |
| `run_id` | UUID string | Correlates the report and logs for one run. |
| `status` | run-status enum | Overall outcome described below. |
| `started_at` | UTC RFC 3339 string | Time the run began. |
| `finished_at` | UTC RFC 3339 string | Time the run reached its final state. |
| `duration_ms` | integer | Non-negative elapsed milliseconds. |
| `companies_attempted` | integer | Selected companies whose feeds entered the run. |
| `companies_succeeded` | integer | Companies whose fetched snapshot was persisted successfully. |
| `companies_failed` | integer | Companies whose routing, fetch, parse, or persistence failed. |
| `empty_feeds` | integer | Successful company feeds containing zero jobs. |
| `jobs_fetched` | integer | Valid jobs returned by successful feeds before persistence. |
| `jobs_upserted` | integer | Jobs successfully upserted; includes inserted and refreshed rows. |
| `providers` | provider-summary array | Per-provider ingestion outcomes. |
| `warnings` | issue array | Complete successful-but-noteworthy outcomes. |
| `errors` | issue array | Complete company-level and run-level failures. |

`companies_succeeded + companies_failed` equals `companies_attempted` for a
normally completed run. A fatal run may stop before every selected company
reaches an outcome.

## Run status

| Status | CLI exit | Meaning |
| --- | ---: | --- |
| `completed` | `0` | The run reached normal completion without company errors. It may contain warnings. |
| `completed_with_errors` | `1` | Usable results were committed, but one or more company problems require operator attention. |
| `failed` | `1` | An unexpected run-level failure prevented normal completion. Earlier company commits may still exist. |
| `skipped` | `0` | Another process held the ingestion lock, so no feeds were attempted. |

Neither `completed_with_errors` nor `failed` implies a global rollback.
Company snapshots are committed independently, and the report counters describe
the work completed before the final state.

## Provider summary

Provider summaries describe Hire Journey's outcomes for configured company
feeds. They do not claim to measure an ATS platform's uptime or reliability.

| Field | Type | Meaning |
| --- | --- | --- |
| `provider` | string | Registered ATS provider name. |
| `ingestion_health` | health enum | Aggregate feed outcome described below. |
| `feeds_attempted` | integer | Selected company feeds attributed to this provider. |
| `feeds_succeeded` | integer | Feeds fetched and parsed successfully, including empty feeds. |
| `feeds_failed` | integer | Attributed feeds that failed routing, fetching, or parsing. |
| `empty_feeds` | integer | Successful feeds containing zero jobs. |
| `persistence_failures` | integer | Successful feed snapshots that could not be persisted. |
| `jobs_fetched` | integer | Valid jobs returned by this provider's successful feeds. |
| `jobs_upserted` | integer | This provider's jobs successfully upserted. |

Persistence failures affect the run status but not provider ingestion health,
because they do not indicate an external source failure. For each provider,
`feeds_succeeded + feeds_failed` equals `feeds_attempted`;
`persistence_failures` is a subset of successful feeds and is tracked
separately.

### Provider ingestion health

| Health | Meaning |
| --- | --- |
| `healthy` | Every attempted feed succeeded and none was empty. |
| `warning` | Every attempted feed succeeded, but at least one valid feed was empty. |
| `degraded` | At least one attempted feed succeeded and at least one failed. |
| `unavailable` | Every attempted feed failed. |

For example, `degraded` can result from a mixture of working boards and stale
HTTP 404 board URLs. It does not, by itself, prove that the ATS provider is
experiencing an outage. Issue codes carry the cause of each failure.

## Issue object

Warnings and errors use the same shape but remain in separate arrays.

| Field | Type | Meaning |
| --- | --- | --- |
| `stage` | stage enum | Boundary at which the issue occurred. |
| `code` | issue-code enum | Stable machine-readable classification. |
| `message` | string | Safe operator-facing explanation. Exact wording is not a machine contract. |
| `company_id` | integer or `null` | Affected company, or `null` for run-level issues. |
| `company_name` | string or `null` | Operator-readable company name. |
| `provider` | string or `null` | Registered ATS provider when its known feed host can be identified safely. |
| `feed_url` | string or `null` | Sanitized configured feed URL for company issues. |
| `exception_type` | string or `null` | Optional diagnostic class name; consumers must not branch on it. |
| `http_status` | integer or `null` | Final HTTP status when one exists. |
| `retry_eligible` | boolean | Whether the failure category qualified for automatic request retry. |

Automation may branch on `code`, `stage`, `http_status`, and
`retry_eligible`. It must not infer behavior from `message` or
`exception_type`.

### Sanitized feed URLs

`feed_url` retains the parsed scheme, hostname, port, and path so an operator can
inspect the provider and board slug. Embedded credentials, query parameters,
and fragments are always removed. The field is `null` when no company URL
applies or the configured value cannot be parsed safely. Raw configured URLs
must never enter reports or logs.

### Retry eligibility

`retry_eligible` describes policy eligibility, not remaining work. A report is
created only after the current run's automatic retry policy has completed.
Therefore, `true` does not mean more attempts remain or instruct an operator to
rerun ingestion immediately.

Timeouts, connection failures, HTTP 429, and selected 5xx responses are retry
eligible. HTTP 404, malformed responses, invalid feeds, and persistence failures
are not. A later scheduled run may still succeed for a transient issue.

## Fixed issue taxonomy

| Code | Array | Stage | Retry eligible | Meaning |
| --- | --- | --- | ---: | --- |
| `empty_feed` | warnings | `fetch` | false | A valid feed contained no jobs. |
| `invalid_feed_url` | errors | `routing` | false | The configured feed URL was invalid or unsupported. |
| `request_timeout` | errors | `fetch` | true | The provider request timed out after policy completion. |
| `connection_failed` | errors | `fetch` | true | A provider connection could not be established or maintained. |
| `rate_limited` | errors | `fetch` | true | HTTP 429 persisted through the retry policy. |
| `provider_http_error` | errors | `fetch` | varies | The final provider response had another error status; selected 5xx statuses are retry eligible. |
| `response_too_large` | errors | `fetch` | false | The response crossed the configured decoded-byte limit. |
| `invalid_json` | errors | `parse` | false | The provider response was not valid JSON. |
| `invalid_feed` | errors | `parse` | false | The JSON did not contain the provider's expected feed envelope. |
| `persistence_failed` | errors | `persistence` | false | A fetched company snapshot could not be committed. |
| `unexpected_fetch_error` | errors | `fetch` | false | Fetch processing raised an unclassified exception. |
| `unexpected_run_error` | errors | `run` | false | Run orchestration could not reach normal completion. |

## Security rules

Reports may include company identifiers, company names, sanitized feed URLs,
provider names, safe messages, exception class names, and HTTP statuses. They
must never include:

- raw provider response bodies;
- job descriptions or other posting content;
- database statements or bound parameters;
- raw exception messages;
- URL credentials, query parameters, or fragments; or
- authentication tokens or user data.

## Fabricated example

The following response is illustrative and contains no live company or run
data:

```json
{
  "run_id": "00000000-0000-4000-8000-000000000001",
  "status": "completed_with_errors",
  "started_at": "2030-01-01T08:00:00Z",
  "finished_at": "2030-01-01T08:00:12Z",
  "duration_ms": 12000,
  "companies_attempted": 3,
  "companies_succeeded": 2,
  "companies_failed": 1,
  "empty_feeds": 1,
  "jobs_fetched": 10,
  "jobs_upserted": 10,
  "providers": [
    {
      "provider": "greenhouse",
      "ingestion_health": "degraded",
      "feeds_attempted": 2,
      "feeds_succeeded": 1,
      "feeds_failed": 1,
      "empty_feeds": 0,
      "persistence_failures": 0,
      "jobs_fetched": 10,
      "jobs_upserted": 10
    },
    {
      "provider": "lever",
      "ingestion_health": "warning",
      "feeds_attempted": 1,
      "feeds_succeeded": 1,
      "feeds_failed": 0,
      "empty_feeds": 1,
      "persistence_failures": 0,
      "jobs_fetched": 0,
      "jobs_upserted": 0
    }
  ],
  "warnings": [
    {
      "stage": "fetch",
      "code": "empty_feed",
      "message": "The provider returned a valid feed containing no jobs.",
      "company_id": 202,
      "company_name": "Example Research",
      "provider": "lever",
      "feed_url": "https://api.lever.co/v0/postings/example-research",
      "exception_type": null,
      "http_status": null,
      "retry_eligible": false
    }
  ],
  "errors": [
    {
      "stage": "fetch",
      "code": "provider_http_error",
      "message": "The provider feed returned HTTP 404.",
      "company_id": 101,
      "company_name": "Example Systems",
      "provider": "greenhouse",
      "feed_url": "https://boards-api.greenhouse.io/v1/boards/example-systems/jobs",
      "exception_type": "HTTPStatusError",
      "http_status": 404,
      "retry_eligible": false
    }
  ]
}
```
