# tabularis-server — FastAPI backend for Tabular
FROM python:3.11-slim

WORKDIR /app

# Install system deps for pdfplumber/PDF (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

COPY app/ ./app/
COPY alembic.ini ./

# Run migrations and start server (migrations can be run as separate step in Render/Railway)
ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# Default: run uvicorn. Override with CMD or run migrations in a separate job.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
