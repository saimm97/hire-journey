# Hire Journey

End-to-end AI-powered job search platform. Upload your resume, discover relevant jobs from top ATS boards, get scored recommendations, deep CV evaluations, and tailored applications.

## Stack

- **Backend:** FastAPI, SQLAlchemy 2.0 (async), Alembic, PostgreSQL
- **Background jobs:** Celery with Redis as broker and result backend
- **AI:** LangGraph agents
- **Job Sources:** Greenhouse, Ashby, Lever  (ATS Job Boards, free-to-use)
- **Frontend:** static HTML/CSS/JS (sign-in/up, CV upload); Next.js planned

---

## Prerequisites

- Python 3.13 (**3.14 is not yet supported** — several dependencies have no
  wheels for it and fail to build)
- Docker
- Git

---



## Getting Started



### 1. Clone the repo

```bash
git clone https://github.com/careerEnginee/career-engine
cd career-engine
```



### 2. Install Docker

**Linux:**

```bash
sudo apt-get update && sudo apt-get install -y docker.io
sudo systemctl start docker && sudo systemctl enable docker
sudo usermod -aG docker $USER
# log out and back in after this
```

**macOS:** Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop), then open it to start the engine.

Verify:

```bash
docker --version
```



### 3. Start the database

Run this once — Docker keeps the container and its data across restarts:

```bash
docker run -d \
  --name career-engine-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=career_engine \
  -p 5432:5432 \
  postgres:16
```

Verify it's running:

```bash
docker ps
# career-engine-db should appear with status "Up"
```



### 4. Start Redis

Redis carries Celery task messages and short-lived task results. Run this once;
Docker preserves its data in a named volume:

```bash
docker run -d \
  --name hire-journey-redis \
  -p 127.0.0.1:6379:6379 \
  -v hire-journey-redis-data:/data \
  redis:8-alpine \
  redis-server --appendonly yes
```

Verify the scheduler broker is reachable:

```bash
docker exec hire-journey-redis redis-cli ping
# PONG
```

### 5. Configure environment

```bash
cp backend/.env.example backend/.env
```

Open `backend/.env` and fill in:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/career_engine
SECRET_KEY=<generate one below>
GEMINI_API_KEY=<your Gemini API key>
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

Generate a secret key:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```



### 6. Install dependencies

```bash
cd backend
python3.13 -m venv .venv         # use a 3.13 interpreter (see Prerequisites)
source .venv/bin/activate        # macOS/Linux
pip install -r requirements-dev.txt
```



### 7. Run migrations

Migrations are committed to the repo, so a fresh setup only needs to apply them:

```bash
alembic upgrade head
```

(You only run `alembic revision --autogenerate` later, after changing a model — see [Day-to-day commands](#day-to-day-commands).)

### 8. Start the backend

```bash
uvicorn app.main:app --reload
```

Server runs at [http://localhost:8000](http://localhost:8000)
Interactive API docs at [http://localhost:8000/docs](http://localhost:8000/docs)

### 9. Start scheduled job ingestion

Scheduled ingestion is not hosted inside FastAPI. Keep two additional backend
processes running: one worker that executes ingestion tasks and exactly one Beat
process that publishes them. Both commands must run from `backend/` with the
virtual environment active.

Terminal 1 — ingestion worker:

```bash
celery \
  -A app.celery_app:celery_app \
  worker \
  --loglevel=INFO \
  --queues=ingestion \
  --pool=solo
```

Terminal 2 — scheduler:

```bash
celery -A app.celery_app:celery_app beat --loglevel=INFO
```

Beat publishes a global scan at `07:00` and `15:00` UTC. It does not run a scan
immediately on startup; use `python scripts/ingest_jobs.py` when an operator needs
an immediate or recovery run. The PostgreSQL advisory lock safely skips either
entry point when another scan is already active.

The prerequisites for successful scheduled ingestion are:

- PostgreSQL is reachable, migrated, and contains companies with non-null
  `careers_url` values;
- Redis is reachable at the configured broker and result-backend URLs;
- at least one worker is consuming the `ingestion` queue;
- exactly one Beat process owns the schedule;
- the worker has the same backend environment as FastAPI and outbound HTTPS
  access to the supported ATS hosts; and
- the machine clock is accurate because the schedule is evaluated in UTC.

FastAPI and the frontend may be stopped while scheduled ingestion runs. See the
[job-ingestion runbook](docs/runbooks/job-ingestion.md) for verification,
production topology, and troubleshooting.

### 10. Start the frontend

The frontend is static — no build step. Serve it from its own directory in a second terminal:

```bash
cd frontend
python3 -m http.server 5500
```

Open [http://localhost:5500](http://localhost:5500). It calls the backend at `http://localhost:8000`, configured in `frontend/config.js`.

> **Google sign-in (optional):** set `GOOGLE_CLIENT_ID` in `backend/.env`, then add `http://localhost:5500` to your OAuth client's **Authorized JavaScript origins** in Google Cloud Console. Leave the variable blank to hide the button.

---



