# Hire Journey

End-to-end AI-powered job search platform. Upload your resume, discover relevant jobs from top ATS boards, get scored recommendations, deep CV evaluations, and tailored applications.

## Stack

- **Backend:** FastAPI, SQLAlchemy 2.0 (async), Alembic, PostgreSQL
- **AI:** LangGraph agents
- **Job Sources:** Greenhouse, Ashby, Lever  (ATS Job Boards, free-to-use)
- **Frontend:** Next.js (coming soon)

---

## Prerequisites

- Python 3.13+
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
```

Open `.env` and fill in:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/career_engine
SECRET_KEY=<generate one below>
GEMINI_API_KEY=<your Gemini API key>
```

Generate a secret key:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Install dependencies

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate      # macOS/Linux
pip install -r requirements-dev.txt
```

### 6. Run migrations

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

### 7. Start the server

```bash
uvicorn app.main:app --reload
```

Server runs at [http://localhost:8000](http://localhost:8000)
Interactive API docs at [http://localhost:8000/docs](http://localhost:8000/docs)

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
pytest
```

---

## Project structure

```
career-engine/
├── backend/
│   ├── app/
│   │   ├── api/v1/        # FastAPI route handlers
│   │   ├── models/        # SQLAlchemy ORM models
│   │   ├── schemas/       # Pydantic request/response schemas
│   │   ├── services/      # Business logic
│   │   ├── sources/       # ATS job source adapters
│   │   ├── agents/        # LangGraph agents
│   │   ├── config.py      # App settings
│   │   ├── database.py    # DB engine and session
│   │   └── main.py        # FastAPI entry point
│   ├── config/
│   │   └── companies.yaml # Companies to fetch jobs from
│   ├── alembic/           # Database migrations
│   ├── tests/
│   └── pyproject.toml
└── frontend/              # Next.js (coming soon)
```

---

## Environment variables


| Variable                      | Required | Description                            |
| ----------------------------- | -------- | -------------------------------------- |
| `DATABASE_URL`                | Yes      | PostgreSQL connection string           |
| `SECRET_KEY`                  | Yes      | JWT signing secret — keep this private |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No       | Token expiry, default 60               |
| `GEMINI_API_KEY`              | Yes      | Gemini API key for AI features         |
| `OPENAI_API_KEY`              | No       | Optional OpenAI fallback               |


> **Never commit `.env` to git.** Each developer maintains their own local copy.

