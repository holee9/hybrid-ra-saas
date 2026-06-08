---
id: SPEC-API-001
version: 1.0.0
status: completed
created: 2026-06-06
updated: 2026-06-08
author: drake.lee
priority: high
issue_number: 12
---

# SPEC-API-001: Customer Local Runtime — FastAPI + Docker Compose 구현

## HISTORY

- **v1.0.0** (2026-06-06): 최초 작성. Customer Local Runtime의 FastAPI 백엔드 + Docker Compose 패키징 구현 범위 확정. OpenAPI 3.1 7개 엔드포인트, Unified Schema 8개 엔티티, 5개 Docker 서비스, EARS 인수 기준(REQ-API-001~015) 정의.

---

## 0. 범위 및 의존성

### 0.1 SPEC 개요

| 항목 | 내용 |
|------|------|
| SPEC-ID | SPEC-API-001 |
| 제목 | Customer Local Runtime — FastAPI + Docker Compose 구현 |
| 상태 | planned |
| 대상 디렉터리 | `customer-runtime/` (FastAPI 앱, Alembic, 테스트, Docker) |
| 분석 기준 | Product PRD (Global Hybrid AI RA Specialist) FR-201~210, NFR, OpenAPI 3.1 명세 |
| 라이프사이클 | spec-anchored (핵심 API 계약, 구현과 함께 유지) |

### 0.2 이 SPEC이 다루는 것 (In Scope)

- FastAPI 백엔드 애플리케이션 구조 및 7개 OpenAPI 엔드포인트 구현
- SQLAlchemy 2.0 async ORM 기반 8개 핵심 엔티티 데이터 모델 + Alembic 마이그레이션
- JWT(HS256) 인증, `X-Tenant-ID` 멀티테넌시, rate limiting, CORS 미들웨어
- 비동기 문서 파싱 잡 처리(BackgroundTasks 기반)
- Document 상태 전이 머신 구현
- Docker multi-stage 빌드 + docker-compose 5개 서비스 오케스트레이션
- pytest + httpx 기반 테스트 전략(커버리지 80%+)
- Air-Gapped 아웃바운드 검증 로직(FR-210)
- AuditEvent append-only 감사 로그
- 핵심 RAG 쿼리 인터페이스(pgvector 기반 벡터 검색 연동 지점)

### 0.3 이 SPEC이 다루지 않는 것 (Exclusions — What NOT to Build)

[HARD] 아래 항목은 SPEC-API-001 구현 범위에서 명시적으로 제외한다.

| 제외 항목 | 사유 | 담당 SPEC |
|-----------|------|-----------|
| NLP/ML 파서 정밀 튜닝 및 골든셋 구성 | 별도 ML 파이프라인 도메인 | SPEC-PARSER-001 |
| Cloud Control Plane Terraform/IaC 구현 | 클라우드 인프라 도메인 | SPEC-INFRA-001 |
| Knowledge Pack 빌드 파이프라인 | 지식팩 제작 도메인 | SPEC-INFRA-001 |
| 프론트엔드 UI React 컴포넌트 구현 | UI 도메인 분리 | SPEC-UI-001 (미래) |
| 멀티사이트 DR 자동화 | 상용화 후순위 | 미정 |
| LLM 모델 자체 파인튜닝 | Ollama 런타임 위임, 모델 학습 비범위 | 비범위 |
| Secure Sync Layer 양방향 동기화 엔진 | API는 manifest 제공만, 동기화 실행은 별도 | SPEC-SYNC-001 (미래) |

> 본 SPEC은 `/sync/manifest` 엔드포인트가 **delta manifest를 응답하는 부분까지만** 구현한다. 실제 지식팩 다운로드/적용 동기화 엔진은 범위 밖이다.

### 0.4 연관 SPEC

- **SPEC-PARSER-001**: Dynamic Parser의 필드 매핑 알고리즘·confidence 산출 로직 제공 (본 SPEC은 인터페이스 계약만 정의, 호출만 수행)
- **SPEC-INFRA-001**: Cloud Control Plane, Knowledge Pack 빌드
- **SPEC-DOC-001**: 제품 문서/기획 패키지 (상위 컨텍스트)

### 0.5 아키텍처 원칙 (불변 제약)

[HARD] 고객 문서 원문은 Customer Local Runtime에서만 처리한다. 클라우드 아웃바운드 패킷에 원문을 포함해서는 안 된다(FR-210).
[HARD] 인바운드 네트워크는 deny-all. 아웃바운드는 HTTPS(443) Cloud Sync Endpoint만 허용한다.

---

## 1. 기술 스택 확정

