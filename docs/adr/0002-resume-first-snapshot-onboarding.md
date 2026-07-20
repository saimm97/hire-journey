# ADR-0002: Adopt a resume-first, snapshot-driven onboarding workflow

- Status: Accepted
- Date: 2026-07-20
- Decision scope: user onboarding across the Next.js frontend and FastAPI backend
- Implementation: `feat/user-onboarding` (`8acccff` through `92ec3bc`)
- Related decision: [ADR-0001](0001-profile-centered-onboarding-schema.md)

## Context

Hire Journey needs enough trustworthy candidate data to drive job matching, but
asking a new user to manually enter their entire work history, education,
projects, and technology stack creates a long and repetitive first-run
experience. Resume extraction can reduce that effort, but model output is
inherently incomplete and inconsistent and therefore cannot be accepted as
authoritative without a correction step.

The workflow also spans several relational and JSON-backed parts of the profile
aggregate. The frontend needs a consistent view after resume extraction and
after each user edit, while the backend needs to prevent partial persistence,
cross-user project changes, stale completion state, and slow LLM calls while
database locks are held.

## Decision

1. Make onboarding resume-first. A source PDF or DOCX is required before the
   profile-details and preferences steps can complete.
2. Extract document text on the backend and use schema-constrained LLM output to
   prefill the profile. Try configured providers in the order Groq, Gemini, then
   OpenAI, with bounded retries.
3. Use separate trust boundaries for machine and human input:
   - accept lenient, optional extraction fields from the LLM;
   - deterministically normalize, bound, deduplicate, or discard unusable
     extracted values before persistence; and
   - strictly validate the user's corrected detail and preference payloads.
4. Run document parsing and LLM extraction before database mutation. Persist the
   resume and all resume-derived profile data in one transaction so the workflow
   never exposes a partially imported profile.
5. Return one aggregate `OnboardingSnapshot` from the onboarding read, resume
   upload, details save, and preferences save. The snapshot contains the profile,
   source-resume metadata, employment, projects, and computed completion state.
6. Split human correction into two route-level steps:
   - profile details, saved with `PUT /profile/details`; and
   - job preferences, saved with `PUT /profile/preferences`.
7. Treat the nested collections in the details step as full replacements. The
   server reconciles normalized relationships, verifies project ownership, uses
   copy-on-write for shared project renames, and deletes unreferenced profile
   memberships.
8. Compute onboarding completion from the current source of truth rather than
   storing a mutable flag. Completion requires a source resume, first name, last
   name, title, at least one desired role, at least one work mode, and seniority.
9. Centralize completed-user routing on `/dashboard`. Wizard pages redirect
   completed users there, while the post-onboarding `/profile` page reuses the
   same forms with completion guards disabled.
10. Replace the current source resume in place on UI re-upload. Resume-derived
    fields and collections are refreshed, while job preferences are preserved.

## Alternatives considered

### Start with a blank manual profile form

Rejected as the primary path. It avoids LLM cost and provider disclosure but
requires users to reproduce information already present in their resume. Manual
correction remains available immediately after extraction.

### Persist LLM output without a review step

Rejected. Even schema-constrained output can omit, duplicate, truncate, or
misclassify facts. The user remains the authority on their profile, and strict
edited schemas provide a safer boundary for downstream matching.

### Use one endpoint and payload per profile section

Rejected for this iteration. It would create more partial states, network
coordination, and error recovery paths. Two explicit `PUT` steps match the user
journey, while a single snapshot gives the browser a coherent aggregate after
each save.

### Patch individual items in nested collections

Deferred. Per-item mutation can reduce write volume and support concurrent
editing, but it requires a larger endpoint surface and more client bookkeeping.
Full replacement is easier to reason about for bounded onboarding collections.

### Persist an `onboarding_complete` column

Rejected. Every field mutation would need to update the flag correctly, and
older clients or direct database changes could leave it stale. Computing the
small rule when building a snapshot keeps completion consistent with the data.

### Process resume extraction asynchronously

Deferred. A background job would avoid a long-running HTTP request and enable
progress or retry controls, but it introduces queue infrastructure, job state,
polling or push notifications, and cleanup rules. The synchronous path is
acceptable for the current onboarding volume.

### Parse resumes with deterministic rules only

Rejected as the main extractor. Fixed heading and regular-expression pipelines
are brittle across resume layouts. Deterministic parsing remains responsible for
document text extraction and post-LLM normalization.

## Consequences

### Positive

- Users begin with an editable prefilled profile instead of a long blank form.
- Every onboarding mutation returns the same normalized server state.
- A failed extraction or persistence step cannot leave partial profile data.
- Lenient machine input improves extraction resilience without weakening the
  strict user-edit API contract.
- Completion cannot drift from its required fields.
- Ownership checks and copy-on-write prevent one profile from mutating another
  profile's shared project identity.
- The onboarding forms can be reused as the permanent profile editor.

### Tradeoffs

- Upload latency includes text extraction and one or more external LLM calls.
- Resume text is stored in the database and sent to a configured third-party
  model provider, which creates privacy, retention, and disclosure obligations.
- A model-provider outage blocks first-time onboarding because a resume is the
  required entry point.
- Image-only resumes fail until OCR support exists.
- Full-replacement collections can lose concurrent edits from another client.
- Re-upload intentionally clears resume-derived values absent from the new
  document, so users may need to review those fields again.
- The web client and backend currently duplicate the upload-size limit and must
  be changed together.

## Operational implications

- At least one supported LLM API key must be configured. No provider key returns
  `503`; exhausted extraction attempts return `502`.
- Uploads are restricted by extension and size, and empty or unreadable
  documents return `422`.
- Provider latency and failures should be monitored separately from validation
  failures.
- The raw and parsed resume fields require an explicit production retention and
  deletion policy.
- The API limits each user to two resume rows with a user-level lock; the current
  web flow normally replaces its one source resume.

## Follow-up decisions

The following remain open and should receive separate decisions if adopted:

- asynchronous extraction jobs, progress reporting, and retry ownership;
- OCR for image-only documents;
- resume retention, deletion, encryption, and provider-disclosure policy;
- optimistic concurrency or versioning for full-replacement detail saves;
- whether every password login should consult onboarding state; and
- whether upload constraints should be delivered to the client through runtime
  configuration instead of being duplicated.