## Browsing the database



### Option 1 — DBeaver (GUI, recommended)

Free database client with a visual table browser and SQL editor.

**Linux:**

```bash
sudo snap install dbeaver-ce
```

**macOS:**

```bash
brew install --cask dbeaver-community
```

Or download from [dbeaver.io](https://dbeaver.io/download).

**Connect:**

1. Open DBeaver → New Database Connection → PostgreSQL
2. Fill in:
  - Host: `localhost`
  - Port: `5432`
  - Database: `career_engine`
  - Username: `postgres`
  - Password: `postgres`
3. Test Connection → Finish



### Option 2 — psql (CLI, quick checks)

```bash
docker exec -it career-engine-db psql -U postgres -d career_engine
```

Useful commands inside psql:

```sql
\dt                  -- list all tables
\d users             -- show columns of a table
SELECT * FROM users; -- run any query
\q                   -- quit
```

---



## Day-to-day commands

```bash
# stop the database (data is preserved)
docker stop career-engine-db

# start it again next session
docker start career-engine-db

# start/stop the Celery broker
docker start hire-journey-redis
docker stop hire-journey-redis

# run the ingestion worker (from backend/ with .venv active)
celery -A app.celery_app:celery_app worker -l INFO -Q ingestion --pool=solo

# run exactly one scheduler process
celery -A app.celery_app:celery_app beat -l INFO

# operator-controlled immediate ingestion fallback
python scripts/ingest_jobs.py

# after changing a model, generate and apply a migration
alembic revision --autogenerate -m "describe the change"
alembic upgrade head

# run tests
pytest
```

---



## Documentation

- [Documentation index](docs/README.md)
- [End-to-end user onboarding flow](docs/architecture/user-onboarding-flow.md)
- [Current database schema and ERD](docs/architecture/database-schema.md)
- [Job ingestion architecture](docs/architecture/job-ingestion.md)
- [Operate scheduled job ingestion](docs/runbooks/job-ingestion.md)
- [ADR-0004: Schedule ingestion with Celery and Redis](docs/adr/0004-celery-redis-ingestion-scheduling.md)
- [Architecture decisions](docs/adr/)

Update the relevant documentation in the same pull request as schema or
business-rule changes.

---



## Project structure

```
career-engine/
├── docs/                  # architecture, ADRs and progress
├── backend/
│   ├── app/
│   │   ├── api/v1/        # FastAPI route handlers
│   │   ├── models/        # SQLAlchemy ORM models
│   │   ├── schemas/       # Pydantic request/response schemas
│   │   ├── services/      # Business logic
│   │   ├── sources/       # ATS job source adapters
│   │   ├── agents/        # LangGraph agents
│   │   ├── tasks/         # Celery delivery adapters
│   │   ├── celery_app.py  # Celery routing and Beat schedule
│   │   ├── config.py      # App settings
│   │   ├── database.py    # DB engine and session
│   │   └── main.py        # FastAPI entry point
│   ├── config/
│   │   └── companies.yaml # Companies to fetch jobs from
│   ├── alembic/           # Database migrations
│   ├── tests/
│   └── pyproject.toml
└── frontend/              # static sign-in/up + CV upload (config.js, strings.js, app.js)
```

---



## Environment variables


| Variable                      | Required | Description                                                       |
| ----------------------------- | -------- | ----------------------------------------------------------------- |
| `DATABASE_URL`                | Yes      | PostgreSQL connection string                                      |
| `SECRET_KEY`                  | Yes      | JWT signing secret — keep this private                            |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No       | Token expiry, default 60                                          |
| `GOOGLE_CLIENT_ID`            | No       | OAuth Web client id for "Continue with Google"; blank disables it |
| `MAX_UPLOAD_MB`               | No       | Max CV upload size in MB, default 5                               |
| `ATS_HTTP_TIMEOUT_SECONDS`    | No       | ATS HTTP operation timeout, default 10 seconds                    |
| `ATS_MAX_RESPONSE_MB`         | No       | Maximum decoded ATS response size, default 50 MB                  |
| `ATS_MAX_ATTEMPTS`            | No       | Maximum attempts for transient ATS failures, default 3            |
| `ATS_GLOBAL_CONCURRENCY`      | No       | Maximum concurrent company fetches, default 12                    |
| `ATS_HTTP_MAX_CONNECTIONS`    | No       | Shared ATS HTTP connection-pool limit, default 20                 |
| `ATS_HTTP_MAX_KEEPALIVE_CONNECTIONS` | No | Shared ATS keep-alive pool limit, default 10                  |
| `CELERY_BROKER_URL`           | No       | Redis broker URL, default `redis://localhost:6379/0`               |
| `CELERY_RESULT_BACKEND`       | No       | Redis result URL, default `redis://localhost:6379/1`               |
| `GEMINI_API_KEY`              | Yes      | Gemini API key for AI features                                    |
| `OPENAI_API_KEY`              | No       | Optional OpenAI fallback                                          |


> **Never commit** `.env` **to git.** Each developer maintains their own local copy.
