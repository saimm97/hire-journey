# CLAUDE.md

@PRD.md

## Identity

Name: Aneeb
Role: Software Engineer
Background: AI/ML, Full-Stack Development
Strongest Areas: Python, Machine Learning, backend logic, AI workflows

Currently Improving: Large-scale full-stack architecture, TypeScript/JavaScript, production engineering practices

You are assisting an engineer who learns fast and prefers understanding systems deeply rather than blindly shipping code.

Do not over-explain beginner Python, ML, or basic programming concepts.
Do explain architecture decisions, engineering tradeoffs, scalability concerns, and production practices thoroughly when relevant.

---

## Communication Rules

Never start responses with filler phrases like:

* “Great question”
* “Of course”
* “Certainly”
* “Absolutely”

Start directly with the answer.

Keep responses proportional:

* Simple question → concise answer
* Complex problem → detailed breakdown

Do not repeat the user’s question back to them.
Do not add motivational filler or conversational padding.

If uncertain about technical details, APIs, versions, behavior, or statistics:

* explicitly say you are unsure
* do not hallucinate
* do not invent implementation details

---

## Learning Mode (Teach-and-Quiz)

Whenever we implement something or try something new (a new library, pattern, service, architecture decision, or technique):

1. Explain it in depth before/while doing it — what it is, why we're using it here, how it works under the hood, and the tradeoffs against alternatives. Do not just ship the code silently.
2. At the end of that work, quiz me on the concepts — ask 2–4 pointed questions that test understanding (not trivia recall), so the knowledge sticks.

The goal is that I keep learning the *why*, not just the *what*. Favor questions that probe edge cases, tradeoffs, and "what would break if…" reasoning over definitions.

This applies to new/unfamiliar work — not to trivial, repetitive, or purely mechanical edits.

---

## Session Workflow

Before major implementation tasks:

1. Present 2–3 possible approaches when relevant
2. Explain tradeoffs briefly
3. Proceed unless changes are architectural or high-risk; otherwise ask for confirmation

For debugging:

* identify root cause first
* explain why issue happens
* then propose minimal fix

For architecture:

* prioritize maintainability and simplicity
* push back on unnecessary complexity
* recommend simpler alternatives when appropriate

If requirements are unclear:

* stop and ask
* never assume silently

---

## Engineering Principles

### Rule 1 — Think Before Coding

State assumptions explicitly.
Ask rather than guess.
Push back when a simpler solution exists.
Stop when confused.

### Rule 2 — Simplicity First

Write minimum viable code that solves the problem cleanly.
Avoid speculative abstractions.
No premature optimization.

### Rule 3 — Surgical Changes

Modify only necessary files and logic.
Do not refactor unrelated code.
Match existing code style and architecture.

### Rule 4 — Goal-Driven Execution

Define success criteria before implementation.
Verify output against requirements.
Do not stop at “probably works.”

---

## Preferred Stack Context

Typical stack:

* Python
* FastAPI / Flask
* Node.js
* React / Next.js
* PostgreSQL / MongoDB
* Docker
* LangChain / LangGraph
* RAG pipelines
* AI agents and automation systems

Preferred patterns:

* modular architecture
* service separation
* async workflows
* clean APIs
* reusable utilities
* explicit typing where useful

Avoid:

* magic abstractions
* over-engineering
* deeply nested logic
* giant files
* unnecessary dependencies

---

## Default Coding Behavior

Before writing code:

* inspect surrounding files first
* understand conventions
* preserve architecture consistency

When writing code:

* prioritize readability
* keep functions focused
* use descriptive names
* add comments only where necessary

When generating project structure:

* organize for scale
* separate business logic from infrastructure
* keep AI pipelines isolated from app logic

Always optimize for long-term maintainability and developer clarity.
Dont Repeat Yourself!

---

# Codebase Guide — Career Engine (Hire Journey)

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

AI-powered job search platform: upload a resume → discover jobs from ATS boards → keyword-score them → LLM-evaluate fit → tailor applications. Two top-level apps: `backend/` (FastAPI) and `frontend/` (Next.js).

## Commands

All backend commands run from `backend/` with the venv active (`source .venv/bin/activate`):

