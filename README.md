# Hire Journey

Resume-first user onboarding for Hire Journey. Users can authenticate, upload a
PDF or DOCX resume, review extracted profile data, choose preferences, and
continue into the application with a complete profile.

## Stack

- **Backend:** FastAPI, SQLAlchemy 2.0 (async), Alembic, PostgreSQL
- **Extraction:** Groq, Gemini, or OpenAI through LangChain provider packages
- **Frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS

---

## Prerequisites

- Python 3.13 (3.11–3.13 supported; **3.14 is not yet supported** — several dependencies have no wheels for it and fail to build)
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



### 4. Configure environment

```bash
cd backend
cp .env.example .env
cd ../frontend
cp .env.example .env
```

Open `.env` and fill in:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/career_engine
SECRET_KEY=<generate one below>
GROQ_API_KEY=<set at least one supported provider key>
```

Generate a secret key:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```



### 5. Install dependencies

```bash
cd backend
python3.13 -m venv .venv         # use a 3.13 interpreter (see Prerequisites)
source .venv/bin/activate        # macOS/Linux
pip install -r requirements-dev.txt

cd ../frontend
npm ci
```



### 6. Run migrations

Migrations are committed to the repo, so a fresh setup only needs to apply them:

```bash
alembic upgrade head
```

(You only run `alembic revision --autogenerate` later, after changing a model — see [Day-to-day commands](#day-to-day-commands).)

### 7. Start the backend

```bash
uvicorn app.main:app --reload
```

Server runs at [http://localhost:8000](http://localhost:8000)
Interactive API docs at [http://localhost:8000/docs](http://localhost:8000/docs)

### 8. Start the frontend

Run the Next.js development server from a second terminal:

```bash
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). It calls the backend URL
configured by `NEXT_PUBLIC_API_URL` in `frontend/.env`.

> **Google sign-in (optional):** set `GOOGLE_CLIENT_ID` in `backend/.env` and
> `NEXT_PUBLIC_GOOGLE_CLIENT_ID` in `frontend/.env`, then add
> `http://localhost:3000` to the OAuth client's authorized JavaScript origins.

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

# after changing a model, generate and apply a migration
alembic revision --autogenerate -m "describe the change"
alembic upgrade head

# run tests
cd backend && pytest
cd ../frontend && npm test
```

---



## Documentation

- [Documentation index](docs/README.md)
- [End-to-end user onboarding flow](docs/architecture/user-onboarding-flow.md)
- [Current database schema and ERD](docs/architecture/database-schema.md)
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
│   │   ├── utils/         # document parsing, normalization, and LLM extraction
│   │   ├── config.py      # App settings
│   │   ├── database.py    # DB engine and session
│   │   └── main.py        # FastAPI entry point
│   ├── alembic/           # Database migrations
│   ├── tests/
│   └── pyproject.toml
└── frontend/              # Next.js authentication, onboarding, and profile UI
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
| `MAX_RESUMES_PER_USER`        | No       | Per-user resume limit, default 2                                  |
| `GROQ_API_KEY`                | No       | Preferred resume-extraction provider key                          |
| `GEMINI_API_KEY`              | No       | Gemini resume-extraction provider key                             |
| `OPENAI_API_KEY`              | No       | Optional OpenAI fallback                                          |

At least one LLM provider key is required to extract structured resume data.
The frontend additionally reads `NEXT_PUBLIC_API_URL` and
`NEXT_PUBLIC_GOOGLE_CLIENT_ID` from `frontend/.env`.


> **Never commit** `.env` **to git.** Each developer maintains their own local copy.
