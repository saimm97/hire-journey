# Hire Journey documentation

This directory is the durable record of the system's architecture, decisions,
operational procedures, and delivery progress. Code and migrations remain the
source of truth; these documents explain why that code exists and how to work
with it safely.

## Documentation map

- [End-to-end user onboarding flow](architecture/user-onboarding-flow.md) —
  authentication, routing, resume extraction, profile correction, preferences,
  completion, API contracts, and failure recovery.
- [Current database schema](architecture/database-schema.md) — tables,
  relationships, constraints, ownership, and known limitations.
- [Visual language](architecture/visual-language.md) — typography, color,
  surfaces, action hierarchy, responsive navigation, and truthful onboarding
  progress.
- [Job ingestion architecture](architecture/job-ingestion.md) — provider
  Adapters, bounded fetching, sanitization, URL-idempotent persistence, and
  current limitations.
- [Ingestion Run Report contract](contracts/ingestion-run-report.md) — normative
  internal JSON schema, run status, provider ingestion health, issue taxonomy,
  safe diagnostic fields, and compatibility rules.
- [Run job ingestion locally](runbooks/job-ingestion.md) — database setup,
  company seeding, manual ingestion, verification, tests, and troubleshooting.
- [ADR-0001: Profile-centred onboarding schema](adr/0001-profile-centered-onboarding-schema.md)
  — the decisions and tradeoffs behind the July 2026 refactor.
- [ADR-0002: Resume-first, snapshot-driven onboarding](adr/0002-resume-first-snapshot-onboarding.md)
  — the cross-stack workflow, trust boundaries, transaction model, and
  completion decision.
- [ADR-0003: Bound and isolate ATS ingestion](adr/0003-bound-ats-ingestion.md)
  — the network, concurrency, registry, failure-isolation, and persistence
  decisions behind the current ingestion Module.
- [Database migration runbook](runbooks/database-migrations.md) — applying,
  verifying, and troubleshooting migrations.
- [Onboarding progress](progress/onboarding.md) — completed work, open work,
  and decisions that must not be rediscovered.

## Maintenance rules

Update the relevant documentation in the same pull request when a change:

- adds, removes, or renames a table, column, relationship, or constraint;
- changes a business rule or where that rule is enforced;
- introduces a migration with operational or data-loss consequences;
- changes an internal operational contract consumed by automation;
- accepts or reverses an architectural decision;
- changes the status of an onboarding milestone; or
- changes the shared visual tokens, interaction hierarchy, navigation, or
  progress semantics.

Create a new ADR for a decision that is expensive to reverse or affects more
than one component. Do not rewrite an accepted ADR to hide history; supersede
it with a new ADR instead.
