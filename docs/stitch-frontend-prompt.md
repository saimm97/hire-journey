# Hire Journey — Stitch Frontend Design Prompt

A ready-to-paste prompt set for **Google Stitch**. It designs the full North-Star product,
annotated with backend readiness so you know what's wireable today vs. design-ahead-of-backend.

---

## How to use this in Stitch

1. **Establish the design language first.** Paste **Part A — Design System** as your first
   Stitch message in a new project. This sets colors, type, shape, and components for everything after.
2. **Generate one screen at a time.** Paste each **Screen block** from Part C as its own prompt.
   If Stitch's context drifts between screens, prepend the **Style Capsule** (Part B) to keep the look consistent.
3. **Iterate per screen.** After a screen generates, refine with short follow-ups
   ("make the score gauge larger", "tighten the filter sidebar to 260px").
4. Target surface: **responsive web app, desktop-first** (1280px canvas), degrading cleanly to mobile.

### Backend-readiness legend (shown per screen)
- ✅ **Wired** — a real endpoint backs this today.
- ⚠️ **Partial** — some data/endpoint exists; gaps are called out.
- 🔨 **Design-ahead** — no backend yet; the design leads implementation.

---

# Part A — Design System


**Product:** Hire Journey — an AI job-search copilot that carries a candidate from resume →
matched jobs → tailored applications → offer. The feeling is **momentum and encouragement**:
job hunting is stressful, and this interface should make progress *felt*, never clinical.

**Overall aesthetic:** warm, vibrant, and modern. Light-first. Rounded, generous, tactile —
but disciplined, not toy-like. One bold signature element (the Journey Spine); everything else quiet.

## Color (light theme)
- Canvas / page background: `#FBF8F4` (warm paper — a *subtle* base, never the star; do NOT pair with a serif)
- Raised surface / sidebar: `#F3EEE7`
- Card: `#FFFFFF`
- Ink / primary text: `#231F1C`
- Muted text / captions: `#7A736B`
- Hairline / border: `#E7E1D8`
- **Brand violet** (structure, nav-active, links, headings accents): `#6D3FE0`
- **Energy coral** (reserved ONLY for momentum CTAs — Run pipeline, Tailor my CV, Generate): `#FF6A3D`
- **Success emerald** (positive states, high scores, "Offered"): `#0FB582`
- Warning amber: `#F5A524` · Danger / rejected: `#F4513B`

## Two gradients — each means something
- **Match-score scale** (fit quality 0→100): `#F4513B` → `#F5A524` → `#0FB582`. Used on every score gauge/badge, everywhere, identically.
- **Journey gradient** (progress through the pipeline): `#FF6A3D` → `#F0468A` → `#6D3FE0`. Used on the Journey Spine, milestone dots, and the hero only. Use it sparingly.

## Dark theme (document as a variant)
Canvas `#161418`, surface `#201D25`, card `#282430`, ink `#F5F1EC`, muted `#A39C93`,
border `#332F3A`. Brand violet lightens to `#9E86FF`; coral and emerald stay. Both gradients keep their hues on the darker base.

## Typography
- **Display / headings:** Bricolage Grotesque — humanist, slightly irregular; carries the "encouraging, human" personality. Use with restraint at large sizes and section titles.
- **Body / UI:** Geist Sans (already in the codebase) — neutral, clean; lets the display face lead.
- **Data / numbers:** Geist Mono — for match scores, salaries, counts, dates. Numbers should read as *data*, tabular-aligned.
- Type scale: Display 40/32/24, Title 20/18, Body 16/14, Caption 12. Headings semibold, body regular, data medium. Sentence case everywhere (no ALL-CAPS shouting).