| 영역 | 선택 | 버전 | 근거 |
|------|------|------|------|
| 웹 프레임워크 | FastAPI | >=0.111 | OpenAPI 3.1 자동 생성, async 네이티브, Pydantic v2 통합 |
| ASGI 서버 | uvicorn (gunicorn worker) | >=0.30 | 프로덕션 멀티워커 |
| ORM | SQLAlchemy | 2.0 async | asyncpg 드라이버, async best-fit |
| DB 드라이버 | asyncpg | >=0.29 | PostgreSQL async |
| 마이그레이션 | Alembic | >=1.13 | SQLAlchemy 표준 마이그레이션 |
| 검증/직렬화 | Pydantic | v2 | FastAPI 통합, 빠른 검증 |
| DOCX 파싱 | python-docx | >=1.1 | DOCX 텍스트/구조 추출 |
| XLSX 파싱 | openpyxl | >=3.1 | XLSX 셀 추출 |
| 임베딩 | sentence-transformers | >=2.7 | 로컬 임베딩(오프라인), CPU 동작 |
| 벡터 검색 | pgvector | >=0.7 (확장) | PostgreSQL 확장, 별도 서비스 불필요 |
| 객체 저장 | MinIO + boto3 | S3-compatible | docker-compose 포함, 로컬 파일 저장 |
| JWT | PyJWT | >=2.8 | HS256, exp/iat/tenant_id claim |
| 비밀번호/해시 | hashlib (SHA-256) | stdlib | source_file_hash, before/after_hash |
| LLM 런타임 | Ollama (HTTP) | latest | 로컬 LLM, CPU fallback |
| Rate Limit | slowapi 또는 커스텀 미들웨어 | >=0.1.9 | tenant별 토큰버킷 |
| 테스트 | pytest, pytest-asyncio, httpx | latest | async TestClient |
| 통합 테스트 | testcontainers-python | >=4.0 | 실제 PostgreSQL 컨테이너 기동 |
| 패키지 관리 | uv 또는 pip + requirements.txt | — | 재현 가능 빌드 |

---

## 2. 프로젝트 구조

```
customer-runtime/
├── src/
│   └── app/
│       ├── __init__.py
│       ├── main.py                 # FastAPI app factory, 라우터 등록, 미들웨어 mount
│       ├── config.py               # Pydantic Settings (env 로딩)
│       ├── database.py             # async engine, session factory, Base
│       ├── deps.py                 # 공통 의존성 (get_db, get_current_tenant, get_user)
│       │
│       ├── models/                 # SQLAlchemy 모델 (8 엔티티)
│       │   ├── __init__.py
│       │   ├── base.py             # Base, TimestampMixin
│       │   ├── product.py
│       │   ├── document.py         # Document + 상태 enum
│       │   ├── requirement.py
│       │   ├── risk.py             # Hazard/Risk
│       │   ├── control.py
│       │   ├── evidence.py
│       │   ├── finding.py
│       │   └── audit.py            # AuditEvent (append-only)
│       │
│       ├── schemas/                # Pydantic 요청/응답 스키마
│       │   ├── __init__.py
│       │   ├── sync.py
│       │   ├── document.py
│       │   ├── parse.py
│       │   ├── guardrail.py
│       │   ├── rag.py
│       │   ├── audit.py
│       │   └── errors.py           # 표준 오류 응답 모델
│       │
│       ├── routers/                # API 라우터 (7 엔드포인트)
│       │   ├── __init__.py
│       │   ├── health.py           # GET /health
│       │   ├── sync.py             # GET /sync/manifest
│       │   ├── documents.py        # POST /documents/upload
│       │   ├── parse.py            # GET /parse/jobs/{job_id}
│       │   ├── guardrail.py        # POST /guardrail/run
│       │   ├── rag.py              # POST /rag/query
│       │   └── audit.py            # POST /audit/export
│       │
│       ├── services/               # 비즈니스 로직 계층
│       │   ├── __init__.py
│       │   ├── parser.py           # 파싱 잡 오케스트레이션 (SPEC-PARSER-001 인터페이스 호출)
│       │   ├── guardrail.py        # Consistency Guardrail 규칙 엔진
│       │   ├── rag.py              # 벡터 검색 + Ollama 호출 + evidence 링크
│       │   ├── export.py           # DOCX/XLSX/PDF/JSON export
│       │   ├── storage.py          # MinIO 클라이언트 래퍼
│       │   ├── audit.py            # AuditEvent 기록 (append-only)
│       │   └── airgap.py           # FR-210 아웃바운드 검증
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── security.py         # JWT 발급/검증, HS256
│       │   ├── ratelimit.py        # tenant별 rate limit
│       │   └── state_machine.py    # Document 상태 전이 검증
│       │
│       └── jobs/
│           ├── __init__.py
│           └── parse_job.py        # BackgroundTasks 파싱 작업 함수
│
├── alembic/
│   ├── env.py                      # async migration 설정
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial_schema.py  # pgvector 확장 + 8 테이블
├── alembic.ini
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # testcontainers PostgreSQL fixture, async client
│   ├── test_health.py
│   ├── test_auth.py                # JWT, tenant_id 검증
│   ├── test_documents.py           # upload + 상태 전이
│   ├── test_parse.py               # 파싱 잡 상태 조회
│   ├── test_guardrail.py
│   ├── test_rag.py
│   ├── test_audit_export.py
│   ├── test_sync.py
│   ├── test_airgap.py              # FR-210 아웃바운드 검증
│   └── test_ratelimit.py
│
├── docker/
│   ├── Dockerfile                  # multi-stage (builder + runtime)
│   └── entrypoint.sh               # alembic upgrade head && uvicorn 기동
│
├── docker-compose.yml
├── .env.example
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## 3. 데이터베이스 스키마

SQLAlchemy 2.0 async + `Mapped`/`mapped_column` 스타일. 모든 테이블은 `tenant_id`(UUID/str)로 격리. pgvector 확장은 Alembic 초기 마이그레이션에서 `CREATE EXTENSION IF NOT EXISTS vector` 실행.

### 3.1 Base + Mixin

```python
# src/app/models/base.py
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TenantMixin:
    # All tenant-scoped rows MUST carry tenant_id for isolation.
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


