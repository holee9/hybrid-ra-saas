"""SPEC-PERMISSION-001: JWT user auth + RBAC — TDD test suite (RED phase).

All tests in this file are written BEFORE implementation.
They will fail until Phase 2 (GREEN) implementation is complete.
"""
import os

import pytest

# Set env before any app import
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
os.environ.setdefault("JWT_SECRET", "test-secret-32-bytes-minimum-here!")
os.environ.setdefault("MINIO_ENDPOINT", "http://minio:9000")
os.environ.setdefault("MINIO_BUCKET", "ra-documents")
os.environ.setdefault("MINIO_USER", "minioadmin")
os.environ.setdefault("MINIO_PASSWORD", "minioadmin")
os.environ.setdefault("OLLAMA_ENDPOINT", "http://ollama:11434")
os.environ.setdefault("OLLAMA_MODEL", "llama3.1:8b")
os.environ.setdefault("CLOUD_SYNC_ENDPOINT", "https://sync.example.com")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:8080")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# In-memory SQLite fixtures (no Docker required for SPEC-PERMISSION-001 tests)
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def perm_client():
    """Async httpx client backed by SQLite in-memory DB.

    Overrides get_db dependency to use the in-memory session.
    Overrides get_current_user to use the test DB.
    """
    from app.main import create_app
    from app.models.base import Base

    # Use aiosqlite in-memory for speed
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Create all tables (including new SPEC-PERMISSION-001 tables)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    from app.deps import get_db
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac, session_factory

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def perm_db(perm_client):
    """Yield the session_factory from perm_client fixture."""
    _, session_factory = perm_client
    return session_factory


@pytest_asyncio.fixture(scope="function")
async def ac(perm_client):
    """Yield only the AsyncClient."""
    client, _ = perm_client
    return client


# ---------------------------------------------------------------------------
# Helper: create a user directly in DB
# ---------------------------------------------------------------------------

