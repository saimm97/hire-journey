# ADR-0001: Adopt a profile-centred onboarding schema

- Status: Accepted
- Date: 2026-07-18
- Decision scope: onboarding database refactor
- Implementation commit: `04cf4b3`

## Context

The original schema mixed UUID and entity-specific primary-key names, stored
several repeated structures directly on a profile, and included job-search
features that were not required for the immediate onboarding milestone. The
team also needed a consistent answer to where shared identity, profile-specific
details, flexible document data, and business rules should live.

The active development database contains disposable data, so preserving rows
during the key-type conversion was not a requirement for this iteration.

## Decision

1. Every entity table uses an auto-incrementing integer primary key named `id`.
   Bridge tables may use composite primary keys made from their foreign keys.
2. `profiles` is the aggregate root for onboarding information and job
   preferences. A user owns at most one profile.
3. Use a hybrid relational/JSON design:
   - normalize identities and relationships that need reuse, uniqueness,
     filtering, or referential integrity: companies, projects, technologies,
     employment histories, and bridge tables;
   - keep profile-owned, variably shaped display data in JSONB: social links,
     education, and certifications;
   - keep simple multi-value preferences in PostgreSQL arrays.
4. Keep shared project identity in `projects` and profile-specific project
   details in `profile_projects`.
5. Treat employment histories as profile-owned stints connected to a normalized
   company. Do not share an employment row between profiles merely because two
   people held the same title at the same company.
6. Normalize technologies once and reference them through profile and project
   membership bridges. Technology names are stored in lowercase.
7. Remove resume slots and the persisted active flag. Allow at most two uploaded
   resumes through a concurrency-safe service rule and treat the newest upload
   as current.
8. Make evaluations and tailored resumes profile-owned rather than user- or
   uploaded-resume-owned.
9. Remove application tracking, job notes, job scores, search sessions, and
   legacy source modelling from the current onboarding-focused schema.
10. Rebuild the development schema rather than attempting an in-place UUID to
    integer data conversion.

## Alternatives considered

### Store all onboarding data in one profile JSONB document

Rejected as the default. It would make shared company/technology identities,
uniqueness, foreign keys, filtering, relationship updates, and data cleanup
harder. JSONB remains appropriate where the data is profile-owned and does not
yet need independent querying.

### Create globally shared employment records with a profile bridge

Rejected for the current model. Two people working at the same company with the
same title still have different dates, descriptions, and employment facts. The
company is the reusable identity; the employment stint belongs to one profile.

### Persist resume slots and an active-resume flag

Rejected following the revised ERD. Slot coordination and single-active-row
constraints added state that the current workflow does not need. Recency gives
the application one deterministic current resume.

### Preserve development data during UUID conversion

Rejected for this iteration because the data is disposable. A production data
migration would require mapping old rows and foreign keys rather than using the
destructive rebuild in this branch.

## Consequences

### Positive

- IDs and foreign keys are consistent across the schema and API contracts.
- Shared identities and many-to-many relationships have database integrity.
- Profile-specific project data no longer pollutes global project identity.
- Technology normalization is protected at both application and database
  boundaries.
- The onboarding schema is smaller and easier to evolve without unrelated job
  workflow entities.

### Tradeoffs

- The rebuild migration discards existing development data.
- JSONB fields cannot provide the same per-property foreign keys or column-level
  constraints as normalized tables.
- Direct SQL inserts can bypass the service-enforced two-resume limit.
- Determining the current resume by recency depends on reliable timestamps and
  intentionally does not preserve a manual active selection.
- Provider ingestion and semantic job deduplication need a later design and ADR.

## Follow-up decisions

The following are deliberately not settled by this ADR:

- provider/source modelling and job provenance;
- cross-provider job deduplication;
- strict inner schemas for education, certification, and social-link JSONB;
- database enforcement for evaluation score bounds and evaluation uniqueness;
  and
- whether the resume limit should eventually be enforced by a PostgreSQL
  trigger in addition to the service.