def new_id() -> str:
    return str(uuid.uuid4())
```

### 3.2 8개 핵심 엔티티

| 테이블 | 주요 컬럼 | 비고 |
|--------|-----------|------|
| `products` | product_id(PK), tenant_id, product_family, intended_use, region_targets(JSON), device_class_hint | |
| `documents` | doc_id(PK), tenant_id, product_id(FK), doc_type, version, owner, source_file_hash, status(enum), storage_key | source_file_hash = SHA-256 |
| `requirements` | req_id(PK), tenant_id, source, clause_ref, text, product_family, severity, embedding(vector) | pgvector 컬럼 |
| `risks` | risk_id(PK), tenant_id, product_id(FK), hazard, hazardous_situation, harm, risk_level, control_id(FK) | Hazard/Risk |
| `controls` | control_id(PK), tenant_id, control_type, linked_srs, linked_ifu_warning, verification_id(FK) | |
| `evidences` | evidence_id(PK), tenant_id, test_report_ref, result_value, acceptance_criteria, file_ref | |
| `findings` | finding_id(PK), tenant_id, product_id(FK), severity, message, evidence_links(JSON), reviewer_status | guardrail 결과 |
| `audit_events` | event_id(PK), tenant_id, user_id, action, timestamp, before_hash, after_hash | **append-only** |

### 3.3 모델 예시 (Document + 상태 enum)

```python
# src/app/models/document.py
import enum
from sqlalchemy import String, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TenantMixin, TimestampMixin, new_id


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PARSED = "parsed"
    NEEDS_CORRECTION = "needs_correction"   # confidence < 0.85
    READY_FOR_CHECK = "ready_for_check"     # confidence >= 0.85
    FINDING_OPEN = "finding_open"
    RESOLVED = "resolved"
    APPROVED = "approved"
    EXPORTED = "exported"


class Document(Base, TenantMixin, TimestampMixin):
    __tablename__ = "documents"

    doc_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.product_id"), nullable=True)
    doc_type: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="1.0")
    owner: Mapped[str] = mapped_column(String(128), nullable=False)
    source_file_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256
    storage_key: Mapped[str] = mapped_column(String(256), nullable=False)      # MinIO object key
    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(DocumentStatus), default=DocumentStatus.UPLOADED, nullable=False
    )
```

### 3.4 pgvector 컬럼 (Requirement 임베딩)

```python
# src/app/models/requirement.py
from pgvector.sqlalchemy import Vector
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TenantMixin, TimestampMixin, new_id

EMBED_DIM = 384  # all-MiniLM-L6-v2 dimension


class Requirement(Base, TenantMixin, TimestampMixin):
    __tablename__ = "requirements"

    req_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    clause_ref: Mapped[str | None] = mapped_column(String(128))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    product_family: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBED_DIM), nullable=True)
```

### 3.5 Alembic 초기 마이그레이션 핵심

```python
# alembic/versions/0001_initial_schema.py (발췌)
def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # ... create_table for products, documents, requirements, risks,
    #     controls, evidences, findings, audit_events
    # requirements.embedding => sa.Column('embedding', Vector(384))
    op.create_index("ix_documents_tenant_id", "documents", ["tenant_id"])
    # IVFFlat index for vector similarity (after data load, optional)
    op.execute(
        "CREATE INDEX ix_requirements_embedding ON requirements "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )
```

---

## 4. API 라우터 구현 (7 엔드포인트)

공통: 모든 인증 엔드포인트는 `Authorization: Bearer <JWT>` + `X-Tenant-ID` 헤더 필수. `tenant_id` claim과 헤더 불일치 시 403.

### 4.1 `GET /health` (인증 없음)

```python
# src/app/routers/health.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

### 4.2 `GET /sync/manifest` (Bearer)

- 입력: `X-Tenant-ID`(헤더), 쿼리 `current_pack_version`, `product_family`
- 로직: 클라우드와의 동기화 없이 로컬 보유 manifest 메타와 비교하여 delta manifest 산출. `manifest_hash` 계산(SHA-256).
- 응답: `{ "delta": [...], "manifest_hash": "...", "latest_pack_version": "..." }`
- 참고: 실제 지식팩 다운로드는 범위 밖(0.3 참조).

### 4.3 `POST /documents/upload` (Bearer, multipart)

- 입력: `file`(multipart), `doc_type_hint`, `product_id`
- 로직:
  1. 파일 바이트 SHA-256 → `source_file_hash`
  2. MinIO 업로드 → `storage_key`
  3. Document row 생성(status=`uploaded`)
  4. 파싱 잡 enqueue(BackgroundTasks) → `parse_job_id` 발급
  5. AuditEvent 기록(action=`document.upload`)
- 응답: `{ "doc_id": "...", "parse_job_id": "..." }`

```python
# src/app/routers/documents.py (발췌)
@router.post("/documents/upload")
async def upload_document(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    doc_type_hint: str = Form(...),
    product_id: str = Form(...),
    tenant: str = Depends(get_current_tenant),
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    raw = await file.read()
    file_hash = hashlib.sha256(raw).hexdigest()
    storage_key = await storage.put_object(tenant, file.filename, raw)

    doc = Document(
        tenant_id=tenant, product_id=product_id, doc_type=doc_type_hint,
        owner=user, source_file_hash=file_hash, storage_key=storage_key,
        status=DocumentStatus.UPLOADED,
    )
    db.add(doc)
    await db.flush()

    job_id = new_id()
    await audit.record(db, tenant, user, "document.upload", after=doc.doc_id)
    await db.commit()

    background.add_task(run_parse_job, job_id, doc.doc_id, tenant)
    return UploadResponse(doc_id=doc.doc_id, parse_job_id=job_id)
```

### 4.4 `GET /parse/jobs/{job_id}` (Bearer)

- 입력: `job_id`(path)
- 응답: `{ "status": "...", "field_candidates": [...], "confidence": 0.0~1.0, "required_missing": [...] }`
- status: `pending | running | done | failed`
- `confidence < 0.85` → Document status를 `needs_correction`으로 전이
- `confidence >= 0.85` → `ready_for_check`로 전이

### 4.5 `POST /guardrail/run` (Bearer)

- 입력: `product_id`, `doc_set_ids[]`, `rule_set_version`
- 로직: RMS-SRS-IFU-시험증적 간 연결성 규칙 엔진 실행 → Finding 생성
- 응답: `{ "findings": [ { "finding_id", "severity", "message", "evidence_links": [...] } ] }`
- High severity finding 존재 시 관련 Document status `finding_open`으로 전이
- AuditEvent 기록(action=`guardrail.run`)

### 4.6 `POST /rag/query` (Bearer)

- 입력: `question`, `scope`, `evidence_required=true`(default), `product_family`
- 로직:
  1. question 임베딩(sentence-transformers, 로컬)
  2. pgvector cosine 유사도 검색(tenant 격리)
  3. Ollama LLM 호출하여 답변 생성, 근거 청크 첨부
  4. `evidence_links`가 비어 있으면 `submit_safe=false`
- 응답: `{ "answer", "evidence_links": [...], "confidence", "submit_safe" }`
- [HARD] `evidence_required=true`이고 근거가 없으면 답변에 제출용 부적합(`submit_safe=false`) 표시 (FR-206)

### 4.7 `POST /audit/export` (Bearer)

- 입력: `scope`, `product_id`, `date_range`, `format`(XLSX/PDF/JSON)
- 로직: 대상 데이터 + 감사 이벤트 + 변경 이력 수집 → 포맷별 바이너리 생성
- 응답: `StreamingResponse` 바이너리 (Content-Type 포맷별)
- 포함: 작업자/시간/근거/변경내역 (FR-208)
- AuditEvent 기록(action=`audit.export`)

---

## 5. 인증/미들웨어

### 5.1 JWT (HS256)

