# tabularis-server

FastAPI backend for **Tabular**: PDF table extraction to Excel (XLSX), with Supabase Auth, usage limits (Free/Pro), and audit logging.

## Stack

- Python 3.11+, FastAPI, Uvicorn
- SQLAlchemy 2.0, PostgreSQL (Supabase or Neon)
- Supabase Auth (JWT validation)
- pdfplumber, openpyxl, pandas for PDF → Excel conversion

## Security

- PDFs are not stored on disk; conversion runs in memory (or temp file deleted immediately).
- Only HTTPS in production; CORS restricted to frontend origin.
- Do not log PDF content; only metadata (size, pages, filename, user) is logged.