## Shape, spacing, elevation
- 8px spacing grid. Generous whitespace.
- Corner radius: cards/inputs `12px`, large panels `16px`, buttons `pill (999px)` for primary CTAs, `10px` for secondary.
- Shadows: soft, low-opacity, **warm-tinted** (e.g. `0 4px 20px rgba(60,40,20,0.06)`) — never hard gray drop-shadows.
- Icons: rounded line icons, consistent ~1.75px stroke (Lucide style).

## Components (define once, reuse)
- **Buttons:** Primary = coral pill, white text. Secondary = white with violet border + violet text. Ghost = text-only. Destructive = red outline.
- **Score gauge:** circular ring filled along the match-score gradient by percentage, big Geist-Mono number in center (e.g. `87`), tiny "match" label. Also a compact pill variant for lists.
- **Status pill** (application stages, color = meaning + always paired with its label): `saved` slate · `applied` coral · `interviewing` amber · `offered` emerald · `rejected` muted red.
- **Chips/tags:** rounded, for skills, roles, tech stack. Removable variant (× on hover) for editable fields.
- **Inputs:** 12px radius, soft inner surface, clear focus ring in brand violet.
- **Empty states:** an encouraging one-line invitation + a primary action (never a dead end).
- **Toasts:** bottom-right, action-consistent wording (a "Publish" button yields a "Published" toast).

## App shell (used on all post-onboarding screens)
- **Left sidebar** (`260px`, collapsible to icons): Dashboard, Search, Matches, Applications, Documents, Profile. Active item marked in brand violet. Sidebar sits on the `#F3EEE7` surface.
- **Top bar:** left = current screen title; right = active-resume switcher (`my_cv.pdf ▾`), notifications, avatar menu.
- **Content area:** max-width ~1120px, comfortable padding.

## Signature — the Journey Spine
A slim progress throughline with labeled milestone dots:
**Profile → Preferences → Search → Matches → Tailor → Apply → Track.**
Completed dots fill with the journey gradient; the current dot pulses gently. It appears:
(a) as the header of the onboarding wizard, (b) as the backbone of the Dashboard, and
(c) collapsed into a per-application status timeline on the tracker. This is the ONE memorable element — keep everything around it calm.

## Motion (restraint)
Score count-up on reveal · milestone dot fill on advance · a single soft celebratory pulse
when a job moves to "Offered." Respect `prefers-reduced-motion`. No confetti, no parallax, no scattered hover effects.

## Accessibility floor
WCAG AA contrast · visible keyboard focus · 44px min touch targets · never rely on color alone
(score color + number; status color + label) · all imagery has alt text.

---

# Part B — Style Capsule (prepend to any screen if Stitch drifts)

> Warm paper `#FBF8F4` canvas, white cards, warm ink `#231F1C`. Brand violet `#6D3FE0`,
> coral `#FF6A3D` for momentum CTAs only, emerald `#0FB582` for success. Match scores use a
> red→amber→green gradient ring. Bricolage Grotesque headings, Geist Sans body, Geist Mono for
> numbers. Rounded-xl cards, soft warm shadows, pill primary buttons. Light, encouraging, disciplined.

---

# Part C — Screen Prompts

---

## ════ SCREEN 0 — Sign in / Create account ════
**Backend:** ✅ Wired — `POST /auth/register`, `POST /auth/login` (form: username-or-email + password), `POST /auth/google` (Google ID token), `GET /auth/config` decides whether the Google button shows.

**PROMPT:**
Design a split-screen auth page for Hire Journey, web, light theme.
Left panel (55%): the brand moment — a large Bricolage Grotesque headline "Your job search, with momentum." and beneath it a subtle rendering of the Journey Spine (Profile → Preferences → Search → Matches → Tailor → Apply → Track) with the first dots filled in the coral→violet journey gradient, over the warm paper background. One encouraging sub-line: "From resume to offer, guided the whole way."
Right panel (45%, white card): a tabbed form — "Sign in" / "Create account". Fields for create: username, email, password (with strength hint). Sign in: "Email or username", password. Primary coral pill button ("Create account" / "Sign in"). A divider "or", then a secondary "Continue with Google" button with the Google mark (this button is conditionally shown). Small print: terms + a link to switch tabs.
States: inline field validation, a friendly error banner ("That email is already registered — sign in instead?"), loading state on the button.

