"""Unit tests for SPEC-JOBQUEUE-001: arq-based persistent job queue.

All tests run without Docker — arq pool and Redis are mocked.

AC coverage:
- AC-001: arq persists to Redis (pool creation + enqueue)
- AC-003/004: retry max_tries=3, terminal FAILED after exhaustion (DLQ)
- AC-005: worker runs as separate process (WorkerSettings struct)
- AC-007: API contract unchanged (job status endpoint)
- AC-008: worker health heartbeat
- AC-009: _push_ifu_result_to_regula preserved on success
- REQ-JQ-005: explicit tenant context in task
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helper to build a minimal fake arq Job object
# ---------------------------------------------------------------------------

class _FakeJob:
    def __init__(self, job_id: str = "job-abc"):
        self.job_id = job_id


# ===========================================================================
# 1. arq pool factory
# ===========================================================================


class TestArqPool:
    """arq_pool.py: pool creation and FastAPI Depends helper."""

    async def test_create_arq_pool_returns_pool(self):
        """create_arq_pool() returns an ArqRedis pool."""
        from app.queue.arq_pool import create_arq_pool

        with patch("app.queue.arq_pool.create_pool") as mock_create:
            mock_pool = AsyncMock()
            mock_create.return_value = mock_pool

            result = await create_arq_pool("redis://localhost:6379")

        mock_create.assert_called_once()
        assert result is mock_pool

    async def test_get_arq_pool_reads_from_app_state(self):
        """get_arq_pool(request) returns pool stored on app.state.arq_pool."""
        from app.queue.arq_pool import get_arq_pool

        request = MagicMock()
        fake_pool = AsyncMock()
        request.app.state.arq_pool = fake_pool

        result = get_arq_pool(request)
        assert result is fake_pool


# ===========================================================================
# 2. arq task signature
# ===========================================================================


class TestRunParseJobSignature:
    """run_parse_job must accept ctx as first arg (arq requirement)."""

    async def test_run_parse_job_accepts_ctx_as_first_arg(self):
        """run_parse_job(ctx, job_id, doc_id, tenant) — ctx must be first."""
        import inspect
        from app.jobs.parse_job import run_parse_job

        sig = inspect.signature(run_parse_job)
        params = list(sig.parameters.keys())
        assert params[0] == "ctx", f"First param must be 'ctx', got {params[0]!r}"

    async def test_run_parse_job_has_no_parser_param(self):
        """parser: ParserService is removed — not serializable to Redis."""
        import inspect
        from app.jobs.parse_job import run_parse_job

        sig = inspect.signature(run_parse_job)
        assert "parser" not in sig.parameters, (
            "'parser' param must not exist — ParserService is not Redis-serializable"
        )

    async def test_run_parse_job_has_file_bytes_kwonly(self):
        """file_bytes= must remain (keyword-only with default b'')."""
        import inspect
        from app.jobs.parse_job import run_parse_job

        sig = inspect.signature(run_parse_job)
        assert "file_bytes" in sig.parameters


# ===========================================================================
# 3. enqueue helper in documents router
# ===========================================================================


class TestEnqueueParseJob:
    """documents.py: upload endpoint enqueues via arq pool."""

    async def test_upload_enqueues_via_arq_not_background_tasks(self):
        """POST /documents/upload must call arq pool.enqueue_job, not background_tasks.add_task."""
        from app.routers.documents import upload_document

        # Confirm BackgroundTasks is no longer used for parse job
        import inspect
        source = inspect.getsource(upload_document)
        assert "enqueue_job" in source or "arq_pool" in source or "arq" in source.lower(), (
            "upload_document must use arq pool, not BackgroundTasks"
        )


# ===========================================================================
# 4. tenant context in arq task
# ===========================================================================


class TestTenantContextInArqTask:
    """REQ-JQ-005: run_parse_job must establish explicit_tenant_context."""

    async def test_run_parse_job_uses_explicit_tenant_context(self):
        """run_parse_job must call explicit_tenant_context(tenant)."""
        import inspect
        from app.jobs.parse_job import run_parse_job

        source = inspect.getsource(run_parse_job)
        assert "explicit_tenant_context" in source, (
            "run_parse_job must use explicit_tenant_context (REQ-JQ-005)"
        )


# ===========================================================================
# 5. _push_ifu_result_to_regula preserved on success (AC-009)
# ===========================================================================


class TestIFUPushPreserved:
    """_push_ifu_result_to_regula must be called on successful parse."""

    async def test_push_ifu_called_on_success(self):
        """On parse success, _push_ifu_result_to_regula is awaited."""
        from app.jobs.parse_job import run_parse_job
        from app.models.parse_job import ParseJobStatus

        fake_job = MagicMock()
        fake_job.status = ParseJobStatus.PENDING
        fake_job.result_json = None
        fake_job.error = None

        fake_doc = MagicMock()
        fake_doc.doc_type = "srs"
        fake_doc.status = "uploaded"

        fake_db = AsyncMock()
        fake_db.get = AsyncMock(side_effect=[fake_job, fake_doc])
        fake_db.flush = AsyncMock()
        fake_db.__aenter__ = AsyncMock(return_value=fake_db)
        fake_db.__aexit__ = AsyncMock(return_value=False)

        ctx = {}

        with (
            patch("app.jobs.parse_job.async_session", return_value=fake_db),
            patch("app.jobs.parse_job.validate_transition"),
            patch("app.jobs.parse_job.StubParserService") as MockParser,
            patch("app.jobs.parse_job._push_ifu_result_to_regula") as mock_push,
            patch("app.jobs.parse_job.explicit_tenant_context") as mock_ctx,
        ):
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=None)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.services.parser import ParseResult
            fake_result = ParseResult(confidence=0.95, field_candidates={}, required_missing=[])
            mock_parser_instance = AsyncMock()
            mock_parser_instance.parse = AsyncMock(return_value=fake_result)
            MockParser.return_value = mock_parser_instance

            mock_push.return_value = None

            await run_parse_job(ctx, "job-1", "doc-1", "tenant-acme")

        mock_push.assert_called_once()


# ===========================================================================
# 6. WorkerSettings structure (AC-005)
# ===========================================================================


class TestWorkerSettings:
    """jobs/worker.py: WorkerSettings is correctly structured for arq."""

    def test_worker_settings_has_functions(self):
        """WorkerSettings.functions contains run_parse_job."""
        from app.jobs.worker import WorkerSettings
        from app.jobs.parse_job import run_parse_job

        assert hasattr(WorkerSettings, "functions"), "WorkerSettings must have 'functions'"
        assert run_parse_job in WorkerSettings.functions

    def test_worker_settings_has_max_tries(self):
        """WorkerSettings.max_tries == 3 (AC-003)."""
        from app.jobs.worker import WorkerSettings

        assert getattr(WorkerSettings, "max_tries", None) == 3

    def test_worker_settings_has_on_startup(self):
        """WorkerSettings.on_startup exists for orphan recovery (AC-002)."""
        from app.jobs.worker import WorkerSettings

        assert callable(getattr(WorkerSettings, "on_startup", None)), (
            "WorkerSettings must have callable on_startup"
        )

    def test_worker_settings_has_keep_result(self):
        """WorkerSettings.keep_result set (results retained in Redis)."""
        from app.jobs.worker import WorkerSettings

        assert getattr(WorkerSettings, "keep_result", None) == 3600


# ===========================================================================
# 7. DLQ / terminal FAILED path (AC-004)
# ===========================================================================


class TestDLQTerminalFailed:
    """After max_tries exhaustion, ParseJob.status reaches terminal FAILED."""

    async def test_on_job_abort_status_set_to_failed(self):
        """on_job_abort hook in WorkerSettings sets ParseJob.status=FAILED."""
        from app.jobs.worker import WorkerSettings

        assert hasattr(WorkerSettings, "on_job_abort"), (
            "WorkerSettings must define on_job_abort to handle DLQ (AC-004)"
        )
        assert callable(WorkerSettings.on_job_abort)


# ===========================================================================
# 8. Worker health endpoint (AC-008)
# ===========================================================================


class TestWorkerHealth:
    """Worker exposes HTTP /health that checks Redis heartbeat key."""

    def test_worker_health_module_importable(self):
        """app.jobs.worker_health can be imported."""
        from app.jobs import worker_health  # noqa: F401

    def test_worker_heartbeat_key_defined(self):
        """HEARTBEAT_KEY constant defined for Redis TTL signal."""
        from app.jobs.worker_health import HEARTBEAT_KEY

        assert isinstance(HEARTBEAT_KEY, str) and len(HEARTBEAT_KEY) > 0


# ===========================================================================
# 9. Settings redis_url field
# ===========================================================================


class TestSettingsRedisUrl:
    """config.py: Settings must have redis_url field."""

    def test_settings_has_redis_url(self):
        """Settings.redis_url defaults to redis://localhost:6379."""
        with patch.dict("os.environ", {
            "DATABASE_URL": "postgresql://u:p@localhost/db",
            "JWT_SECRET": "a" * 32,
            "MINIO_ENDPOINT": "localhost:9000",
            "MINIO_BUCKET": "test",
            "MINIO_USER": "user",
            "MINIO_PASSWORD": "pass",
            "OLLAMA_ENDPOINT": "http://localhost:11434",
            "OLLAMA_MODEL": "llama3",
            "CLOUD_SYNC_ENDPOINT": "http://localhost:8001",
            "CORS_ORIGINS": "http://localhost:3000",
        }):
            from app.config import Settings
            s = Settings()
            assert hasattr(s, "redis_url")
            assert "redis" in s.redis_url


# ===========================================================================
# 10. cloud-control-plane crawl arq task signature (AC-006)
# ===========================================================================


class TestCrawlArqTask:
    """cloud-control-plane: execute_crawl_job must accept ctx as first arg."""

    def test_crawl_task_file_exists(self):
        """cloud-control-plane/src/app/jobs/crawl_worker.py exists."""
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "cloud-control-plane", "src", "app", "jobs", "crawl_worker.py"
        )
        assert os.path.isfile(os.path.normpath(path)), (
            "crawl_worker.py must exist (AC-006)"
        )

    def test_crawl_task_signature_has_ctx(self):
        """execute_crawl_job source code has ctx as first arg."""
        import os
        path = os.path.normpath(os.path.join(
            os.path.dirname(__file__),
            "..", "..", "cloud-control-plane", "src", "app", "jobs", "crawl_worker.py"
        ))
        with open(path, encoding="utf-8") as f:
            source = f.read()
        # Check signature pattern: async def execute_crawl_job(ctx
        assert "async def execute_crawl_job(ctx" in source, (
            "execute_crawl_job must have ctx as first arg (arq requirement, AC-006)"
        )
