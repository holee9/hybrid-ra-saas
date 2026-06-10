# SPEC-CRAWLER-001: Regulatory Document Crawler — Research & Architecture

**Date:** 2026-06-10  
**Project:** Global Hybrid AI RA Specialist SaaS  
**Codebase Root:** `D:\workspace-github\SaaS_RA_site`

---

## 1. Project Architecture Overview

### 1.1 High-Level Structure

```
SaaS_RA_site/
├── customer-runtime/            # FastAPI microservice (Container App)
│   ├── src/app/
│   │   ├── main.py              # FastAPI app factory, lifespan, routers
│   │   ├── config.py            # Settings via pydantic-settings
│   │   ├── database.py          # SQLAlchemy async engine init
│   │   ├── models/              # ORM models (SQLAlchemy)
│   │   ├── schemas/             # Pydantic request/response models
│   │   ├── routers/             # FastAPI route handlers
│   │   ├── services/            # Business logic
│   │   │   ├── parser_engine/   # 15-field IFU extraction (SPEC-PARSER-001)
│   │   │   ├── storage.py       # boto3 S3/MinIO client
│   │   │   ├── sync.py          # Delta manifest generation
│   │   │   └── parser.py        # Parser service abstraction
│   │   └── core/
│   │       └── ratelimit.py     # slowapi rate limiter
│   ├── docker/Dockerfile        # Multi-stage build
│   └── requirements.txt          # uv export dependencies
├── infra/terraform/
│   ├── environments/prod/
│   │   └── main.tf              # Azure Container App, PostgreSQL, Blob, ACR
│   └── modules/
├── .github/workflows/
│   ├── ci.yml                   # PR lint + pytest
│   └── deploy-prod.yml          # Tag → build → ACR push → deploy
└── .moai/specs/
    ├── SPEC-PARSER-001/         # Field extraction engine (complete)
    └── SPEC-CRAWLER-001/        # NEW: Regulatory doc fetcher
```

---

## 2. Dependency Versions (from requirements.txt)

### Python & Core
- **Python:** `3.13` (Dockerfile: `python:3.13-slim`)
- **FastAPI:** `0.136.3`
- **Pydantic:** `2.x` (via pydantic-settings)
- **SQLAlchemy:** `2.x` (async support)
- **asyncpg:** `0.31.0` (PostgreSQL driver)

### Database & Storage
- **PostgreSQL:** `16` (Terraform: `pg_version = "16"`)
- **SQLAlchemy async:** `create_async_engine()`, `AsyncSession`, `async_sessionmaker`
- **boto3:** `1.43.24` (S3-compatible MinIO/Blob client)

### HTTP & Networking
- **httpx:** Available via FastAPI (AsyncClient used in existing services)
- **requests:** Implicit dependency

### Parsing & NLP
- **python-docx:** Installed (DOCX text extraction)
- **openpyxl:** Installed (XLSX text extraction)
- **spacy:** Installed (NER extraction)
- **transformers:** Installed (NLP models)
- **sentence-transformers:** Installed (semantic similarity)

### Rate Limiting
- **slowapi:** Rate limiter (app.core.ratelimit)

---

## 3. Docker Build Pattern

### Multi-Stage Build

```dockerfile
# Stage 1: builder
FROM python:3.13-slim AS builder
RUN pip install --no-cache-dir uv
COPY pyproject.toml .
# Generate requirements.txt, install system-wide

# Stage 2: runtime
FROM python:3.13-slim AS runtime
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY src/app /app
CMD ["uvicorn", "app.main:create_app()", "--host", "0.0.0.0", "--port", "8000"]
```

**Entry Point:** `uvicorn app.main:create_app()`  
**Port:** `8000`

---

## 4. Database Models (SQLAlchemy)

### 4.1 Base Classes

**File:** `customer-runtime/src/app/models/base.py`

```python
class Base(DeclarativeBase):
    pass

class TenantMixin:
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now(), onupdate=func.now())

def new_id() -> str:
    return str(uuid.uuid4())
```

### 4.2 Document Model

```python
class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    NEEDS_CORRECTION = "needs_correction"
    READY_FOR_CHECK = "ready_for_check"
    APPROVED = "approved"
    REJECTED = "rejected"

class Document(Base, TenantMixin, TimestampMixin):
    __tablename__ = "documents"
    
    doc_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.product_id"))
    doc_type: Mapped[str] = mapped_column(String(100))
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA-256
    storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)  # MinIO path
    status: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED)
    
    product: Mapped["Product"] = relationship(back_populates="documents")
    parse_jobs: Mapped[list["ParseJob"]] = relationship(back_populates="document")
```

### 4.3 ParseJob Model