---

## ════ SCREEN 1 — Onboarding · Profile from resume ════
**Backend:** ✅ `POST /profile/cv` (multipart PDF → parses identity, skills, projects, creates active resume). ⚠️ **Editing fields has no persistence endpoint yet** — design the edit UI, but mark saved edits as local/pending.

**PROMPT:**
Design the first step of a 3-step onboarding wizard for Hire Journey, web, light theme. Across the top, show the Journey Spine with "Profile" as the active milestone (pulsing), the rest upcoming.
Main area, two states in one screen:
(1) Empty: a large friendly dropzone card — "Drop your resume to get started" (PDF, up to 5MB), with a coral pill "Upload resume" and a line "We'll read it and fill in the details — you can fix anything."
(2) After upload: a parsing shimmer briefly, then an auto-filled, editable form in a clean card, grouped:
  • Identity: first name, last name, email, phone, GitHub URL, portfolio URL.
  • Skills / tech stack: removable chips (from the resume), plus an "add skill" input.
  • A read-only "Resume summary" panel (parsed).
  • A "Projects we found" list: each project as a small card (name, one-line summary, tech chips, GitHub / live links) with a source tag ("from CV").
Every field shows a subtle "auto-filled" marker and is editable inline. A small note near Save: "Editing here is saved locally for now." Footer: secondary "Back", coral pill "Save & continue".
States: upload error toasts — 413 "That file's over 5MB", 415 "That needs to be a PDF", 422 "We couldn't read any text from that PDF — try another export."

---

## ════ SCREEN 2 — Onboarding · Additional documents ════
**Backend:** ✅ `POST /profile/linkedin` (stores full parse into `candidate.linkedin_data`), `POST /profile/projects` (replaces `projects_pdf`-sourced projects).

**PROMPT:**
Design step 2 of the Hire Journey onboarding wizard, web, light theme, Journey Spine with "Profile" done and this still under the Profile milestone. Heading: "Add more so we match you better (optional)."
Two upload cards side by side:
  • "LinkedIn profile (PDF export)" — dropzone, a one-line "How to export your LinkedIn as PDF" helper link. On success show a compact summary chip row (headline, location, top skills extracted).
  • "Projects (PDF)" — dropzone. On success, list the parsed projects as cards, each tagged "from Projects PDF", editable, with a subtle merge note if a project overlaps one already from the CV.
Below: a combined "Your projects" gallery mixing CV-sourced and PDF-sourced items, each with its source tag. Footer: "Skip for now" ghost button + coral pill "Continue".

---

## ════ SCREEN 3 — Onboarding · Job preferences ════
**Backend:** ⚠️ Only `desired_role[]` and `minimum_salary` are real columns; there's no write endpoint yet, and **no fields for locations / work-mode / salary-range**. Design the full targeting step; mark the non-backed inputs as 🔨.

**PROMPT:**
Design step 3 of the Hire Journey onboarding wizard — "job targeting" — web, light theme, Journey Spine with "Preferences" active. Warm, encouraging tone: "Tell us what you're aiming for."
A single clean card, grouped fields:
  • Target roles — chip multi-select with type-ahead (e.g. "Machine Learning Engineer", "Backend Engineer", "AI Engineer"). (backed: desired_role)
  • Locations — chip multi-select of cities/regions + a "Open to relocating" toggle. (design-ahead)
  • Work mode — a segmented control: Remote / Hybrid / Onsite (multi-choice). (design-ahead)
  • Salary — a min→max range slider with currency select, plus a "Minimum acceptable" field. (only "minimum" is backed)
  • Seniority — segmented: Junior / Mid / Senior / Staff+.  (design-ahead)
  • "Anything else" — a free-text area for dealbreakers, industries, visa/work-authorization, availability date. (design-ahead)
