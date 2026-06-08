"""T-005: Integration test — alembic upgrade head creates all 9 tables + pgvector."""
import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from tests.conftest import skip_no_docker

pytestmark = skip_no_docker


@pytest.mark.integration
async def test_migration_creates_all_tables(run_alembic, db_url):
    """After upgrade head: pgvector extension + 9 tables must exist."""
    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        # Check pgvector extension
        result = await conn.execute(
            text("SELECT extname FROM pg_extension WHERE extname='vector'")
        )
        row = result.fetchone()
        assert row is not None, "pgvector extension not installed"

        # Check all 9 table names
        expected_tables = {
            "products", "documents", "requirements", "risks",
            "controls", "evidences", "findings", "audit_events", "parse_jobs",
        }
        result = await conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )
        )
        actual_tables = {row[0] for row in result.fetchall()}
        missing = expected_tables - actual_tables
        assert not missing, f"Missing tables: {missing}"

    await engine.dispose()