```python
class ParseJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"

class ParseJob(Base, TenantMixin, TimestampMixin):
    __tablename__ = "parse_jobs"
    
    job_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    doc_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.doc_id"))
    status: Mapped[ParseJobStatus] = mapped_column(Enum(ParseJobStatus), default=ParseJobStatus.PENDING)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    document: Mapped["Document"] = relationship(back_populates="parse_jobs")
```

### 4.4 Database Connection

**File:** `customer-runtime/src/app/database.py`

```python
def create_engine_from_url(database_url: str):
    return create_async_engine(database_url, echo=False, pool_pre_ping=True)

def init_engine(database_url: str) -> None:
    global _engine, _session_factory
    _engine = create_engine_from_url(database_url)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**Environment:** `DATABASE_URL` (e.g., `postgresql+asyncpg://user:pass@host:5432/db`)

---

## 5. Storage Service (MinIO/Blob)

**File:** `customer-runtime/src/app/services/storage.py`

```python
class StorageService:
    def __init__(self, client: Any, bucket: str) -> None:
        self._client = client  # boto3 S3 client
        self._bucket = bucket

    def upload_file(self, tenant: str, key: str, data: bytes) -> str:
        import io
        full_key = f"{tenant}/{key}"
        self._client.upload_fileobj(io.BytesIO(data), self._bucket, full_key)
        return full_key

    def get_file(self, tenant: str, key: str) -> bytes:
        import io
        full_key = f"{tenant}/{key}"
        buf = io.BytesIO()
        self._client.download_fileobj(self._bucket, full_key, buf)
        return buf.getvalue()

def create_storage_service() -> StorageService:
    settings = Settings()
    client = boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_user,
        aws_secret_access_key=settings.minio_password,
    )
    return StorageService(client=client, bucket=settings.minio_bucket)
```

---

## 6. CI/CD Pipeline

### Deploy Workflow (deploy-prod.yml)

**Trigger:** Git tags matching `v*` (e.g., `v1.0.0`)

**Steps:**
1. Extract version from tag
2. Azure OIDC login
3. Docker build & push to ACR
4. Deploy to Azure Container App
5. Health check `/health`
6. Auto-rollback on health check failure

### CI Workflow (ci.yml)

**Trigger:** Pull requests to main/develop

**Steps:**
1. Python 3.13 setup
2. Install uv
3. Ruff lint check
4. Pytest (skip integration tests marked `@pytest.mark.integration`)
5. Coverage report (target: >=85%)

---

## 7. FastAPI Application

### 7.1 App Factory (main.py)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    init_engine(settings.database_url)
    yield

def create_app() -> FastAPI:
    app = FastAPI(title="RA Customer Runtime", version="1.0.0", lifespan=lifespan)
    
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins_list)
    
    # Include all routers
    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(parse_router)
    app.include_router(sync_router)
    
    return app
```

### 7.2 Key Routers

- **health_router:** `GET /health`
- **documents_router:** `POST /documents/upload`, `PATCH /documents/{doc_id}/fields`
- **parse_router:** `GET /parse/jobs`, `GET /parse/jobs/{job_id}`, `PATCH /parse/{job_id}/corrections`
- **sync_router:** `GET /sync/manifest`

---

## 8. Parser Engine (SPEC-PARSER-001)

### 8.1 ParserEngine Class

**File:** `customer-runtime/src/app/services/parser_engine/__init__.py`

```python
class ParserEngine:
    async def parse(self, file_bytes: bytes, doc_type: str) -> ParsedFields:
        """
        3-stage pipeline:
        1. Rule-based regex/keyword extraction
        2. spaCy NER (if confidence < threshold)
        3. LLM fallback via Ollama (if still below threshold)
        
        Returns ParsedFields with 15 fields, overall_confidence, stage info
        """
```

### 8.2 ParsedFields (15-Field Extraction)

```python
IFU_FIELD_NAMES = (
    "device_name",
    "intended_use",
    "indications",
    "contraindications",
    "warnings",
    "device_classification",
    "region_targets",
    "cybersecurity_requirements",
    "precautions",
    "product_code",
    "maintenance_interval",
    "cleaning_disinfection",
    "software_version",
    "accessories",
    "disposal_instructions",
)

class FieldExtraction(BaseModel):
    value: str | list[str] | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    stage: ExtractionStage  # RULE | NER | LLM | NONE
    needs_correction: bool = False

class ParsedFields(BaseModel):
    # 15 field extractions
    device_name: FieldExtraction
    intended_use: FieldExtraction
    # ... (13 more fields)
    overall_confidence: float = Field(ge=0.0, le=1.0)
    requires_correction: bool = False
    rejected: bool = False
```

---

## 9. HTTP Client Pattern

### Existing httpx Usage

**File:** `customer-runtime/src/app/services/parser_engine/llm_fallback.py`

```python
import httpx

