# User onboarding flow

- Status: current as of 2026-07-20
- Implementation branch: `feat/user-onboarding`
- Comparison base: `development` at `0325655`
- Related decision: [ADR-0002](../adr/0002-resume-first-snapshot-onboarding.md)

This document describes the user journey from account creation through a
completed Hire Journey profile. It also records the frontend routing rules,
backend API contract, resume-extraction pipeline, persistence semantics, and
recovery paths that support that journey.

## Flow at a glance

```mermaid
flowchart TD
    Start([Visitor]) --> Auth{"Authentication path"}
    Auth -->|Create local account| Register["POST /auth/register"]
    Register --> Login["POST /auth/login<br/>issue HttpOnly session cookie"]
    Auth -->|Continue with Google| Google["POST /auth/google<br/>create or resolve account"]
    Auth -->|Existing password login| Existing["POST /auth/login"]

    Login --> Lookup["GET /profile"]
    Google --> Lookup
    Existing --> Dashboard["/dashboard"]

    Lookup --> State{"Onboarding state"}
    State -->|No profile or source resume| ProfileStep["/onboarding/profile"]
    State -->|Resume present; core details missing| ProfileStep
    State -->|Core details ready; preferences missing| Preferences["/onboarding/preferences"]
    State -->|Complete| Dashboard

    ProfileStep --> Upload["Upload PDF or DOCX<br/>up to 5 MB"]
    Upload --> Parse["POST /profile/cv<br/>extract text and structured data"]
    Parse -->|Failure| UploadError["Show actionable error<br/>keep user on upload step"]
    UploadError --> Upload
    Parse --> Persist["Transactionally persist resume,<br/>profile, employment, projects, and skills"]
    Persist --> Review["Prefilled, editable profile form"]
    Review --> SaveDetails["PUT /profile/details"]
    SaveDetails --> Preferences

    Preferences --> SavePreferences["PUT /profile/preferences"]
    SavePreferences --> Complete{"Server-computed<br/>onboarding_complete?"}
    Complete -->|No| Incomplete["Stay on preferences;<br/>prompt to finish details"]
    Incomplete -->|Back| ProfileStep
    Complete -->|Yes| Dashboard

    Dashboard --> Editor["/profile"]
    Editor -->|Edit details| SaveDetails
    Editor -->|Edit preferences| SavePreferences
    Editor -->|Replace source resume| Parse
```

The local password sign-in screen currently sends existing users directly to
`/dashboard`. Local registration and Google authentication inspect the
onboarding snapshot before routing. A user without a source resume who opens
`/profile` is sent back to the resume step; a partially completed user with a
source resume can finish through the reused editor forms.

## Onboarding state model

The backend does not store a completion flag. Every onboarding response
computes `onboarding_complete` from the current profile, which prevents a stale
flag from disagreeing with the underlying data.

| State | Server-side evidence | Destination |
| --- | --- | --- |
| Not started | `GET /profile` returns `404`, or no source resume exists | `/onboarding/profile` |
| Resume uploaded, details incomplete | A source resume exists, but first name, last name, or title is blank | `/onboarding/profile` |
| Details ready, preferences incomplete | Source resume, first name, last name, and title exist; at least one preference requirement is missing | `/onboarding/preferences` |
| Complete | Source resume, first name, last name, title, at least one desired role, at least one work mode, and seniority all exist | `/dashboard` |

Desired locations and minimum salary are optional and do not affect completion.

## End-to-end user journey

### 1. Authenticate

- Local registration creates the user, immediately signs them in, hydrates the
  client session through `GET /auth/me`, and checks their onboarding snapshot.
- Google authentication verifies the Google credential in the backend, resolves
  an account by verified email or creates one, issues the same application
  session, and checks the snapshot.
- Authentication uses an `access_token` cookie with `HttpOnly`, `SameSite=Lax`,
  and the configured expiry. The frontend includes credentials on every API
  request.
- The Next.js proxy redirects unauthenticated visitors to `/login`. Protected
  API endpoints independently validate the token and resolve the current user.

