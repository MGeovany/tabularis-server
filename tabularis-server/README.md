# tabularis-server

FastAPI backend for **Tabular**: PDF table extraction to Excel (XLSX), with Supabase Auth, usage limits (Free/Pro), and audit logging.

## Stack

- Python 3.11+, FastAPI, Uvicorn
- SQLAlchemy 2.0, PostgreSQL (Supabase or Neon)
- Supabase Auth (JWT validation)
- pdfplumber, openpyxl, pandas for PDF → Excel conversion

## Setup

1. Create a virtualenv and install:

   ```bash
   uv venv && source .venv/bin/activate
   uv pip install -e .
   ```

2. Copy env and set variables:

   ```bash
   cp .env.example .env
   # Edit .env: DATABASE_URL, SUPABASE_URL, SUPABASE_JWT_SECRET, CORS_ORIGINS
   ```

3. Run migrations:

   ```bash
   alembic upgrade head
   ```

4. Start the server:

   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## API

- `GET /api/v1/me` — Current user + plan (Bearer JWT; creates user if missing)
- `POST /api/v1/convert/pdf-to-excel` — Upload PDF, get XLSX stream (Bearer JWT)
- `GET /api/v1/history?limit=20&offset=0` — User conversion history
- `GET /api/v1/usage` — conversions_used, conversions_limit, plan

Docs: `http://localhost:8000/docs` when running.

## Deploy (Render / Railway / Cloud Run)

- **Environment variables**: Set `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_JWT_SECRET`, `CORS_ORIGINS` (and optionally `MAX_PDF_BYTES`, `MAX_PDF_PAGES`).
- **Database**: Run migrations once (e.g. `alembic upgrade head`) in a release phase or one-off job before starting the app.
- **Docker**: Use the provided `Dockerfile`; build and run with port 8000 exposed.
- **Rate limiting**: Optional. To add per-user or per-IP limits (e.g. 10 conversions/day), use a library like `slowapi` or a Redis/counter in `app/core/security.py` and attach to the convert endpoint.

## Security

- PDFs are not stored on disk; conversion runs in memory (or temp file deleted immediately).
- Only HTTPS in production; CORS restricted to frontend origin.
- Do not log PDF content; only metadata (size, pages, filename, user) is logged.