Subtle "coming soon / saves later" tag on the design-ahead groups so it reads honest. Footer: "Back" + coral pill "Finish setup → Start searching". Completing this fills the "Preferences" milestone on the spine with the journey gradient.

---

## ════ SCREEN 4 — Job search & run pipeline ════
**Backend:** ✅ `POST /search/run` (body: `search_terms[]` + `resume_id` → 202, returns `session_id` + `total_jobs_scored`). The **only real inputs are search terms + resume**; company/title/location filtering is server-side config. 🔨 Advanced filters are design-ahead.

**PROMPT:**
Design the "Run a search" screen for Hire Journey inside the app shell (sidebar + top bar), light theme, "Search" active in the sidebar.
Centerpiece card titled "Find your matches":
  • Search terms — a prominent chip input with type-ahead ("ml", "backend", "ai", "platform"), helper: "Keywords we score jobs against." (real, required)
  • Active resume — a select showing the resume to score against ("my_cv.pdf") with a small "manage documents" link. (real, required)
  • A collapsible "Advanced filters" group, clearly badged "Design preview — not yet applied": work mode (Remote/Hybrid/Onsite), locations, salary range, and source boards (Greenhouse / Lever / Ashby toggles). Keep it visually present but visibly secondary.
  • A big coral pill CTA: "Run pipeline →".
On run: the button shows an async working state and a friendly progress card appears — "Scanning company boards…" → "Scoring against your resume…" — since this is a 202/async job. When done: a success banner "Scored 214 jobs" with a coral "View matches" button. Show a compact "recent searches" list below (terms + date + job count) so runs are re-openable.

---

## ════ SCREEN 5 — Matches (results list) ════
**Backend:** ✅ `GET /search/{session_id}/results` (`min_score`, `limit`, `offset`) → each result has job_id, title, company_name, location, url, score. ⚠️ **No description snippet or posted date in this payload** (description is on job detail; `posted_at` is null). 🔨 remote/hybrid & posted-within filters have no backing data.

**PROMPT:**
Design the "Matches" results screen for Hire Journey in the app shell, light theme, "Matches" active.
Header: "214 matches for ml, backend, ai" with a sort control (Best match / Newest) and a result count.
Left filter sidebar (260px):
  • Minimum match score — a slider over the red→amber→green score gradient. (real)
  • Work mode — Remote / Hybrid / Onsite checkboxes, badged "preview". (design-ahead)
  • Posted within — 24h / 7d / 30d radio, badged "preview". (design-ahead)
  • Source — Greenhouse / Lever / Ashby. (partial)
Main: a responsive list/grid of **job cards**. Each card:
  • Circular match-score gauge (gradient ring + Geist-Mono number, e.g. 87).
  • Job title (Bricolage, prominent) + company name + location.
  • A one-line description snippet — render it, but note it may be empty until the job is opened (placeholder: "Open to see the full description").
  • A posted-date line shown as "—" when unknown (data often absent).
  • Quick actions: "Save" (bookmark), "Open".
High scores (80+) get a subtle emerald edge; keep it tasteful. Include an empty state ("No matches above this score — try lowering the minimum") and a loading skeleton row.

---

## ════ SCREEN 6 — Job detail + AI analysis ════
**Backend:** ✅ `GET /jobs/{job_id}` (full description; salary usually null) and `POST /evaluations` (body: job_id + resume_id → match_score, strengths[], weaknesses[], recommendations[]). This is the best-supported flow. The "Tailor my CV" CTA leads to a 🔨 screen.