```python
# src/app/core/security.py
import jwt
from datetime import datetime, timedelta, timezone
from app.config import settings


def create_token(user_id: str, tenant_id: str, ttl_min: int = 60) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "iat": now,
        "exp": now + timedelta(minutes=ttl_min),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    # raises jwt.ExpiredSignatureError / jwt.InvalidTokenError
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
```

### 5.2 의존성: tenant 검증

```python
# src/app/deps.py (발췌)
async def get_current_tenant(
    authorization: str = Header(...),
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token")
    try:
        claims = decode_token(authorization.removeprefix("Bearer "))
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "invalid token")
    if claims["tenant_id"] != x_tenant_id:
        raise HTTPException(403, "tenant mismatch")
    return x_tenant_id
```

### 5.3 Rate Limiting

- tenant별 100 req/min 토큰버킷. 초과 시 429.
- 구현: slowapi `key_func`를 `tenant_id` 기반으로, 또는 인메모리 토큰버킷 미들웨어.

### 5.4 CORS

- 기본 origin은 로컬 UI(`http://localhost:8080`)만 허용. `.env`로 추가 origin 설정 가능.
- credentials 허용, 허용 메서드 GET/POST.

---

## 6. 비동기 파싱 잡

### 6.1 선택: FastAPI BackgroundTasks (MVP)

| 후보 | 장점 | 단점 | 결정 |
|------|------|------|------|
| **BackgroundTasks** | 외부 브로커 불필요, compose 서비스 최소 | 워커 프로세스 종료 시 잡 유실, 무거운 잡 부적합 | **MVP 채택** |
| Celery + Redis | 견고한 큐, 재시도, 분산 | Redis 서비스 추가, 운영 복잡도 증가 | 확장 시 전환 |

근거: MVP는 `docker compose up -d` 1회 기동·서비스 수 최소화가 핵심 NFR(1일 설치). 외부 브로커 도입은 air-gapped 설치 단순성을 해친다. 100페이지 DOCX 3분 목표는 단일 워커 BackgroundTasks로 충족 가능. P2에서 부하 증가 시 Celery로 전환(인터페이스는 `services/parser.py`로 추상화하여 교체 비용 최소화).

### 6.2 잡 상태 저장

- 잡 상태는 인메모리 dict 대신 DB 또는 간단한 `parse_jobs` 테이블/MinIO 메타에 저장(워커 재시작 내성). MVP는 `parse_jobs` 경량 테이블 권장.
- 상태: `pending → running → done | failed`

### 6.3 잡 함수

```python
# src/app/jobs/parse_job.py (구조)
async def run_parse_job(job_id: str, doc_id: str, tenant: str) -> None:
    async with async_session() as db:
        await _set_status(db, job_id, "running")
        try:
            raw = await storage.get_object_for_doc(db, tenant, doc_id)
            # SPEC-PARSER-001 interface: returns candidates + confidence
            result = parser.parse(raw)  # field_candidates, confidence, required_missing
            await _save_result(db, job_id, result)
            new_status = (
                DocumentStatus.READY_FOR_CHECK if result.confidence >= 0.85
                else DocumentStatus.NEEDS_CORRECTION
            )
            await _transition_document(db, tenant, doc_id, new_status)
            await _set_status(db, job_id, "done")
        except Exception as exc:                # noqa: BLE001
            await _set_status(db, job_id, "failed", error=str(exc))
        await db.commit()
```

---

## 7. Docker 패키징

### 7.1 Dockerfile (multi-stage)

```dockerfile
# docker/Dockerfile
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=builder /install /usr/local
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY docker/entrypoint.sh ./entrypoint.sh
RUN chmod +x entrypoint.sh
ENV PYTHONPATH=/app/src
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"
ENTRYPOINT ["./entrypoint.sh"]
```

```bash
# docker/entrypoint.sh
#!/bin/sh
set -e
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${API_WORKERS:-2}"
```

### 7.2 docker-compose.yml

```yaml
services:
  api:
    image: ghcr.io/${ORG}/ra-local-api:latest
    build:
      context: .
      dockerfile: docker/Dockerfile
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
      minio:
        condition: service_started
      ollama:
        condition: service_started
    networks: [internal]

  ui:
    image: ghcr.io/${ORG}/ra-local-ui:latest
    ports:
      - "8080:8080"
    env_file: .env
    depends_on: [api]
    networks: [internal]

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    volumes:
      - db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks: [internal]

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data
    networks: [internal]

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    networks: [internal]

volumes:
  db_data:
  minio_data:
  ollama_data:

networks:
  internal:
    driver: bridge
```

> 네트워크 정책: 인바운드 deny-all + 아웃바운드 443만 허용은 호스트 방화벽/iptables 레벨에서 설정(설치 가이드). compose 네트워크는 내부 서비스 간 통신용 `internal` 브리지로 격리.

### 7.3 .env.example