`postAuthDestination()` treats a profile lookup failure as non-blocking and
falls back to `/dashboard`; a temporary profile API failure therefore does not
turn a successful login into a failed login.

### 2. Upload and parse a resume

The profile step initially shows a drag-and-drop uploader. The browser accepts
one `.pdf` or `.docx` file and rejects files over 5 MB before sending them. The
backend repeats both checks and does not trust the client-provided size.

`POST /api/v1/profile/cv` performs the following work:

1. Extract plain text with PyMuPDF for PDF or `python-docx` for DOCX, including
   text in DOCX tables.
2. Reject corrupt, password-protected, empty, or image-only documents.
3. Send the extracted text to configured LLM providers in the order Groq,
   Gemini, then OpenAI. Each provider is asked for schema-constrained output;
   invalid results are retried.
4. Accept lenient extraction fields so a partially understood resume can still
   reach the correction screen. Missing values remain empty rather than being
   invented.
5. Normalize values for persistence: trim and bound strings, normalize URLs and
   dates, lowercase and deduplicate technologies, discard unusable relationship
   rows, and collapse duplicate employment or project entries.
6. In one database transaction, create or replace the resume, upsert the
   profile, replace resume-derived technologies, employment, and projects, and
   set the profile's `source_resume_id`.
7. Return a fresh onboarding snapshot to prefill the UI.

The LLM call happens before database locks or writes. If parsing, extraction, or
persistence fails, no partial onboarding state is committed.

The resume row stores extracted text in `raw_content` and the original
structured extraction in `parsed_content`. The onboarding snapshot exposes only
resume metadata and its summary; it never returns the raw resume text.

### 3. Review and correct profile details

After extraction, the user can edit:

- name, phone number, location, professional title, and summary;
- GitHub, LinkedIn, and portfolio links;
- education and certifications;
- employment history;
- projects and each project's technologies; and
- the profile-level technology list.

`PUT /api/v1/profile/details` is a full replacement of the details step. Empty
UI rows are omitted, omitted collection entries are removed, and the entire save
is atomic. User-edited payloads are validated strictly: required row fields,
`YYYY-MM` dates, date ordering, URLs, collection limits, and string lengths must
all be valid.

Project IDs are ownership-checked. Renaming a project that another profile also
references uses copy-on-write, so another user's project identity is not
modified. Shared company rows are reused case-insensitively and are never
deleted when a profile changes its employment history.

### 4. Choose job preferences

The preferences step collects:

- one or more desired roles;
- zero or more desired locations;
- one or more work modes: remote, hybrid, or onsite;
- one seniority level; and
- an optional non-negative minimum salary.

`PUT /api/v1/profile/preferences` trims and deduplicates list values, validates
the allowed work modes and seniority values, saves the preferences, and returns
a fresh snapshot. The frontend moves to `/dashboard` only when that response
reports `onboarding_complete: true`; otherwise it asks the user to finish the
missing profile details.

### 5. Continue into the application

The dashboard is the completed destination and uses the shared application
shell. The shell exposes Dashboard and Profile navigation, shows the signed-in
account, and logs out through `POST /auth/logout` before returning to `/login`.

### 6. Edit or replace data later

`/profile` reuses the onboarding detail and preference forms with completion
redirects disabled. Saves stay on the page and show success or error feedback.

Selecting a new resume from the existing profile replaces the current source
resume in place by passing `replace_resume_id`. Resume-derived detail fields and
collections are replaced, including clearing values absent from the new resume;
job preferences are deliberately preserved. The service supports at most two
resume records per account, although the current onboarding UI replaces its
source record instead of consuming another slot.

## API contract

All routes below are under `/api/v1` and require an authenticated user except
registration, login, Google authentication, and public auth configuration.

