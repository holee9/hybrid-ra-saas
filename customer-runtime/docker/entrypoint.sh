#!/bin/bash
set -e

# Run database migrations
python -m alembic upgrade head

# Start API server
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
