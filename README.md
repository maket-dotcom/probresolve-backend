# ProbResolve — Backend

FastAPI backend for ProbResolve — a consumer complaint board for India.  
Serves a JSON API consumed by the Next.js frontend and an HTML admin dashboard.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI + Uvicorn |
| Database | PostgreSQL (Supabase) via asyncpg + SQLAlchemy 2 (async) |
| Migrations | Alembic |
| File Storage | Supabase Storage |
| Rate Limiting | SlowAPI |
| Validation | Pydantic v2 |
| Python | 3.12+ |

---

## Prerequisites

- **Python 3.12+**
- **A Supabase project** with:
  - A PostgreSQL database
  - A storage bucket (default name: `awaaz-uploads`)
- Access to the existing database (ask the team for the connection string)

---

## Local Setup

### 1. Clone & enter the directory

```bash
git clone <repo-url>
cd probresolve-backend
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -e ".[dev]"
```

### 4. Configure environment variables

Copy the example file and fill in the real values:

```bash
cp .env.example .env
```

Then edit `.env`:

```env
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:5432/postgres
SUPABASE_URL=https://<project-id>.supabase.co
SUPABASE_KEY=<anon-public-key>
SUPABASE_SERVICE_KEY=<service-role-secret-key>
SUPABASE_BUCKET=awaaz-uploads
ADMIN_KEY=<a-long-random-secret-you-generate>
ALLOWED_ORIGINS=http://localhost:3000
FRONTEND_URL=http://localhost:3000
```

> **Get credentials from the team** — never commit real values to git.  
> Generate `ADMIN_KEY` with: `python -c "import secrets; print(secrets.token_hex(32))"`

### 5. Run database migrations

```bash
alembic upgrade head
```

> Alembic reads `DATABASE_URL` from `.env` automatically via `env.py`.  
> If you add new models or change existing ones, create a migration:
> ```bash
> alembic revision --autogenerate -m "describe your change"
> alembic upgrade head
> ```

### 6. Start the dev server

```bash
uvicorn app.main:app --reload --port 8000
```

The API is now available at `http://localhost:8000`.

---

## Project Structure

```
app/
├── main.py           # FastAPI app setup, CORS, middleware
├── config.py         # Pydantic settings (reads from .env)
├── models.py         # SQLAlchemy ORM models
├── schemas.py        # Pydantic request/response schemas
├── database.py       # Async engine + session factory
├── deps.py           # FastAPI dependency: get_db
├── limiter.py        # SlowAPI rate limiter instance
├── escalation.py     # Domain → escalation links mapping
├── routes/
│   ├── api_routes.py # JSON API: problems, upvotes, reports, search, companies
│   ├── problems.py   # POST /api/problems (problem creation + file upload)
│   ├── admin.py      # HTML admin dashboard (key-protected)
│   └── pages.py      # Static HTML page routes
└── services/
    ├── problem_service.py  # DB queries for problems
    ├── upload_service.py   # Supabase Storage upload/delete
    ├── upvote_service.py   # Upvote deduplication logic
    ├── report_service.py   # Report deduplication logic
    └── category_service.py # Domain & category queries
alembic/              # Migration scripts
```

---

## Key API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/problems` | List problems (paginated, filterable by domain) |
| `POST` | `/api/problems` | Submit a new complaint (multipart form + file uploads) |
| `GET` | `/api/problems/{id}` | Problem detail with escalation links |
| `POST` | `/api/problems/{id}/upvote` | Upvote a problem |
| `POST` | `/api/problems/{id}/report` | Report a problem |
| `GET` | `/api/search` | Full-text search across problems |
| `GET` | `/api/domains` | List all domains |
| `GET` | `/api/companies` | Autocomplete company search |
| `GET` | `/admin` | Admin dashboard (requires `?key=<ADMIN_KEY>`) |
| `GET` | `/healthz` | Health check |

---

## Admin Dashboard

Visit `http://localhost:8000/admin?key=<your-ADMIN_KEY>`.  
From there you can verify, hide, resolve, or delete complaints.

---

## Running Tests

```bash
pytest
```

---

## Adding a Migration

After changing `app/models.py`:

```bash
alembic revision --autogenerate -m "short description"
alembic upgrade head
```

Always review the auto-generated migration file before running it.

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | asyncpg connection string |
| `SUPABASE_URL` | ✅ | Supabase project URL |
| `SUPABASE_KEY` | ✅ | Supabase anon/public key |
| `SUPABASE_SERVICE_KEY` | ✅ | Supabase service-role key (server-side only) |
| `SUPABASE_BUCKET` | ✅ | Storage bucket name |
| `ADMIN_KEY` | ✅ | Secret key for the admin dashboard |
| `ALLOWED_ORIGINS` | ❌ | Comma-separated CORS origins (default: `http://localhost:3000`) |
| `FRONTEND_URL` | ❌ | Used in admin redirect links (default: `http://localhost:3000`) |