async def _create_user(
    session_factory,
    *,
    tenant_id: str = "tenant-test",
    email: str = "user@example.com",
    password: str = "password123",
    role: str = "practitioner",
    is_active: bool = True,
) -> dict:
    """Insert a user and return dict with id + plain password."""
    from app.core.security import hash_password
    from app.models.user import User

    async with session_factory() as session:
        user = User(
            tenant_id=tenant_id,
            email=email,
            hashed_password=hash_password(password),
            role=role,
            is_active=is_active,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return {"id": user.id, "email": email, "password": password, "tenant_id": tenant_id}


async def _get_token(ac, *, tenant_id: str, email: str, password: str) -> str:
    """Login and return access_token."""
    resp = await ac.post(
        "/auth/login",
        json={"email": email, "password": password},
        headers={"X-Tenant-ID": tenant_id},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


# ===========================================================================
# 1. POST /auth/login
# ===========================================================================

@pytest.mark.asyncio
async def test_login_success(perm_client):
    ac, sf = perm_client
    await _create_user(sf, email="login@example.com", password="secret123")
    resp = await ac.post(
        "/auth/login",
        json={"email": "login@example.com", "password": "secret123"},
        headers={"X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert "expires_in" in body


@pytest.mark.asyncio
async def test_login_wrong_password(perm_client):
    ac, sf = perm_client
    await _create_user(sf, email="login2@example.com", password="correct")
    resp = await ac.post(
        "/auth/login",
        json={"email": "login2@example.com", "password": "wrong"},
        headers={"X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(perm_client):
    ac, _ = perm_client
    resp = await ac.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "any"},
        headers={"X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_inactive_user(perm_client):
    ac, sf = perm_client
    await _create_user(sf, email="inactive@example.com", password="pass", is_active=False)
    resp = await ac.post(
        "/auth/login",
        json={"email": "inactive@example.com", "password": "pass"},
        headers={"X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 401


# ===========================================================================
# 2. POST /auth/refresh
# ===========================================================================

@pytest.mark.asyncio
async def test_refresh_success(perm_client):
    ac, sf = perm_client
    await _create_user(sf, email="refresh@example.com", password="pass123")
    token = await _get_token(ac, tenant_id="tenant-test", email="refresh@example.com", password="pass123")
    resp = await ac.post(
        "/auth/refresh",
        json={"refresh_token": token},
        headers={"X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_refresh_inactive_user_rejected(perm_client):
    ac, sf = perm_client
    # Create active, get token, deactivate, then try refresh
    from app.models.user import User
    from sqlalchemy import select

    user_info = await _create_user(sf, email="deactivate@example.com", password="pass123")
    token = await _get_token(ac, tenant_id="tenant-test", email="deactivate@example.com", password="pass123")

    # Deactivate the user
    async with sf() as session:
        result = await session.execute(select(User).where(User.id == user_info["id"]))
        user = result.scalar_one()
        user.is_active = False
        await session.commit()

    resp = await ac.post(
        "/auth/refresh",
        json={"refresh_token": token},
        headers={"X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 401


# ===========================================================================
# 3. GET /users/me
# ===========================================================================

@pytest.mark.asyncio
async def test_get_me_success(perm_client):
    ac, sf = perm_client
    await _create_user(sf, email="me@example.com", password="mypass")
    token = await _get_token(ac, tenant_id="tenant-test", email="me@example.com", password="mypass")
    resp = await ac.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "me@example.com"
    assert body["role"] == "practitioner"
    assert "hashed_password" not in body


@pytest.mark.asyncio
async def test_get_me_no_auth_returns_401(perm_client):
    ac, _ = perm_client
    resp = await ac.get("/users/me", headers={"X-Tenant-ID": "tenant-test"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_expired_token_returns_401(perm_client):
    ac, _ = perm_client
    from app.core.security import create_user_token
    token = create_user_token("user-1", "tenant-test", "practitioner", ttl_min=-1)
    resp = await ac.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_inactive_user_blocked_with_valid_jwt(perm_client):
    """Even with a valid JWT, inactive users must be rejected (every request)."""
    ac, sf = perm_client
    from app.models.user import User
    from sqlalchemy import select

    user_info = await _create_user(sf, email="willdeact@example.com", password="pass123")
    token = await _get_token(ac, tenant_id="tenant-test", email="willdeact@example.com", password="pass123")

    # Deactivate after token issuance
    async with sf() as session:
        result = await session.execute(select(User).where(User.id == user_info["id"]))
        user = result.scalar_one()
        user.is_active = False
        await session.commit()

    resp = await ac.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 401


# ===========================================================================
# 4. GET /users — admin only
# ===========================================================================

@pytest.mark.asyncio
async def test_list_users_admin_success(perm_client):
    ac, sf = perm_client
    await _create_user(sf, email="admin@example.com", password="adminpass", role="admin")
    token = await _get_token(ac, tenant_id="tenant-test", email="admin@example.com", password="adminpass")
    resp = await ac.get(
        "/users",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_list_users_non_admin_returns_403(perm_client):
    ac, sf = perm_client
    await _create_user(sf, email="pract@example.com", password="pass", role="practitioner")
    token = await _get_token(ac, tenant_id="tenant-test", email="pract@example.com", password="pass")
    resp = await ac.get(
        "/users",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 403


# ===========================================================================
# 5. POST /users — admin creates user
# ===========================================================================

@pytest.mark.asyncio
async def test_admin_creates_user(perm_client):
    ac, sf = perm_client
    await _create_user(sf, email="admin2@example.com", password="adminpass", role="admin")
    token = await _get_token(ac, tenant_id="tenant-test", email="admin2@example.com", password="adminpass")
    resp = await ac.post(
        "/users",
        json={"email": "newuser@example.com", "password": "newpass123", "role": "practitioner"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "newuser@example.com"
    assert "hashed_password" not in body


@pytest.mark.asyncio
async def test_create_user_non_admin_returns_403(perm_client):
    ac, sf = perm_client
    await _create_user(sf, email="nonadmin@example.com", password="pass", role="practitioner")
    token = await _get_token(ac, tenant_id="tenant-test", email="nonadmin@example.com", password="pass")
    resp = await ac.post(
        "/users",
        json={"email": "another@example.com", "password": "pass", "role": "practitioner"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_user_duplicate_email_returns_409(perm_client):
    ac, sf = perm_client
    await _create_user(sf, email="admin3@example.com", password="adminpass", role="admin")
    await _create_user(sf, email="dup@example.com", password="pass")
    token = await _get_token(ac, tenant_id="tenant-test", email="admin3@example.com", password="adminpass")
    resp = await ac.post(
        "/users",
        json={"email": "dup@example.com", "password": "pass2", "role": "practitioner"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 409


# ===========================================================================
# 6. PUT /users/{user_id}/role — admin changes role + audit log
# ===========================================================================

@pytest.mark.asyncio
async def test_admin_changes_role(perm_client):
    ac, sf = perm_client
    from app.models.user import RoleAuditLog
    from sqlalchemy import select

    await _create_user(sf, email="admin4@example.com", password="adminpass", role="admin")
    target = await _create_user(sf, email="target@example.com", password="pass")
    token = await _get_token(ac, tenant_id="tenant-test", email="admin4@example.com", password="adminpass")

    resp = await ac.put(
        f"/users/{target['id']}/role",
        json={"role": "quality_manager"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "quality_manager"

    # Verify audit log was written
    async with sf() as session:
        result = await session.execute(
            select(RoleAuditLog).where(RoleAuditLog.target_user_id == target["id"])
        )
        log = result.scalar_one_or_none()
    assert log is not None
    assert log.old_role == "practitioner"
    assert log.new_role == "quality_manager"


@pytest.mark.asyncio
async def test_change_role_not_found_returns_404(perm_client):
    ac, sf = perm_client
    await _create_user(sf, email="admin5@example.com", password="adminpass", role="admin")
    token = await _get_token(ac, tenant_id="tenant-test", email="admin5@example.com", password="adminpass")
    resp = await ac.put(
        "/users/nonexistent-id/role",
        json={"role": "quality_manager"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 404


# ===========================================================================
# 7. POST /review-items — practitioner submits
# ===========================================================================

@pytest.mark.asyncio
async def test_create_review_item(perm_client):
    ac, sf = perm_client
    await _create_user(sf, email="submitter@example.com", password="pass")
    token = await _get_token(ac, tenant_id="tenant-test", email="submitter@example.com", password="pass")
    resp = await ac.post(
        "/review-items",
        json={"title": "Test Item", "description": "Needs review"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Test Item"
    assert body["status"] == "pending"


# ===========================================================================
# 8. GET /review-items
# ===========================================================================

@pytest.mark.asyncio
async def test_list_review_items(perm_client):
    ac, sf = perm_client
    await _create_user(sf, email="lister@example.com", password="pass")
    token = await _get_token(ac, tenant_id="tenant-test", email="lister@example.com", password="pass")
    resp = await ac.get(
        "/review-items",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ===========================================================================
# 9. PUT /review-items/{id}/assign — quality_manager assigns
# ===========================================================================

@pytest.mark.asyncio
async def test_assign_review_item(perm_client):
    ac, sf = perm_client
    qm = await _create_user(sf, email="qm@example.com", password="pass", role="quality_manager")
    _ = await _create_user(sf, email="sub2@example.com", password="pass")

    # Create review item
    sub_token = await _get_token(ac, tenant_id="tenant-test", email="sub2@example.com", password="pass")
    item_resp = await ac.post(
        "/review-items",
        json={"title": "To Assign"},
        headers={"Authorization": f"Bearer {sub_token}", "X-Tenant-ID": "tenant-test"},
    )
    item_id = item_resp.json()["id"]

    # Assign
    qm_token = await _get_token(ac, tenant_id="tenant-test", email="qm@example.com", password="pass")
    resp = await ac.put(
        f"/review-items/{item_id}/assign",
        json={"assigned_to": qm["id"]},
        headers={"Authorization": f"Bearer {qm_token}", "X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 200
    assert resp.json()["assigned_to"] == qm["id"]


@pytest.mark.asyncio
async def test_assign_requires_qm_or_admin(perm_client):
    ac, sf = perm_client
    pract = await _create_user(sf, email="pract2@example.com", password="pass")

    # Create item first
    token = await _get_token(ac, tenant_id="tenant-test", email="pract2@example.com", password="pass")
    item_resp = await ac.post(
        "/review-items",
        json={"title": "NoAssign"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-test"},
    )
    item_id = item_resp.json()["id"]

    # Practitioner tries to assign — should fail
    resp = await ac.put(
        f"/review-items/{item_id}/assign",
        json={"assigned_to": pract["id"]},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 403


# ===========================================================================
# 10. POST /review-items/{id}/decide — approved, conflict-of-interest guard
# ===========================================================================

@pytest.mark.asyncio
async def test_decide_review_item_approved(perm_client):
    ac, sf = perm_client
    _ = await _create_user(sf, email="qm2@example.com", password="pass", role="quality_manager")
    _ = await _create_user(sf, email="sub3@example.com", password="pass")

    sub_token = await _get_token(ac, tenant_id="tenant-test", email="sub3@example.com", password="pass")
    item_resp = await ac.post(
        "/review-items",
        json={"title": "Decide Me"},
        headers={"Authorization": f"Bearer {sub_token}", "X-Tenant-ID": "tenant-test"},
    )
    item_id = item_resp.json()["id"]

    qm_token = await _get_token(ac, tenant_id="tenant-test", email="qm2@example.com", password="pass")
    resp = await ac.post(
        f"/review-items/{item_id}/decide",
        json={"decision": "approved", "rationale": "Looks good"},
        headers={"Authorization": f"Bearer {qm_token}", "X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["decision"] == "approved"


@pytest.mark.asyncio
async def test_decide_conflict_of_interest_rejected(perm_client):
    """Admin who submitted an item cannot approve their own item."""
    ac, sf = perm_client
    _ = await _create_user(sf, email="self_admin@example.com", password="pass", role="admin")

    admin_token = await _get_token(ac, tenant_id="tenant-test", email="self_admin@example.com", password="pass")

    # Submit item as admin
    item_resp = await ac.post(
        "/review-items",
        json={"title": "Self Submit"},
        headers={"Authorization": f"Bearer {admin_token}", "X-Tenant-ID": "tenant-test"},
    )
    item_id = item_resp.json()["id"]

    # Try to approve own submission
    resp = await ac.post(
        f"/review-items/{item_id}/decide",
        json={"decision": "approved", "rationale": "I trust myself"},
        headers={"Authorization": f"Bearer {admin_token}", "X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_decide_rejected_decision_no_conflict_check(perm_client):
    """Rejected decision has no conflict of interest rule."""
    ac, sf = perm_client
    _ = await _create_user(sf, email="self_admin2@example.com", password="pass", role="admin")
    admin_token = await _get_token(ac, tenant_id="tenant-test", email="self_admin2@example.com", password="pass")

    item_resp = await ac.post(
        "/review-items",
        json={"title": "Self Submit 2"},
        headers={"Authorization": f"Bearer {admin_token}", "X-Tenant-ID": "tenant-test"},
    )
    item_id = item_resp.json()["id"]

    # Rejected is allowed even for submitter
    resp = await ac.post(
        f"/review-items/{item_id}/decide",
        json={"decision": "rejected", "rationale": "Not ready"},
        headers={"Authorization": f"Bearer {admin_token}", "X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_decide_practitioner_returns_403(perm_client):
    ac, sf = perm_client
    _ = await _create_user(sf, email="pract3@example.com", password="pass")
    token = await _get_token(ac, tenant_id="tenant-test", email="pract3@example.com", password="pass")

    # Create item with same user (practitioner)
    item_resp = await ac.post(
        "/review-items",
        json={"title": "Cannot Decide"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-test"},
    )
    item_id = item_resp.json()["id"]

    resp = await ac.post(
        f"/review-items/{item_id}/decide",
        json={"decision": "approved", "rationale": "I wish"},
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 403


# ===========================================================================
# 11. GET /audit/decisions
# ===========================================================================

@pytest.mark.asyncio
async def test_audit_decisions_admin_only(perm_client):
    ac, sf = perm_client
    await _create_user(sf, email="auditadmin@example.com", password="pass", role="admin")
    token = await _get_token(ac, tenant_id="tenant-test", email="auditadmin@example.com", password="pass")
    resp = await ac.get(
        "/audit/decisions",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_audit_decisions_practitioner_returns_403(perm_client):
    ac, sf = perm_client
    await _create_user(sf, email="auditpract@example.com", password="pass", role="practitioner")
    token = await _get_token(ac, tenant_id="tenant-test", email="auditpract@example.com", password="pass")
    resp = await ac.get(
        "/audit/decisions",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-test"},
    )
    assert resp.status_code == 403


# ===========================================================================
# 12. Security helpers: bcrypt password hashing
# ===========================================================================

def test_hash_password_is_not_plaintext():
    from app.core.security import hash_password
    hashed = hash_password("my_secret")
    assert hashed != "my_secret"
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")


def test_verify_password_correct():
    from app.core.security import hash_password, verify_password
    hashed = hash_password("correct_password")
    assert verify_password("correct_password", hashed) is True


def test_verify_password_wrong():
    from app.core.security import hash_password, verify_password
    hashed = hash_password("correct_password")
    assert verify_password("wrong_password", hashed) is False


def test_create_user_token_includes_role():
    from app.core.security import create_user_token, decode_token
    token = create_user_token("user-1", "tenant-abc", "admin")
    payload = decode_token(token)
    assert payload["sub"] == "user-1"
    assert payload["tenant_id"] == "tenant-abc"
    assert payload["role"] == "admin"


def test_existing_create_token_still_works():
    """Ensure the original create_token signature is unchanged (HARD constraint)."""
    from app.core.security import create_token, decode_token
    token = create_token(user_id="user-x", tenant_id="tenant-y")
    payload = decode_token(token)
    assert payload["sub"] == "user-x"
    assert payload["tenant_id"] == "tenant-y"