**PROMPT:**
Design the job detail screen for Hire Journey in the app shell, light theme. Two-column layout.
Header band: job title (large Bricolage), company + location, source badge, salary shown only if present, an outbound "View original posting ↗" link, and a coral "Save" action.
Left/main column: the full job description, cleanly typeset (headings, bullet lists), comfortable reading measure.
Right column (sticky, ~360px): the **AI analysis panel**.
  • Initial state: a card "See how well you match" with a coral pill "Run AI analysis" (uses your active resume).
  • Working state: a brief analyzing animation.
  • Result state: a large match-score gauge (gradient), then three labeled, icon-led sections — "Strengths" (emerald checks), "Gaps to address" (amber), "How to improve your fit" (violet, actionable recommendations). Each is a short bullet list.
  • Under the analysis, a prominent next-step card: "Ready to apply? Tailor your CV to this role" with a coral pill "Tailor my CV →".
Also include a secondary row: set application status (a status-pill selector: saved / applied / interviewing / offered / rejected) and an "Add note" field — both badged "coming soon".
Empty/err: if no LLM provider is configured the analysis card shows "AI analysis is temporarily unavailable" (maps to a 503), not a crash.

---

## ════ SCREEN 7 — Tailored CV ════
**Backend:** 🔨 Design-ahead — no endpoint, service, or LLM code exists; the `tailored_resumes` table is empty scaffolding. Design the full run → suggest → approve/edit → apply flow as the target.

**PROMPT:**
Design the "Tailor my CV" screen for Hire Journey, web, light theme, shown in context of a specific job (small job chip in the header: title + company + match score). Journey Spine shows "Tailor" active.
Flow in one screen:
  • Intro state: a card "Tailor your CV for Senior ML Engineer at Ramp" + a coral pill "Generate suggestions". A note that it uses your active resume + this job's requirements.
  • Working state: analyzing/rewriting animation.
  • Review state — the core: a **side-by-side diff** per CV section (Summary, Experience bullets, Skills). Left = your current text, right = the AI suggestion, changed spans highlighted. Each suggestion has: Approve (emerald check), Edit inline (pencil → editable text), Reject (dismiss). A running "X of Y suggestions reviewed" progress bar in the journey gradient.
  • A sticky footer: "Approve all", and a coral pill "Apply changes → " (disabled until reviewed), plus "See tailored CV" preview link.
  • On apply: a success moment ("Your tailored CV is ready") with buttons "View CV" and "Write cover letter →".
Keep the diff calm and legible — the highlight color for changes is a soft violet tint, approvals turn emerald.

---

## ════ SCREEN 8 — Cover letter & outreach email ════
**Backend:** 🔨 Design-ahead — nothing in the backend. Mirror the tailored-CV run → suggest → approve/edit → apply pattern.

**PROMPT:**
Design a "Cover letter & email" screen for Hire Journey, web, light theme, tied to a job (job chip in header). Two tabs: "Cover letter" and "Outreach email".
Each tab, same pattern:
  • A coral pill "Generate" (uses tailored CV + job + your profile).
  • Result: an editable rich-text draft in a clean document card on the left; on the right, a panel of AI "suggestions & tone controls" — tone segmented control (Warm / Direct / Formal), length, and a list of specific improvement suggestions the user can Approve / Edit / Reject.
  • For the email tab, also show To / Subject fields and a short "why this opener works" note.
  • Footer: "Regenerate", "Copy", and a coral pill "Save to application".
Consistent voice with the tailored-CV screen — same buttons, same approve/edit/reject affordances, same journey-gradient progress. A milestone celebration is fine but subtle.

---

## ════ SCREEN 9 — CV viewer & download ════
**Backend:** 🔨 Design-ahead — no PDF generation or resume-serving endpoint exists. Design the viewer + versions + download as the target.

