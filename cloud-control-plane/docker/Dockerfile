# Stage 1: builder — compile dependencies with uv
FROM python:3.13-slim AS builder
WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml .
# Compile pinned requirements from pyproject.toml (excludes dev extras)
RUN uv pip compile pyproject.toml -o requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: runtime — minimal image
FROM python:3.13-slim AS runtime
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source and alembic migrations
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONPATH=/app/src

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
