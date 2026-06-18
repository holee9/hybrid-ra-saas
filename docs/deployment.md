# Azure 배포 가이드

> 이 문서는 새 세션에서 작업을 이어받을 때 즉시 참조하는 배포 체크리스트입니다.  
> **목표**: `v1.0.0` 태그 push → Azure 자동 배포 → end-to-end 기능 검증

---

## 1. 배포 아키텍처 요약

```
v* 태그 push
  │
  └── deploy-prod.yml (GitHub Actions)
        ├── 이미지 빌드 → ACR push
        │     ├── customer-runtime  → acrhybridrasaasprod.azurecr.io/api:{VERSION}
        │     └── cloud-control-plane → acrhybridrasaasprod.azurecr.io/cloud-control-plane-api:{VERSION}
        │
        ├── Container App 배포
        │     ├── api-prod (customer-runtime API, port 8000)
        │     ├── cloud-control-plane-api (크롤러 API)
        │     └── crawler-job (cron 02:00 UTC)
        │
        └── 헬스체크 → 실패 시 자동 롤백
```

**Container App 이름 → Azure 리소스 매핑**

| 앱 | 이름 | 생성 방법 |
|----|------|---------|
| customer-runtime API | `api-prod` | `azure/container-apps-deploy-action` 자동 생성 |
| 크롤러 API | `cloud-control-plane-api` | Terraform 정의 (SPEC-INFRA-001) |
| 크롤러 Job | `crawler-job` | Terraform 정의 (SPEC-CRAWLER-001) |

---

## 2. 배포 전 체크리스트

### 2-1. GitHub Secrets 확인

아래 Secrets이 모두 등록되어 있어야 합니다 (`holee9/hybrid-ra-saas` → Settings → Secrets):

| Secret | 값 | 상태 |
|--------|-----|------|
| `AZURE_CLIENT_ID` | `6620dc2b-93af-453c-b1b8-20f9582d7354` | ✅ 등록됨 |
| `AZURE_TENANT_ID` | `42580dce-4bd2-4556-b531-4843eba6431d` | ✅ 등록됨 |
| `AZURE_SUBSCRIPTION_ID` | `a49390df-1886-495c-9fb0-cf8faf1aa5ef` | ✅ 등록됨 |
| `AZURE_CONTAINER_REGISTRY` | `acrhybridrasaasprod.azurecr.io` | ✅ 등록됨 |
| `AZURE_RESOURCE_GROUP` | `rg-hybrid-ra-saas-prod` | ✅ 등록됨 |
| `AZURE_CONTAINER_APP_ENV` | `cae-hybrid-ra-saas-staging` | ✅ 등록됨 |

### 2-2. Terraform 상태 확인

Terraform은 PR 머지 시 `terraform apply`가 실행됩니다 (`terraform.yml`).  
`cloud-control-plane-api`와 `crawler-job`이 Azure에 이미 존재해야 크롤러 배포 단계가 성공합니다.

```bash
# Azure CLI로 리소스 존재 확인
az containerapp show --name cloud-control-plane-api --resource-group rg-hybrid-ra-saas-prod
az containerapp job show --name crawler-job --resource-group rg-hybrid-ra-saas-prod
```

> **만약 리소스가 없다면:** main 머지가 Terraform apply를 트리거했는지 확인.  
> `terraform.yml` 워크플로 실행 이력 확인 → GitHub Actions → terraform workflow.

### 2-3. Container App 환경 변수 설정 ⚠️ 수동 작업 필요

Container App에 DB/Storage 환경 변수가 설정되어 있어야 합니다.  
Key Vault 시크릿은 이미 등록되어 있으므로 Container App에서 KV 참조로 주입합니다.

**customer-runtime (api-prod) 필요 환경 변수:**

```bash
az containerapp update \
  --name api-prod \
  --resource-group rg-hybrid-ra-saas-prod \
  --set-env-vars \
    DATABASE_URL=secretref:db-connection-string \
    JWT_SECRET=secretref:jwt-secret \
    AZURE_STORAGE_CONN_STRING=secretref:azure-storage-conn-string \
    REGULA_API_KEY=secretref:regula-api-key \
    REGULA_ALLOWED_TENANTS=tenant-prod \
    REGULA_AUDIT_WEBHOOK_URL=secretref:regula-audit-webhook-url \
    REGULA_IFU_WEBHOOK_URL=secretref:regula-ifu-webhook-url
```

**cloud-control-plane-api 필요 환경 변수:**

```bash
az containerapp update \
  --name cloud-control-plane-api \
  --resource-group rg-hybrid-ra-saas-prod \
  --set-env-vars \
    DATABASE_URL=secretref:db-connection-string \
    AZURE_STORAGE_CONN_STRING=secretref:azure-storage-conn-string \
    APPLICATIONINSIGHTS_CONNECTION_STRING=secretref:app-insights-conn-string \
    REGULA_KNOWLEDGE_PUSH_URL=secretref:regula-knowledge-push-url \
    CRAWL_PUSH_SECRET=secretref:crawl-push-secret \
    CORS_ORIGINS=https://regula.abyz-lab.work
```

> Key Vault 시크릿 이름: `DB-CONNECTION-STRING`, `JWT-SECRET`, `AZURE-STORAGE-CONN-STRING`, `APP-INSIGHTS-CONN-STRING`, `REGULA-API-KEY`, `REGULA-KNOWLEDGE-PUSH-URL`, `CRAWL-PUSH-SECRET`, `REGULA-AUDIT-WEBHOOK-URL`, `REGULA-IFU-WEBHOOK-URL`