| Method and path | Purpose | Success response | Important semantics |
| --- | --- | --- | --- |
| `POST /auth/register` | Create a local account | `UserRead` (`201`) | Does not issue a session by itself |
| `POST /auth/login` | Password login | Token plus session cookie | Accepts username or email in form field `username` |
| `POST /auth/google` | Google sign-up/sign-in | Token plus session cookie | Requires a verified Google email |
| `GET /auth/me` | Hydrate the client session | `UserRead` | Resolves the cookie to the current user |
| `POST /auth/logout` | End the session | Confirmation object | Clears the session cookie |
| `GET /profile` | Load all onboarding state | `OnboardingSnapshot` | Returns `404` until a profile exists |
| `POST /profile/cv` | Parse and persist a resume | `OnboardingSnapshot` (`201`) | Optional `replace_resume_id` must belong to the user |
| `PUT /profile/details` | Save corrected profile data | `OnboardingSnapshot` | Full replacement of profile-owned collections |
| `PUT /profile/preferences` | Save matching preferences | `OnboardingSnapshot` | Response contains freshly computed completion |
| `PATCH /profile` | Partial profile update | `ProfileRead` | Available to other clients; the current web editor uses the two `PUT` routes |

`OnboardingSnapshot` is the shared response shape for the read, upload, detail,
and preference steps. It contains the profile, source-resume metadata,
employment history, projects, and computed completion state. Returning the same
shape after every mutation lets the browser replace local state with the
server's normalized source of truth.

## Failure and recovery behavior

| Status | Typical cause | User recovery |
| --- | --- | --- |
| `401` | Missing, expired, or invalid session | Sign in again |
| `404` | Profile not started, or replacement resume not owned/found | Start with a resume upload; do not reuse foreign IDs |
| `409` | Account already has the configured maximum number of resumes | Replace or remove a resume |
| `413` | Upload exceeds the backend size limit | Upload a smaller document |
| `415` | Filename is not PDF or DOCX | Choose a supported format |
| `422` | Unreadable/no-text document, invalid edited data, or foreign project ID | Correct the file or highlighted profile data |
| `502` | Every configured LLM attempt failed | Retry; inspect provider health if persistent |
| `503` | No LLM provider key is configured | Configure at least one provider and restart the backend |

The frontend keeps the user on the current step and presents an error toast when
an onboarding request fails. A failed re-upload restores the existing editable
profile rather than discarding it.

## Configuration

Backend onboarding settings:

- `MAX_UPLOAD_MB` defaults to `5`.
- `MAX_RESUMES_PER_USER` defaults to `2`.
- At least one of `GROQ_API_KEY`, `GEMINI_API_KEY`, or `OPENAI_API_KEY` is
  required for resume extraction; their corresponding model variables are
  optional overrides.
- `CORS_ORIGINS` must include the frontend origin.
- `GOOGLE_CLIENT_ID` enables backend verification for Google authentication.

Frontend settings:

- `NEXT_PUBLIC_API_URL` is the backend origin, for example
  `http://localhost:8000`.
- `NEXT_PUBLIC_GOOGLE_CLIENT_ID` must match the backend's Google OAuth web
  client when Google authentication is enabled.

The browser currently enforces a fixed 5 MB upload limit. If the backend limit
changes, update the frontend limit at the same time so the two checks remain
consistent.

## Verification coverage

- Backend tests cover PDF/DOCX text extraction, provider fallback and retries,
  atomic resume persistence, normalization, deduplication, re-upload behavior,
  resume limits, API validation, project ownership, and computed completion.
- Frontend tests cover snapshot routing, profile hydration and payload mapping,
  local file validation, source-resume replacement, preference validation, and
  completion redirects.

Relevant suites live in `backend/tests/test_*onboarding*`,
`backend/tests/test_process_cv.py`, `backend/tests/test_document_parser.py`,
`backend/tests/test_llm_extraction.py`, and `frontend/src/**/*.test.ts(x)`.

## Known limitations and follow-ups

- Extraction is synchronous, so the upload request remains open during the LLM
  call and the UI can show only an indeterminate parsing state.
- Scanned/image-only PDFs are unsupported because there is no OCR stage.
- Full-replacement detail saves are simple and deterministic but can overwrite
  a concurrent edit from another browser tab.
- Resume text and structured extraction contain personal information. A
  retention/deletion policy and explicit user-facing provider disclosure should
  be settled before production use.
- Existing password login currently routes directly to the dashboard instead of
  consulting onboarding state; registration and Google authentication do
  consult it.
