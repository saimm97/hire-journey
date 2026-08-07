# Domain Docs

HireJourney uses a single-context domain documentation layout.

## Before exploring, read these

- `CONTEXT.md` at the repository root, when it exists.
- Relevant architectural decisions under `docs/adr/`.

If one of these resources does not exist, proceed silently. Do not flag its absence or suggest creating it preemptively. The domain-modeling workflow creates or updates domain documentation when terminology or architectural decisions are actually resolved.

## File structure

```text
/
├── CONTEXT.md
├── docs/
│   └── adr/
│       ├── 0001-profile-centered-onboarding-schema.md
│       ├── 0002-resume-first-snapshot-onboarding.md
│       └── 0003-bound-ats-ingestion.md
└── backend/
└── frontend/
```

## Use the glossary vocabulary

When an output names a domain concept—in a Jira ticket, refactoring proposal, hypothesis, test, API, or schema—use the term defined in `CONTEXT.md`.

Do not replace established terms with synonyms that the glossary explicitly avoids.

If a required concept is absent, reconsider whether new terminology is necessary. When it represents a genuine domain gap, note it for the domain-modeling workflow.

## Flag ADR conflicts

If proposed work contradicts an accepted ADR, surface the conflict explicitly instead of silently overriding the decision.

Example:

> Contradicts ADR-0003 (Bound and isolate ATS ingestion), because this proposal moves user-specific filtering into the global ingestion path.