**Regula 연동 배포 후 검증:**

```bash
# Cloud Control Plane CORS/health
curl -i -H "Origin: https://regula.abyz-lab.work" \
  https://cloud-control-plane-api.<region>.azurecontainerapps.io/health

# Customer Runtime server-to-server auth
curl -i -X POST https://api-prod.<region>.azurecontainerapps.io/rag/query \
  -H "Authorization: Bearer <jwt>" \
  -H "X-Tenant-ID: tenant-prod" \
  -H "X-Regula-API-Key: <regula-api-key>" \
  -H "Content-Type: application/json" \
  -d '{"question":"test","top_k":1}'
```

`/rag/query`는 Ollama non-streamed 응답을 기다리기 위해 요청 timeout을 `25s`로 둔다.
retry는 최대 3회이며, backoff를 포함한 전체 Ollama budget은 `28s`로 30초 API SLA 안에 유지한다.
Ollama timeout/5xx가 budget을 소진하면 HTTP 요청 자체는 fallback 응답을 반환하며,
검색된 evidence는 유지되고 `submit_safe=false`가 된다.

---

## 3. DB 마이그레이션 (첫 배포 시 수동 실행)

CI/CD에 마이그레이션이 포함되어 있지 않습니다. 첫 배포 전 수동으로 실행합니다.

### customer-runtime 마이그레이션

```bash
# Azure Container Apps Job으로 실행하거나, 로컬에서 DB 직접 연결
# PostgreSQL: psql-hybrid-ra-saas-prod.postgres.database.azure.com
cd customer-runtime
DATABASE_URL="postgresql+asyncpg://hradmin:{PASSWORD}@psql-hybrid-ra-saas-prod.postgres.database.azure.com/postgres?ssl=require" \
  uv run alembic upgrade head
```

### cloud-control-plane 마이그레이션

```bash
cd cloud-control-plane
DATABASE_URL="postgresql+asyncpg://hradmin:{PASSWORD}@psql-hybrid-ra-saas-prod.postgres.database.azure.com/postgres?ssl=require" \
  uv run alembic upgrade head
```

> DB 비밀번호는 Key Vault `kv-hybrid-ra-prod` → `DB-CONNECTION-STRING` 참조.

---

## 4. 배포 실행

모든 체크리스트 완료 후 태그를 push합니다:

```bash
git checkout main
git pull
git tag v1.0.0
git push origin v1.0.0
```

**GitHub Actions 모니터링:**
- `https://github.com/holee9/hybrid-ra-saas/actions`
- `Deploy — Production` 워크플로우 확인
- 예상 소요 시간: ~5분 (Docker 빌드 포함)

---

## 5. 배포 후 검증

### 헬스체크 URL 확인

```bash
# customer-runtime API URL
az containerapp show \
  --name api-prod \
  --resource-group rg-hybrid-ra-saas-prod \
  --query properties.configuration.ingress.fqdn -o tsv

# cloud-control-plane API URL
az containerapp show \
  --name cloud-control-plane-api \
  --resource-group rg-hybrid-ra-saas-prod \
  --query properties.configuration.ingress.fqdn -o tsv
```

### 기능 검증 체크리스트

```bash
# 1. customer-runtime 헬스체크
curl https://{api-prod-url}/health

# 2. cloud-control-plane 헬스체크
curl https://{crawler-url}/health

# 3. 크롤러 수동 트리거 (소량 수집 테스트)
curl -X POST https://{crawler-url}/crawl/trigger
# → job_id 반환

# 4. 잡 상태 확인
curl https://{crawler-url}/crawl/status/{job_id}

# 5. 교정 UI 접근 (브라우저)
# https://{api-prod-url}/docs — FastAPI Swagger UI
```

### 예상 정상 응답

```json
// GET /health
{"status": "ok"}

// POST /crawl/trigger
{"job_id": "uuid-여기에"}

// GET /crawl/status/{job_id}
{"job_id": "...", "status": "completed", "document_count": N}
```

---

## 6. 알려진 제약 및 주의사항

| 항목 | 내용 |
|------|------|
| **Terraform CI on PR** | Azure OIDC가 `pull_request` subject를 미허용 → PR 시 terraform 체크 항상 실패. 정상 동작. |
| **DB 마이그레이션 미자동화** | 첫 배포 시 수동 실행 필요 (위 §3 참조) |
| **customer-runtime docker-compose** | 로컬 개발 전용. Azure 배포는 CI/CD 사용. |
| **httpx 클라이언트 미종료** | crawl.py 백그라운드 태스크 종료 시 ResourceWarning. Container App Job 프로세스 종료로 OS 정리. 무해. |
| **크롤러 cron** | 매일 02:00 UTC 자동 실행. 수동 트리거는 `POST /crawl/trigger`. |

---

## 7. 다음 단계 (배포 검증 완료 후)

- **Issue #10**: Cloudflare `abyz-lab.work` 도메인 연결 (후보: `ra.abyz-lab.work`)
  - Cloudflare CNAME → Azure Container App Custom Domain
  - SSL: Cloudflare Full(Strict) 모드
- **Issue #9**: Customer Local Runtime Docker compose 패키지 (고객 온프레미스용)

---

*최종 갱신: 2026-06-11 | 대상 버전: v1.0.0*