```bash
uvicorn app.main:app --reload      # dev server → http://localhost:8000 (docs at /docs)
pytest                             # run all tests
pytest tests/test_security.py      # single file
pytest tests/test_security.py::test_name -q   # single test
ruff check .                       # lint (rules E, F, I; line-length 100)
ruff check --fix .                 # autofix

alembic upgrade head                          # apply migrations (also needed on fresh setup)
alembic revision --autogenerate -m "message"  # generate a migration AFTER changing a model
```

Postgres runs in Docker (`career-engine-db`, db `career_engine`, user/pass `postgres`); see README for the one-time `docker run`. Frontend (from `frontend/`): `npm run dev`, `npm run build`, `npm run lint`.

## Backend architecture

Layered, fully async. Dependency direction is **api → services → models/sources**; keep business logic in services, not route handlers.

- `app/api/v1/` — thin FastAPI route handlers, one module per domain (auth, profile, resumes, jobs, search, evaluations, applications, notes), all mounted under `/api/v1` in `api/v1/__init__.py`. Auth via `Depends(get_current_user)` from `api/deps.py` (decodes a PyJWT bearer token → `User`).
- `app/services/` — business logic. `search_service.run_search` is the core orchestrator: a 4-stage pipeline (create `SearchSession` → `fetch_service.fetch_all` companies concurrently → `job_service.upsert_jobs` with DB-level dedup → `score_service.keyword_score` into `job_scores`). `get_results` is the read path, ranking by score desc.
- `app/sources/` — ATS adapters (Greenhouse, Ashby, Lever) implementing the `JobSource` Protocol in `base.py` (returns `RawJob` dataclasses). Registered in the `SOURCES` dict (`sources/__init__.py`); `fetch_service` looks adapters up by `company.source.name`. A failed fetch for one company is logged and skipped, never aborting the scan.
- `app/agents/` — LangGraph/LangChain LLM work, isolated from app logic. `evaluator.evaluate_job` returns a Pydantic-structured `EvaluationResult` (match_score + strengths/weaknesses/recommendations).
- `app/models/` — SQLAlchemy 2.0 ORM (async). All models are imported in `models/__init__.py` (Alembic autogenerate needs them registered on `Base.metadata`). `database.py` exposes the async engine, `AsyncSessionLocal`, and the `get_db` session dependency.
- `app/schemas/` — Pydantic request/response models. `config.py` — pydantic-settings from `.env`. `exceptions.py` / `messages.py` / `utils/patterns.py` — centralized exceptions, user-facing strings, and regexes (keep them there, don't inline).

## Key conventions & gotchas

- **Everything DB-facing is async** — use `await`, `AsyncSession`, and `selectinload` for relationships (see `search_service.get_results`). No sync SQLAlchemy sessions.
- **LLM provider fallback**: keys are tried in order **Groq → Gemini → OpenAI** (`config.py`, `agents/evaluator._build_providers`). Any one configured key works; at least one is required for AI features. The README env table under-documents Groq — check `config.py` for the full set.
- **Job filtering** (title/location allow/block lists) lives in `config/companies.yaml`, loaded by `fetch_service`. Companies to scan are seeded via `scripts/seed_companies.py`.
- **New model → migration**: add the model, import it in `models/__init__.py`, then `alembic revision --autogenerate`. Migration heads occasionally need merging (see the `*_merge_*` revisions).
- Python **3.13** required (3.14 has no wheels for several deps). Ruff line-length 100; pytest is `asyncio_mode = "auto"`.

## Frontend

⚠️ The README still describes the *old* static HTML/JS frontend — that has been replaced. `frontend/` is now a **Next.js 16 + React 19 + Tailwind v4** app (App Router, TypeScript). Per `frontend/AGENTS.md`, this Next.js version has **breaking changes vs. training data** — read the relevant guide in `frontend/node_modules/next/dist/docs/` before writing frontend code; do not assume older Next.js conventions.

> Note: `CLAUDE.md` imports `@PRD.md`, which is not present in the repo — that import currently resolves to nothing.

<<<<<<< Updated upstream
=======
## Agent skills

### Issue tracker

Work is tracked in Jira project HIJ (`hirejourney`). Agents prepare ticket drafts only and must not create, update, transition, comment on, or label Jira issues. See `docs/agents/issue-tracker.md`.

### Triage labels

Ticket drafts use the canonical triage labels `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

This repository uses a single-context domain layout: `CONTEXT.md` at the repository root and architectural decisions under `docs/adr/`. See `docs/agents/domain.md`.
>>>>>>> Stashed changes
