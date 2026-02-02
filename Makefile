.PHONY: run server install migrate migrate-up migrate-down ci test

# Prefer venv if present, else uv run
VENV := .venv
ifeq ($(wildcard $(VENV)/bin/uvicorn),)
  RUN_SERVER := uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  RUN_ALEMBIC := uv run alembic
else
  RUN_SERVER := $(VENV)/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  RUN_ALEMBIC := $(VENV)/bin/python -m alembic
endif

run:
	$(RUN_SERVER)

server: run

install:
	uv venv && uv pip install -e .

test:
	uv run pytest

ci:
	uv run python -m compileall -q app
	uv run pytest -q

migrate: migrate-up

migrate-up:
	$(RUN_ALEMBIC) upgrade head

migrate-down:
	$(RUN_ALEMBIC) downgrade -1
