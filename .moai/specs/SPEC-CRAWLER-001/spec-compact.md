# SPEC-CRAWLER-001 — Compact (요구사항 + 인수기준)

> Cloud Control Plane 규제 문서 크롤러. 요구사항과 인수 기준만 포함(아키텍처 서술 제외). 상세는 spec.md 참조.

## EARS 요구사항

### M1 — 수집 및 저장
- **REQ-CRAWLER-001**: When cron(02:00 UTC daily) fires, the crawler shall fetch new documents from each enabled source (FDA, MFDS, EU MDR) and store raw bytes to Blob.
- **REQ-CRAWLER-002**: The crawler shall store documents at `regulatory-docs/{source}/{YYYY-MM-DD}/{filename}` (source ∈ {fda, mfds, eu-mdr}).

### M2 — 데이터 무결성
- **REQ-CRAWLER-003**: When the crawler fetches a document, it shall compute the SHA-256 hash of the document's raw byte content.
- **REQ-CRAWLER-003b**: If the computed SHA-256 hash matches an existing `regulatory_documents.content_hash` record, then the crawler shall skip Blob upload and DB row insertion for that document.
- **REQ-CRAWLER-004**: When a non-duplicate document is stored to Blob, the crawler shall insert a metadata row (source, blob_path, content_hash, fetched_at, source_url) into `regulatory_documents`, and shall NOT write raw content to PostgreSQL.

### M3 — 안정성 및 준수
- **REQ-CRAWLER-005**: If a network error or non-2xx HTTP response occurs while fetching, then the crawler shall retry up to 3 times with exponential backoff (initial delay 2s, multiplier 2).
- **REQ-CRAWLER-006**: If all retry attempts are exhausted, then the crawler shall log the failure and continue with the next document without aborting the job.
- **REQ-CRAWLER-007**: The crawler shall read each source's robots.txt before crawling any URL from that source.
- **REQ-CRAWLER-008**: The crawler shall NOT fetch any URL disallowed by that source's robots.txt.
- **REQ-CRAWLER-009**: While crawling a source, the crawler shall not exceed 1 request per second.

### M4 — 관측성 및 API
- **REQ-CRAWLER-010**: The crawler shall emit structured JSON logs (timestamp, level, source, event, document_count, job_id) to Application Insights for every job lifecycle event.
- **REQ-CRAWLER-011**: When `POST /crawl/trigger` is received, the API shall start an async job and return a `job_id`.
- **REQ-CRAWLER-012**: When `GET /crawl/status/{job_id}` is received, the API shall return the current status of that job.

### M5 — 배포 및 CI
- **REQ-CRAWLER-013**: The system shall support scheduled daily execution of the crawler via a dedicated infrastructure job resource. (구현 제안: Container App Job `crawler-job`, cron `0 2 * * *` — spec.md §1.0)
- **REQ-CRAWLER-014**: The crawler shall be packaged as a container image deployable to Azure Container Apps. (구현 제안: Python 3.13 + uv multi-stage Dockerfile — spec.md §1.0)
- **REQ-CRAWLER-015**: When a `v*` tag is pushed, `deploy-prod.yml` shall build+push the crawler image to ACR and deploy to `cloud-control-plane-api` and `crawler-job`.

## 인수 기준 (Given/When/Then 요약)

| AC | 요지 | REQ |
|----|------|-----|
| AC-001 | 스케줄 잡이 신규 FDA 문서를 `regulatory-docs/fda/{date}/` Blob에 저장 + 메타데이터 INSERT(원문 미기록) | 001, 002, 004 |
| AC-002 | 동일 SHA-256 중복 문서는 Blob/DB 모두 skip, 행 수 1 유지 | 003, 003b |
| AC-003 | source당 연속 요청 간격 >=1초, 소스별 독립 적용 | 009 |
| AC-004 | 네트워크 오류 시 지수 백오프 3회 재시도, 실패 시 로그+continue | 005, 006 |
| AC-005 | `POST /crawl/trigger`가 job_id 반환, `GET /crawl/status/{id}` 상태 반환, JSON 로그 전송 | 010, 011, 012 |
| AC-006 | robots.txt disallow 경로 skip, 잡 실행 시 재조회 | 007, 008 |
| AC-007 | multi-stage Docker 빌드, `v*` 태그 시 ACR push + Container App/Job 배포, `/health` 정상 | 014, 015 |
| AC-008 | Terraform `plan`에 `azurerm_container_app_job.crawler_job` 포함, drift 0 | 013 |

## 핵심 제외 (Exclusions)

1. 15필드 파싱/추출 (SPEC-PARSER-001)
2. customer-runtime 스키마 수정 (regulatory_documents 신규 테이블만)
3. 인프라 프로비저닝 (SPEC-INFRA-001, 본 SPEC은 이미지 교체 + Job 추가만)
4. OCR / 포맷 변환

## Definition of Done

- REQ-001~015 전부 AC 통과 · 유닛 커버리지 >=85% · ruff 0 경고 · FR-210(원문/PII 미기록) 검증 · customer-runtime 스키마 무변경 · Terraform plan drift 0