```dotenv
# --- Org / images ---
ORG=your-org

# --- Database ---
DB_USER=ra_user
DB_PASSWORD=change-me
DB_NAME=ra_local
DATABASE_URL=postgresql+asyncpg://ra_user:change-me@db:5432/ra_local

# --- MinIO ---
MINIO_USER=minioadmin
MINIO_PASSWORD=change-me
MINIO_ENDPOINT=http://minio:9000
MINIO_BUCKET=ra-documents

# --- Ollama ---
OLLAMA_ENDPOINT=http://ollama:11434
OLLAMA_MODEL=llama3.1:8b

# --- Security ---
JWT_SECRET=change-me-32-bytes-min
JWT_TTL_MIN=60
RATE_LIMIT_PER_MIN=100

# --- Sync (outbound only, HTTPS 443) ---
CLOUD_SYNC_ENDPOINT=https://sync.example.com

# --- API ---
API_WORKERS=2
CORS_ORIGINS=http://localhost:8080
```

---

## 8. 테스트 전략

### 8.1 도구 및 목표

- pytest + pytest-asyncio + httpx(`ASGITransport` async client)
- testcontainers-python로 실제 PostgreSQL(pgvector 이미지) 기동 → 통합 테스트
- 커버리지 목표: **80%+** (pytest-cov, fail_under=80)
- [HARD] 통합 테스트는 모킹된 DB가 아닌 실제 PostgreSQL 컨테이너 사용 (마이그레이션·pgvector 동작 검증)

### 8.2 conftest 핵심

```python
# tests/conftest.py (구조)
@pytest.fixture(scope="session")
def pg_container():
    with PostgresContainer("pgvector/pgvector:pg16") as pg:
        yield pg

@pytest_asyncio.fixture
async def client(pg_container):
    # build app with test DATABASE_URL, run alembic upgrade head
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
```

### 8.3 FR별 테스트 목록

| 테스트 파일 | 검증 FR/요구 | 핵심 케이스 |
|-------------|-------------|------------|
| test_health.py | NFR(설치) | 200 `{"status":"ok"}`, 인증 불필요 |
| test_auth.py | NFR(보안) | 토큰 없음→401, 만료→401, tenant 불일치→403, 정상→200 |
| test_documents.py | FR-207 | upload→doc_id/parse_job_id, SHA-256 일치, status=uploaded, MinIO 키 생성 |
| test_parse.py | FR-201 | confidence<0.85→needs_correction, >=0.85→ready_for_check, required_missing 반환 |
| test_guardrail.py | FR-203 | High finding 생성 시 finding_open 전이, evidence_links 포함 |
| test_rag.py | FR-206 | evidence 없으면 submit_safe=false, 있으면 evidence_links 채움, confidence 반환 |
| test_audit_export.py | FR-208 | XLSX/PDF/JSON 바이너리, 작업자/시간/변경내역 포함, export 이벤트 기록 |
| test_sync.py | FR-209 | delta manifest + manifest_hash, 민감 데이터 미포함 |
| test_airgap.py | FR-210 | 아웃바운드 페이로드에 문서 원문 미포함 검증(직렬화 캡처) |
| test_ratelimit.py | NFR(보안) | 100 req/min 초과 시 429 |

---

## 9. 인수 기준 (EARS)

형식: `WHEN [조건] THE SYSTEM SHALL [동작]` (필요 시 `AND IF [예외] THE SYSTEM SHALL [대응]`)

- **REQ-API-001** (FR-207, 인증): WHEN 클라이언트가 유효한 Bearer JWT와 일치하는 `X-Tenant-ID`로 요청 THE SYSTEM SHALL 요청을 인가한다. AND IF JWT가 없거나 만료되면 THE SYSTEM SHALL 401을 반환한다. AND IF JWT의 tenant_id와 `X-Tenant-ID` 헤더가 불일치하면 THE SYSTEM SHALL 403을 반환한다.

- **REQ-API-002** (헬스): WHEN `GET /health`가 호출되면 THE SYSTEM SHALL 인증 없이 200과 `{"status":"ok"}`를 반환한다.

- **REQ-API-003** (FR-207, 업로드): WHEN 인증된 사용자가 `POST /documents/upload`로 파일을 전송 THE SYSTEM SHALL 파일의 SHA-256을 `source_file_hash`로 저장하고 MinIO에 업로드하며 Document(status=uploaded)를 생성하고 `doc_id`와 `parse_job_id`를 반환한다.

- **REQ-API-004** (FR-201, 파싱): WHEN 파싱 잡이 완료되어 confidence가 0.85 미만이면 THE SYSTEM SHALL Document 상태를 `needs_correction`으로 전이하고 보정 대상 필드를 `field_candidates`에 표시한다. AND IF confidence가 0.85 이상이면 THE SYSTEM SHALL 상태를 `ready_for_check`로 전이한다.