async def extract(
    text: str,
    fields: list[str],
    llm_client: httpx.AsyncClient | None = None,
    base_url: str = "http://localhost:11434",
) -> dict[str, FieldExtraction]:
    client = llm_client if llm_client is not None else httpx.AsyncClient()
    try:
        response = await client.post(
            f"{base_url}/api/generate",
            json={"model": "llama3", "prompt": "..."},
            timeout=30,
        )
        result = response.json()
    except (httpx.HTTPError, json.JSONDecodeError, KeyError) as exc:
        logger.warning("LLM fallback failed: %s", exc)
        return {}
```

### Recommended for Crawler

- Use `httpx.AsyncClient` with timeout (30-60s)
- Implement exponential backoff retry logic
- Set User-Agent header
- Respect Retry-After headers for 429 responses
- Reuse session across requests (connection pooling)

---

## 10. Configuration

**File:** `customer-runtime/src/app/config.py`

```python
class Settings(BaseSettings):
    # Database
    database_url: str
    
    # MinIO
    minio_endpoint: str
    minio_bucket: str
    minio_user: str
    minio_password: str
    
    # Ollama
    ollama_endpoint: str
    ollama_model: str
    
    # Rate limiting
    rate_limit_per_min: int = 100
```

### New Settings for Crawler

```
CRAWLER_FDA_ENABLED=true
CRAWLER_MFDS_ENABLED=true
CRAWLER_EU_MDR_ENABLED=true
CRAWLER_TIMEOUT_SEC=60
CRAWLER_RETRY_MAX=3
CRAWLER_RATE_LIMIT_PER_SEC=2
```

---

## 11. Integration Workflow

### Crawler → Document → Parser → Cloud Sync

```
1. Crawler Service (NEW)
   └─ Fetch + classify regulatory docs
      └─ Upload to MinIO → storage_key

2. Document Model (EXISTING)
   └─ Create record with doc_type, storage_key, status=UPLOADED

3. ParseJob (EXISTING)
   └─ Create job with doc_id, status=PENDING

4. ParserEngine (EXISTING)
   └─ Extract 15 fields via 3-stage pipeline

5. Document Status
   ├─ High confidence: READY_FOR_CHECK
   └─ Low confidence: NEEDS_CORRECTION

6. Cloud Sync (EXISTING)
   └─ Metadata only (no document content per FR-210)
```

---

## 12. Constraints & Risks

### Rate Limiting per Source
- **FDA:** ~3-5 requests/sec (crawl-delay)
- **MFDS:** ~2 requests/sec
- **EU MDR:** ~1-2 requests/sec

**Mitigation:** Exponential backoff, respect Retry-After headers

### robots.txt Compliance
- Read robots.txt before crawling
- Set User-Agent header
- Log violations in AuditEvent

### Document Format Diversity
- PDF: Scanned (OCR) vs. digital (pdfplumber)
- DOCX/XLSX: Supported (python-docx, openpyxl)
- HTML: BeautifulSoup or text extraction

### Data Privacy (FR-210)
- Raw bytes → encrypted Blob only
- PostgreSQL → metadata only (no content)
- SyncService validated by AirGapService

---

## 13. Test Patterns

- **Framework:** pytest
- **Markers:** `@pytest.mark.integration` for external service tests
- **Coverage:** Target >=85%
- **Mock:** Use pytest fixtures for database, storage, httpx
- **CI:** Skip integration tests; run unit tests only

---

## 14. Reference File Paths

| Component | Path |
|-----------|------|
| App Factory | `customer-runtime/src/app/main.py` |
| Config | `customer-runtime/src/app/config.py` |
| Database | `customer-runtime/src/app/database.py` |
| Models Base | `customer-runtime/src/app/models/base.py` |
| Document Model | `customer-runtime/src/app/models/document.py` |
| ParseJob Model | `customer-runtime/src/app/models/parse_job.py` |
| StorageService | `customer-runtime/src/app/services/storage.py` |
| SyncService | `customer-runtime/src/app/services/sync.py` |
| ParserEngine | `customer-runtime/src/app/services/parser_engine/__init__.py` |
| Parse Schemas | `customer-runtime/src/app/schemas/parse.py` |
| Documents Router | `customer-runtime/src/app/routers/documents.py` |
| Parse Router | `customer-runtime/src/app/routers/parse.py` |
| Sync Router | `customer-runtime/src/app/routers/sync.py` |
| Dockerfile | `customer-runtime/docker/Dockerfile` |
| Terraform | `infra/terraform/environments/prod/main.tf` |
| CI Workflow | `.github/workflows/ci.yml` |
| Deploy Workflow | `.github/workflows/deploy-prod.yml` |

---

## Conclusion

SPEC-CRAWLER-001 extends the existing codebase by:
1. Adding CrawlerService for regulatory document fetching
2. Reusing Document/ParseJob models for metadata storage
3. Leveraging ParserEngine for 15-field extraction
4. Integrating with StorageService for encrypted Blob storage
5. Following tenant isolation & FR-210 compliance patterns
6. Extending CI/CD for crawler-specific tests