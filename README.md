# CognitiveBrainDB

CognitiveBrainDB is a starter FastAPI project scaffolded for PostgreSQL access with synchronous SQLAlchemy 2.x and pgvector support.

## Tech Stack

- Python 3.11
- FastAPI
- Uvicorn
- SQLAlchemy 2.x (sync)
- psycopg (binary)
- pgvector
- python-dotenv
- pydantic
- alembic

## Project Structure

```text
cognitivebrain/
    __init__.py
    main.py
    config.py
    db.py
    models/
        __init__.py
        base.py
    services/
        __init__.py
    api/
        __init__.py
        routes.py
alembic/
    env.py
    script.py.mako
    versions/
```

## Quick Start

1. Create and activate a Python 3.11 virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy environment variables:
   ```bash
   cp .env.example .env
   ```
4. Run the application:
   ```bash
   uvicorn cognitivebrain.main:app --reload
   ```

5. Run tests:
   ```bash
   pytest
   ```

6. Run database migrations:
   ```bash
   make migrate
   ```

   This runs:
   ```bash
   alembic upgrade head
   ```

## Database Migrations

Alembic is scaffolded and configured to read `DATABASE_URL` from environment variables. Create a migration with:

```bash
alembic revision -m "init"
```

Apply migrations with:

```bash
make migrate
```

## Status

This is an initial scaffold only. Business logic and domain models are intentionally not implemented yet.