**PROMPT:**
Design a "My CV" viewer screen for Hire Journey, web, light theme, app shell, "Documents" active.
Layout: a version rail on the left (a list of resume versions — "Base CV (active)", "Tailored · Senior ML Engineer @ Ramp", "Tailored · Backend @ Linear", each with a date and a small status), and a large centered document preview (paper-styled A4 rendering of the CV) in the middle.
Top-right actions: "Download PDF" (coral pill), "Set as active", "Duplicate", "Delete". A zoom control and page indicator under the preview.
Empty state: "No CV yet — upload your resume to get started" linking back to Documents. Keep the preview crisp and print-accurate.

---

## ════ SCREEN 10 — Dashboard ════
**Backend:** 🔨 Design-ahead — no applications / notes / resume-list / analytics endpoints exist to feed this. Design the full progress hub; treat the charts as the data model to build toward.

**PROMPT:**
Design the Hire Journey dashboard, web, light theme, app shell, "Dashboard" active. This is the candidate's progress hub — encouraging and momentum-focused.
Top: a welcome line ("Welcome back, Nihal — you're making progress") and the **Journey Spine rendered large and horizontal** as the section backbone, showing how far along the overall journey the user is, dots filled in the journey gradient.
Stat tile row (4 tiles, Geist-Mono numbers, one accent each, label always paired): Jobs saved · Applications sent · Interviews · Offers.
Charts area (apply clean data-viz conventions — right chart per data type, reuse the app's semantic colors, legends + accessible labels, never color-only):
  • "Applications over time" — an area/line chart of applications per week (momentum).
  • "Pipeline breakdown" — a horizontal stacked bar or funnel using the status-pill colors (saved / applied / interviewing / offered / rejected).
  • "Match-score distribution" — a histogram of your matches' scores, bars tinted along the red→amber→green score gradient.
  • "Response rate" — a compact stat + small trend sparkline.
Below: two panels — "Saved jobs" (compact cards with score + quick apply) and "Saved resumes" (version chips). Every chart has a friendly empty state ("Apply to your first role to start seeing patterns").
Keep it calm around the charts; let the Journey Spine be the hero.

---

## ════ SCREEN 11 — Application tracker (kanban) ════
**Backend:** ⚠️ The `ApplicationStatus` enum exists (`saved`, `applied`, `interviewing`, `offered`, `rejected`) but there's **no API** to read/write applications yet. Use these exact five stages.

**PROMPT:**
Design an application tracker for Hire Journey as a kanban board, web, light theme, app shell, "Applications" active.
Five columns using the exact status stages and their pill colors: **Saved** (slate) · **Applied** (coral) · **Interviewing** (amber) · **Offered** (emerald) · **Rejected** (muted red). Each column header shows a count.
Application cards (draggable between columns): company + role, a small match-score chip, the date of the last status change, tiny document indicators (CV / cover letter attached), and a note preview line. Moving a card to "Offered" triggers a single soft celebratory pulse.
Include: a board/list view toggle, a filter bar (by role, by min score), a per-card status timeline on hover (the Journey Spine collapsed to this application's history), and an empty column state ("Nothing here yet — save a job to start tracking"). Add-application affordance at the top of "Saved".

---

# Appendix — Real schema vocabulary (so mockups stay accurate)

- **Application stages (only real enum):** `saved` · `applied` · `interviewing` · `offered` · `rejected`.
- **Project source tag:** `cv` or `projects_pdf`.
- **Job source boards:** `greenhouse` · `lever` · `ashby`.
- **Match score:** integer 0–100 (keyword score in search results; LLM `match_score` in evaluations).
- **Profile fields that exist:** first_name, last_name, email, phone, github_url, portfolio_url, tech_stack[], desired_role[], minimum_salary, linkedin_data (JSON), source_resume_id.
- **Evaluation result:** match_score + strengths[], weaknesses[], recommendations[].
- **Known-empty fields (show as "—"):** job `salary_min/max`, job `posted_at` — never populated by the fetch adapters today.
- **No work-mode field exists** — remote/hybrid/onsite is design-ahead; job `location` is free text.
- **App title in code is "Career Engine"** though the product is "Hire Journey" — use Hire Journey.
