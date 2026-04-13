# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project
ProbResolve — consumer complaint board for India. FastAPI backend serving JSON API + server-rendered admin panel.

## Stack
- Python 3.12+, FastAPI 0.115+, SQLAlchemy 2.0 async, asyncpg, Alembic, Pydantic v2
- Database: PostgreSQL via Supabase (use Session Pooler URL, not direct — direct is IPv6-only)
- File storage: Supabase Storage (use SUPABASE_SERVICE_KEY for uploads, not anon key)

## Run
```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

## Commands
```bash
alembic upgrade head                   # Apply migrations
alembic revision --autogenerate -m ""  # Generate new migration
ruff check .                           # Lint
pytest                                 # Run tests
```

## Key facts
- POST /api/problems accepts multipart form, returns `{"id", "slug"}` 201
- `amount_lost` stored in rupees (₹)
- Admin auth: `` query param
- supabase-py storage is synchronous — always use `asyncio.to_thread()`
- DATABASE_URL username format for pooler: `postgres.PROJECTREF`

## Architecture
- **Entry point**: `app/main.py` — app setup, CORS, exception handlers, router registration
- **Routes**: `app/routes/api_routes.py` (core REST), `app/routes/problems.py` (POST /api/problems), `app/routes/admin.py`
- **Services**: `app/services/` — business logic between routes and DB
- **Models**: `app/models.py` — Domain, Category, Problem, Evidence, Upvote, Report
- **Config**: `app/config.py` — reads `.env`
- **User identity**: fingerprint (hash of IP + User-Agent) for upvotes/reports; no auth system
- **Slugs**: not unique, SEO-only; UUID is the real identity