- **REQ-API-005** (FR-201, 파싱 성능): WHEN 100페이지 DOCX가 업로드되면 THE SYSTEM SHALL 3분 이내에 파싱 잡을 완료한다.

- **REQ-API-006** (FR-202, 보정 이력): WHEN 작업자가 파싱 결과 필드를 수정 THE SYSTEM SHALL 수정 전후 값과 작업자·시각을 AuditEvent에 기록한다.

- **REQ-API-007** (FR-203, 가드레일): WHEN `POST /guardrail/run`이 호출되면 THE SYSTEM SHALL RMS-SRS-IFU-시험증적 연결성을 검사하여 findings(severity, message, evidence_links)를 반환한다. AND IF High severity finding이 존재하면 THE SYSTEM SHALL 관련 Document 승인 전 해결 또는 예외승인을 요구한다.

- **REQ-API-008** (FR-206, RAG 근거): WHEN `POST /rag/query`가 `evidence_required=true`로 호출되고 근거가 없으면 THE SYSTEM SHALL `submit_safe=false`로 표시하여 제출용 사용을 차단한다. AND IF 근거가 있으면 THE SYSTEM SHALL `evidence_links`와 `confidence`를 포함해 응답한다.

- **REQ-API-009** (NFR, RAG 성능): WHEN RAG 질의가 접수되면 THE SYSTEM SHALL 30초 이내에 1차 응답을 반환한다.

- **REQ-API-010** (FR-208, export): WHEN `POST /audit/export`가 호출되면 THE SYSTEM SHALL 요청 포맷(DOCX/XLSX/PDF/JSON)으로 작업자·시간·근거·변경내역을 포함한 바이너리를 생성한다.

- **REQ-API-011** (감사성): WHEN 수정·승인·export 이벤트가 발생하면 THE SYSTEM SHALL append-only AuditEvent에 before_hash/after_hash와 함께 기록한다. AND IF AuditEvent 수정 시도가 발생하면 THE SYSTEM SHALL 이를 거부한다.

- **REQ-API-012** (FR-209, sync): WHEN `GET /sync/manifest`가 호출되면 THE SYSTEM SHALL delta manifest와 `manifest_hash`를 반환하며 heartbeat/manifest 응답에 고객 문서 원문 등 민감 데이터를 포함하지 않는다.

- **REQ-API-013** (FR-210, air-gapped): WHILE 시스템이 동작하는 동안 THE SYSTEM SHALL 모든 아웃바운드 페이로드에 고객 문서 원문을 포함하지 않는다. AND IF 아웃바운드 직렬화에 원문이 감지되면 THE SYSTEM SHALL 전송을 차단하고 오류를 기록한다.

- **REQ-API-014** (NFR, rate limit): WHEN 단일 tenant의 요청이 분당 100건을 초과하면 THE SYSTEM SHALL 429를 반환한다.

- **REQ-API-015** (NFR, 설치): WHEN 운영자가 `docker compose up -d`를 1회 실행하면 THE SYSTEM SHALL 5개 서비스(api/ui/db/minio/ollama)를 기동하고 Alembic 마이그레이션을 적용하여 `/health`가 200을 반환하는 상태로 진입한다.

---

## 10. 구현 우선순위

### P0 — MVP 기동 (필수, 최우선)

1. 프로젝트 구조 + `pyproject.toml`/`requirements.txt`
2. `config.py`, `database.py`(async engine/session), Base/Mixin
3. SQLAlchemy 8개 모델 + Alembic 초기 마이그레이션(pgvector 확장 포함)
4. JWT 인증 + `get_current_tenant`/`get_current_user` 의존성 (REQ-API-001)
5. `GET /health` (REQ-API-002)
6. `POST /documents/upload` + MinIO storage 서비스 (REQ-API-003)
7. BackgroundTasks 파싱 잡 + `GET /parse/jobs/{job_id}` + 상태 전이 (REQ-API-004)
8. Dockerfile multi-stage + docker-compose 5서비스 + entrypoint(alembic upgrade) (REQ-API-015)
9. test_health, test_auth, test_documents, test_parse

### P1 — 핵심 워크플로

10. `POST /guardrail/run` 규칙 엔진 + Finding 생성 (REQ-API-007)
11. `POST /rag/query` 임베딩 + pgvector 검색 + Ollama + evidence/submit_safe (REQ-API-008/009)
12. `POST /audit/export` 포맷별 export (REQ-API-010)
13. AuditEvent append-only 기록 + 보정 이력 (REQ-API-006/011)
14. Manual Correction 로직(필드 수정 API + 이력)
15. test_guardrail, test_rag, test_audit_export

