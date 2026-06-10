# SPEC-CRAWLER-001 — 인수 기준 (acceptance.md)

Given/When/Then 형식. 각 AC는 spec.md의 REQ와 대응한다. 통합 테스트는 `@pytest.mark.integration`(CI 제외), 유닛은 모킹(Docker 비의존).

---

## AC-001 — 스케줄 잡이 신규 FDA 문서를 Blob에 저장 (REQ-CRAWLER-001, -002, -004)

- **Given** `crawler-job`이 FDA 소스 활성화 상태로 구성되어 있고, 신규 규제 문서 URL이 FDA에 존재한다
- **When** cron 스케줄(02:00 UTC)이 발화하여 크롤 잡이 실행된다
- **Then** 해당 문서 원문 바이트가 `regulatory-docs/fda/{YYYY-MM-DD}/{filename}` 경로로 Blob에 저장된다
- **And** `regulatory_documents` 테이블에 source=`fda`, blob_path, content_hash, source_url, fetched_at를 포함한 메타데이터 1행이 INSERT된다
- **And** PostgreSQL에는 원문 바이트가 저장되지 않는다

## AC-002 — 중복 문서 감지 및 skip (REQ-CRAWLER-003, -003b)

- **Given** content_hash `H`를 가진 문서가 이미 `regulatory_documents`에 존재한다
- **When** 크롤러가 동일 콘텐츠(SHA-256 = `H`)의 문서를 다시 fetch한다
- **Then** Blob 업로드와 메타데이터 INSERT가 모두 skip된다
- **And** `regulatory_documents`의 해당 content_hash 행 수는 1개로 유지된다(중복 미생성)

## AC-003 — Rate limiting이 source당 1 req/sec 초과 방지 (REQ-CRAWLER-009)

- **Given** FDA 소스에 대해 N개(N>=3)의 문서 URL이 발견되었다
- **When** 크롤러가 해당 URL들을 순차 fetch한다
- **Then** 동일 소스에 대한 연속 요청 간 간격이 최소 1초 이상으로 유지된다(초당 1건 초과 금지)
- **And** 서로 다른 소스(FDA/MFDS)의 rate limit은 독립적으로 적용된다

## AC-004 — 네트워크 오류 시 재시도 동작 (REQ-CRAWLER-005, -006)

- **Given** 특정 문서 URL이 일시적 네트워크 오류(또는 5xx)를 반환한다
- **When** 크롤러가 해당 URL을 fetch한다
- **Then** 지수 백오프로 최대 3회 재시도한다
- **And** 3회 모두 실패하면 실패를 로그에 기록하고 다음 문서로 진행한다(잡 전체는 중단되지 않는다)

## AC-005 — 수동 트리거 API가 job_id와 status 반환 (REQ-CRAWLER-010, -011, -012)

- **Given** Container App API(`cloud-control-plane-api`)가 실행 중이다
- **When** 클라이언트가 `POST /crawl/trigger`를 호출한다
- **Then** 비동기 크롤 잡이 시작되고 응답으로 `job_id`가 반환된다
- **And** `GET /crawl/status/{job_id}` 호출 시 해당 잡의 현재 상태가 반환된다
- **And** 잡 생명주기 이벤트가 구조화 JSON 로그(timestamp, level, source, event, job_id)로 Application Insights에 전송된다

## AC-006 — robots.txt disallow 준수 (REQ-CRAWLER-007, -008)

- **Given** 소스의 robots.txt가 특정 경로 `/private/*`를 disallow로 지정한다
- **When** 크롤러가 해당 소스를 크롤링한다
- **Then** disallow된 경로의 URL은 fetch되지 않고 skip된다
- **And** robots.txt는 크롤 잡 실행 시점에 재조회된다

## AC-007 — Docker 빌드 및 CI/CD 배포 (REQ-CRAWLER-014, -015)

- **Given** `cloud-control-plane/docker/Dockerfile`이 multi-stage(Python 3.13 + uv)로 작성되어 있다
- **When** `v*` 패턴의 릴리스 태그가 push되어 `deploy-prod.yml`이 실행된다
- **Then** 크롤러 이미지가 빌드되어 ACR에 push된다
- **And** `cloud-control-plane-api` Container App과 `crawler-job`에 해당 이미지가 배포된다
- **And** 배포 후 `/health`가 정상 응답한다

## AC-008: Terraform Container App Job 정의 검증

**대상 REQ:** REQ-CRAWLER-013

Given `infra/terraform/environments/prod/main.tf`를 `terraform validate && terraform plan`으로 검증할 때,
When `crawler-job` Azure Container App Job 리소스가 정의되어 있으면,
Then plan 출력에 `azurerm_container_app_job.crawler_job` 리소스가 포함되어야 하고 변경(drift)이 0이어야 한다.

---

## 엣지 케이스

- 동일 잡 실행 중 동일 소스에서 동일 content_hash가 두 번 나타나면 첫 건만 저장, 두 번째는 skip(잡 내 dedup).
- robots.txt 조회 실패(404 등) 시 보수적으로 전체 disallow가 아닌, 표준 관행에 따라 크롤 허용하되 로그 기록.
- Blob 업로드 성공 후 DB INSERT 실패 시 — content_hash UNIQUE 위반은 정상 skip, 그 외 오류는 로그+continue(고아 Blob은 다음 잡에서 dedup으로 무해).
- 모든 소스 비활성화 시 잡은 즉시 정상 종료(no-op, 로그 기록).

## Quality Gate / Definition of Done

- [ ] REQ-CRAWLER-001~015 (003b 포함) 전부 대응 AC(AC-001~008) 통과
- [ ] 유닛 테스트 커버리지 >=85% (dedup, ratelimit, retry, robots.txt)
- [ ] 통합 테스트(`@pytest.mark.integration`)는 CI 제외, 로컬/CI 전용 잡에서 통과
- [ ] ruff lint 0 경고
- [ ] PostgreSQL에 원문/PII 미기록 검증(FR-210)
- [ ] `customer-runtime` 스키마 무변경 검증
- [ ] Terraform `plan` drift 0(placeholder 교체 + crawler-job 추가만)
