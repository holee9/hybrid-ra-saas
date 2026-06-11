#!/bin/bash
set -e

# Run database migrations (DATABASE_URL env var is read by alembic/env.py)
python -m alembic upgrade head

# Start API server
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