### P2 — 완성

16. `GET /sync/manifest` delta manifest + 민감 데이터 배제 (REQ-API-012)
17. Air-Gapped 아웃바운드 검증(`services/airgap.py`) (REQ-API-013)
18. Rate limiting 미들웨어 (REQ-API-014)
19. 성능 튜닝(파싱 3분 / RAG 30초 목표 검증)
20. UI 연동 계약 점검(CORS, 응답 스키마)
21. test_sync, test_airgap, test_ratelimit, 커버리지 80% 달성

---

## 11. 보안 고려사항

### 11.1 Air-Gapped Privacy (FR-210)

- [HARD] 클라우드로 향하는 모든 아웃바운드(현재 범위: `/sync/manifest` 메타 및 향후 heartbeat)는 고객 문서 원문·파싱 텍스트·임베딩 원천 텍스트를 포함하지 않는다.
- `services/airgap.py`는 아웃바운드 직렬화 직전 페이로드를 검사하여 문서 원문 패턴(원문 해시 외 본문 텍스트)이 포함되면 차단·로깅한다.
- 테스트(`test_airgap.py`)는 직렬화 페이로드를 캡처하여 원문 미포함을 단언한다.

### 11.2 민감 데이터 로컬 처리

- 문서 원문·파싱 결과·임베딩은 로컬 PostgreSQL/MinIO에만 저장. 외부 LLM API 미사용(Ollama 로컬 런타임).
- 임베딩도 로컬 sentence-transformers로 생성(외부 임베딩 API 금지).

### 11.3 JWT 관리

- HS256 비밀키는 `.env`의 `JWT_SECRET`(최소 32바이트). 저장소 커밋 금지(`.env.example`만 커밋).
- 토큰 TTL 기본 60분(`JWT_TTL_MIN`). claim에 `sub`, `tenant_id`, `iat`, `exp` 포함.
- 모든 보호 엔드포인트는 tenant claim ↔ 헤더 일치 검증(403 firewall).

### 11.4 네트워크 격리

- 인바운드 deny-all, 아웃바운드 HTTPS(443) Cloud Sync Endpoint만 허용(호스트 방화벽).
- TLS 1.3+ (리버스 프록시 또는 호스트 종단). compose 내부 통신은 `internal` 브리지로 격리.

### 11.5 감사·무결성

- AuditEvent는 append-only. UPDATE/DELETE 차단(서비스 계층 + DB 권한).
- 변경 추적은 `before_hash`/`after_hash`(SHA-256)로 무결성 보장.

### 11.6 입력 검증 (OWASP)

- 모든 요청은 Pydantic v2 스키마 검증. 검증 실패 시 422.
- 파일 업로드: 허용 확장자(DOCX/XLSX) 및 크기 제한 검증.
- rate limit 100 req/min/tenant로 남용 방지.

---

## 12. Implementation Notes (2026-06-08)

SPEC 라이프사이클: `spec-anchored` — 실제 구현 내용을 반영하여 업데이트됨.

### 12.1 구현 완료 요약

| 단계 | 커밋 | 주요 내용 |
|------|------|-----------|
| P0 MVP | `4cb77f3` + `88d1170` | FastAPI 앱 팩토리, SQLAlchemy 9모델, Alembic, JWT, health/upload/parse 엔드포인트, 통합 테스트 Docker 스킵 처리 |
| P1 | `62ecb8f` | Guardrail 규칙 엔진, RAG/pgvector, 감사 Export, 필드 보정 AuditEvent |
| P2 | `b6a9fe8` | Sync manifest, Air-Gap 검증(FR-210), slowapi rate limit, Docker multi-stage + docker-compose |

### 12.2 SPEC 대비 실제 구현 차이

| 항목 | SPEC 계획 | 실제 구현 | 분류 |
|------|-----------|-----------|------|
| SQLAlchemy 모델 수 | 8개 엔티티 | 9개 (ParseJob 추가) | scope_expansion |
| 통합 테스트 | 로컬 실행 | CI(GitHub Actions) 전용, 로컬은 자동 스킵 | structural_change |
| Ollama 연동 | 런타임 위임 (Exclusion) | docker-compose 서비스로 포함 (인터페이스만) | unplanned_addition |

### 12.3 최종 지표

| 지표 | 값 |
|------|-----|
| 테스트 | 92 passed, 23 skipped(Docker CI), 0 failed |
| 커버리지 | 82% (목표 80% 초과) |
| ruff errors | 0 |
| 엔드포인트 | 7개 |
| Docker 서비스 | 5개 |
| 배포 대상 | Azure Container Apps |

Version: v1.0.0 | Created: 2026-06-06 | Status: planned | Lifecycle: spec-anchored
