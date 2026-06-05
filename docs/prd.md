# 제품 요구사항 명세서 (PRD) — Global Hybrid AI RA Specialist

> **버전:** v3.0 | **기준일:** 2026-06-02 | **완성도:** 85~88%  
> **분류:** Confidential / Development Version  
> **목적:** 사업화 검토와 MVP/상용화 개발을 동시에 지원하기 위한 실구축 중심 명세

---

## 1. 제품 목표와 설계 원칙

| 원칙 | 내용 |
|------|------|
| **공개 지식 연결** | 공개 규제 지식과 고객 내부 문서를 연결하여 표준 문서 생성, 정합성 검토, 변경 영향도 분석을 지원 |
| **데이터 경계** | 민감 데이터는 로컬에서 처리하고, 클라우드는 공개 지식 수집·정규화·버전 관리·변경 알림 역할에 집중 |
| **책임 AI** | AI 출력은 근거 링크와 confidence를 포함해야 하며, 승인 없는 자동 제출/자동 확정 판단은 금지 |
| **품목 집중** | 초기 구현은 X-ray/디텍터/촬영실 SW/피부미용 초음파에 특화하고, 품목군 확장은 지식팩/스키마 단위로 수행 |

---

## 2. 전체 시스템 아키텍처

| 영역 | 구성요소 | 책임 | 데이터 유형 |
|------|---------|------|-----------|
| **Cloud Control Plane** | Regulatory Crawler, Normalizer, PostgreSQL/pgvector, S3 Archive, EventBridge/SQS/SNS, CloudWatch/Budgets | 공개 규제 지식 수집·분류·버전관리·변경 알림 | 공개 원문, 청크, 임베딩, 제품군 태그, 변경 메타데이터 |
| **Secure Sync Layer** | Signed Knowledge Pack, Delta Manifest, Outbound HTTPS Pull, Tenant Isolation | 고객별 지식팩과 변경 이벤트를 안전하게 전달 | 증분 ID, 해시, 버전, 메타데이터, 공개 지식 청크 |
| **Customer Local Runtime** | Docker Agent, n8n, FastAPI, SQLite/Postgres Local, Vector Store, Ollama/vLLM, Web UI | 민감 문서 처리, 파싱, RAG, 정합성 검사, 검토 워크플로 | 고객 문서, 설계치, SRS/IFU/RMS, 감사로그 |
| **Admin/Ops** | Monitoring, Audit Export, Backup, License Manager | 운영 상태, 비용, 지식팩 버전, 라이선스 관리 | 운영 로그, 사용량, 오류 이벤트 |

**데이터 경계 규칙:**
- 고객 문서 원문, 임상 원자료, 소스코드, 설계치, 시험 원자료는 **클라우드로 전송하지 않는다**
- 클라우드에는 공개 규제 자료, 지식팩 버전, 고객별 라이선스/동기화 메타데이터만 저장
- 로컬 에이전트가 **outbound HTTPS로 지식팩을 pull**하는 구조를 기본값으로 한다

---

## 3. 핵심 데이터 모델 (Unified Schema)

### 3.1 엔티티 정의

| 엔티티 | 주요 필드 | 설명 |
|--------|---------|------|
| **Product** | `product_id`, `product_family`, `intended_use`, `region_targets`, `device_class_hint` | 제품군/지역/용도 기준으로 규제 지식과 문서를 매핑 |
| **Document** | `doc_id`, `doc_type`, `version`, `owner`, `source_file_hash`, `status` | IFU/SRS/RMS/시험요약 등 문서 단위 관리 |
| **Requirement** | `req_id`, `source`, `clause_ref`, `text`, `product_family`, `severity` | 규제/표준/내부 요구사항 |
| **Hazard/Risk** | `risk_id`, `hazard`, `hazardous_situation`, `harm`, `risk_level`, `control_id` | ISO 14971형 위험관리 구조 반영 |
| **Control** | `control_id`, `control_type`, `linked_srs`, `linked_ifu_warning`, `verification_id` | 위험통제 수단과 문서/검증 연결 |
| **Evidence** | `evidence_id`, `test_report_ref`, `result_value`, `acceptance_criteria`, `file_ref` | 시험성적서와 검증 증적 |
| **Finding** | `finding_id`, `severity`, `message`, `evidence_links`, `reviewer_status` | 정합성 검사/AI 검토 결과 |
| **AuditEvent** | `event_id`, `user_id`, `action`, `timestamp`, `before_hash`, `after_hash` | 검토·수정·승인 이력 |

### 3.2 JSON 예시 (X-ray IFU)

```json
{
  "product": {
    "family": "X-ray System",
    "region_targets": ["US", "KR", "EU"]
  },
  "document": {
    "type": "IFU",
    "version": "0.9",
    "source_hash": "sha256:..."
  },
  "requirement_links": [
    {
      "req_id": "FDA-CYBER-001",
      "clause_ref": "cybersecurity design documentation",
      "confidence": 0.88
    }
  ],
  "risk_controls": [
    {
      "risk_id": "RISK-012",
      "control": "warning label + software interlock",
      "linked_srs": ["SRS-45"],
      "linked_ifu": ["IFU-W-03"]
    }
  ]
}
```

---

## 4. 기능 요구사항 상세

| ID | 기능 | 설명 | 구현 포인트 | 수용 기준 |
|----|------|------|-----------|---------|
| **FR-201** | Dynamic Parser | DOCX/XLSX 문서를 파싱하여 Unified Schema 후보 필드로 매핑 | 필수 필드 completeness, rule match, semantic score를 조합해 confidence 산출 | 핵심 필드 85%+ 목표; confidence < 0.85는 보정 UI 표시 |
| **FR-202** | Manual Correction UI | 자동 매핑 결과를 사용자에게 보여주고 필드 단위 수정/승인을 받음 | 원문 위치 하이라이트, 추천값, 변경 이력 표시 | 수정 전후 값과 작업자 로그 저장 |
| **FR-203** | Consistency Guardrail | RMS-SRS-IFU-시험증적 간 연결성 누락/불일치를 탐지 | 규칙 기반 그래프 쿼리 + LLM 보조 설명 | High finding은 승인 전 해결/예외승인 필요 |
| **FR-204** | Regulatory Knowledge Pack | 국가/기관/제품군별 공개 규제 지식을 버전 패키지로 제공 | 문서 청크, 출처 URL, 버전, 해시, 적용 제품군 포함 | 지식팩 버전/변경 이력 조회 가능 |
| **FR-205** | Impact Analyzer | 규제 변경 이벤트와 제품군/문서 필드를 매핑하여 영향도 큐를 생성 | 변경 diff, 관련 요구사항, 영향 문서, 추천 액션 표시 | 24시간 이내 큐 생성 목표 |
| **FR-206** | Local RAG Assistant | 로컬 문서와 지식팩을 함께 검색하여 근거 기반 답변/초안을 생성 | 근거 문서/청크/조항 링크와 confidence 표시 | 근거 없는 답변은 제출용 표시 금지 |
| **FR-207** | Review Workspace | 검토 큐, 상태, 담당자, 우선순위, 승인/반려 흐름을 제공 | RA/QA/관리자 역할별 권한과 상태 전이 | 비전문 개발자도 기본 업로드/검토 가능 |
| **FR-208** | Audit & Export | 검토 결과, 추적성 매트릭스, 보완 대응 초안, 감사로그를 내보냄 | DOCX/XLSX/PDF/JSON export 옵션 | 작업자/시간/근거/변경내역 포함 |
| **FR-209** | Admin & License | 고객사 로컬 에이전트 상태, 지식팩 버전, 라이선스 상태를 관리 | 상태 heartbeat는 민감 데이터 제외 | 관리 콘솔에서 동기화 상태 확인 |

---

## 5. 비기능 요구사항

| 분류 | 요구사항 | 목표/기준 | 검증 방법 |
|------|---------|---------|---------|
| **보안** | 로컬 Inbound deny-all; 외부 통신은 outbound HTTPS/TLS 1.3 기준 고객 원문 문서 외부 전송 금지 | — | 네트워크 로그/프록시 로그 검증 |
| **개인/기밀정보** | 문서 원문, 설계치, 임상 원자료, 소스코드 클라우드 저장 금지 | — | 민감정보 local-only DLP 테스트, 업로드 차단 테스트 |
| **성능 (파싱)** | 100페이지 DOCX 파싱 3분 이내 목표 | 표준 로컬 CPU/GPU 환경 기준 | 샘플 벤치마크 |
| **성능 (검색)** | RAG 답변 30초 이내 1차 응답 목표 | 문서 규모 5천 청크 이하 MVP 기준 | 부하 테스트 |
| **성능 (정합성)** | 핵심 문서 세트 10분 이내 검사 목표 | IFU/SRS/RMS/시험요약 기준 | 파일럿 데이터 측정 |
| **가용성** | 클라우드 지식 서비스 99.5% 목표; 로컬 단독 검토 가능 | 동기화 장애 시 기존 지식팩 사용 | 장애 주입 테스트 |
| **운영성** | Docker Compose 또는 Helm 기반 설치 표준 패키지 1일 설치 목표 | — | 설치 체크리스트 |
| **감사성** | 모든 수정·승인·export 이벤트 로그화 | 불변/append-only 옵션 | 감사로그 샘플 검증 |
| **저장성** | 공개 원문은 S3 archive 정책, 검색용 인덱스는 핫 스토리지 유지 | 복원 지연을 고려한 계층화 | 복원/재색인 리허설 |

---

## 6. 클라우드 구축 상세

| 컴포넌트 | 권장 서비스 | 구축 내용 | 운영 주의사항 |
|---------|-----------|---------|-----------|
| **Raw Source Archive** | S3 + KMS + Lifecycle | 공개 규제 원문/첨부파일 원본 저장, 7~30일 후 Deep Archive 전환 | Deep Archive는 실시간 조회 불가, 검색 인덱스 별도 유지 |
| **Metadata DB** | PostgreSQL/Aurora/RDS + pgvector | 문서 청크, 임베딩, 소스 URL, 버전, 제품군 태그 관리 | 비용 고려해 dev/prod 분리 |
| **Crawler Jobs** | Lambda/Container/ECS/Fargate | 웹/API/RSS 수집, 파싱, 중복 제거, 해시 계산 | 소스별 robots/이용약관 준수 |
| **Queue/Event** | EventBridge + SQS/SNS | 변경 감지 이벤트, 지식팩 생성, 고객 알림 | 재시도/DLQ 구성 |
| **Sync API** | API Gateway/ALB + signed manifest | 고객 에이전트가 지식팩 manifest를 pull | 인증/서명/고객별 isolation |
| **Monitoring** | CloudWatch + Budgets | 크롤러 실패, 큐 적체, 비용 초과 알림 | 월 $5 가드는 dev/idle 기준 |
| **Secrets** | Secrets Manager/Parameter Store | API key, signing key, DB credential 관리 | 키 로테이션 정책 필요 |

---

## 7. 로컬 런타임 구축 상세

| 컴포넌트 | 기술 후보 | 역할 | 비고 |
|---------|---------|------|------|
| **Orchestrator** | n8n 또는 Temporal Lite | 파일 업로드, 파싱, 검사, RAG, export 워크플로 | MVP는 n8n으로 빠른 구현 |
| **API** | FastAPI | UI와 파서/검사기/검색기의 로컬 API | OpenAPI 문서 자동 생성 |
| **Local DB** | SQLite/PostgreSQL | 스키마, 문서 메타, 감사로그 저장 | 단일 PC/NAS는 SQLite 가능 |
| **Vector Store** | SQLite-vec/FAISS/pgvector local | 로컬 문서 청크 검색 | 데이터 규모에 따라 선택 |
| **LLM Runtime** | Ollama 또는 vLLM | 근거 기반 답변/초안 생성 | GPU 없으면 소형 모델/CPU fallback |
| **Parser** | python-docx/openpyxl/pdfplumber + rules + embeddings | DOCX/XLSX 필드 추출/매핑 | OCR은 후순위 |
| **Web UI** | React/Vue/Svelte | 검토 큐, 보정 UI, 대시보드 | 권한/감사 이벤트 필수 |
| **Packaging** | Docker Compose | 설치/업데이트/백업 표준화 | 고객사 프록시/인증서 설정 지원 |

> **[GAP-T11]** Docker Compose 파일 미작성 — `SPEC-DOC-001 T11` 완료 후 실제 `docker-compose.yml` 추가 예정

---

## 8. 주요 워크플로와 상태 전이

### 8.1 핵심 워크플로

1. **Regulatory Update** — 클라우드 크롤러가 원문 변경을 감지하고 `source_hash`, `diff_summary`, `product_family_tags`를 생성
2. **Knowledge Pack Build** — 정규화 파이프라인이 청크, 임베딩, 메타데이터, manifest를 생성하고 서명
3. **Local Sync** — 고객사 에이전트가 outbound HTTPS로 manifest를 조회하고 필요한 증분 지식팩만 다운로드
4. **Document Ingestion** — 사용자가 내부 문서를 업로드하면 파서가 필드 후보와 confidence를 생성
5. **Human Correction** — confidence 미달 또는 필수 필드 누락 시 사용자가 보정하고 승인
6. **Guardrail Check** — 그래프 룰과 RAG 근거 검색으로 문서 간 불일치/누락 finding을 생성
7. **Review & Approval** — RA/QA/관리자가 finding을 해결, 예외승인, 반려, 산출물 내보내기를 수행

### 8.2 상태 전이 테이블

| 현재 상태 | 다음 상태 | 트리거 | 차단 조건 |
|---------|---------|-------|---------|
| Uploaded | Parsed | 파서 성공 | 파일 손상/미지원 포맷 |
| Parsed | Needs Correction | confidence < threshold | 필수 필드 누락 |
| Parsed | Ready for Check | confidence >= threshold | 없음 |
| Ready for Check | Finding Open | 불일치 발견 | High finding 존재 |
| Finding Open | Resolved | 수정/근거 첨부 | 근거 부족 |
| Resolved | Approved | 책임자 승인 | 권한 부족 |
| Approved | Exported | 내보내기 실행 | 감사로그 생성 실패 |

---

## 9. API/이벤트 인터페이스 초안

| 인터페이스 | 메서드/방식 | 입력 | 출력/효과 |
|---------|-----------|------|---------|
| `/sync/manifest` | GET | `tenant_id`, `current_pack_version`, `product_family` | delta manifest, hash, signed URL |
| `/sync/pack/{id}` | GET | `pack_id`, `signature` | knowledge pack 다운로드 |
| `/documents/upload` | POST | `local file`, `doc_type_hint`, `product_id` | `doc_id`, `parse_job_id` |
| `/parse/jobs/{id}` | GET | `parse_job_id` | field candidates, confidence, required missing |
| `/guardrail/run` | POST | `product_id`, `doc_set_ids`, `rule_set_version` | finding list |
| `/rag/query` | POST | `question`, `scope`, `evidence_required=true` | answer, evidence_links, confidence |
| `/audit/export` | POST | `scope`, `date_range`, `format` | audit package |

> **[GAP-T12]** OpenAPI 완전 명세 미작성 — 요청/응답 JSON Schema, 인증 헤더, 오류 코드 추가 예정

---

## 10. UI/UX 요구사항

> **[GAP-T09]** UI/UX 와이어프레임 미작성 — `SPEC-DOC-001 T09` 완료 후 추가 예정

**구현 예정 화면 목록:**
1. 대시보드 — KPI 카드, 검토 큐 미리보기, 규제 업데이트 알림
2. 문서 업로드 — 드래그앤드롭, 형식 지원 표시, 파싱 진행 상태
3. 보정 UI — 원문 하이라이트, 필드별 수정, confidence 표시
4. 검토 큐 — 우선순위 정렬, 제품군 필터, 상태 관리
5. Traceability Graph — 연결 시각화, 누락/불일치 하이라이트
6. RAG 검색 — 질의 입력, 근거 링크, confidence 표시
7. 감사로그 — 작업자/시간/변경내역, 내보내기
8. 설정/관리자 — 지식팩 버전, 동기화 상태, 라이선스

---

## 11. 파서 NLP 명세

> **[GAP-T10]** 파서 NLP 상세 명세 미작성 — `SPEC-DOC-001 T10` 완료 후 추가 예정

**추가 예정 내용:**
- X-ray IFU 핵심 필드 10~15개 정의 (Device Name, Indications, Contraindications, Warnings 등)
- Confidence 계산 공식 (필수 필드 완성도 + 규칙 매칭 + 시멘틱 스코어)
- 모델 선택 근거: spaCy NER vs LLM 폴백 전략
- 학습 데이터 전략 및 정답 세트 구성 방법

---

## 12. 테스트 전략과 Definition of Done

### 12.1 테스트 유형

| 테스트 유형 | 범위 | 통과 기준 |
|-----------|------|---------|
| **Unit Test** | 파서 룰, schema validator, graph rule, API handler | 핵심 로직 80%+ 커버리지 목표 |
| **Golden Dataset Test** | 샘플 IFU/SRS/RMS/XLSX 정답 세트 | 핵심 필드 85%+ 목표 달성 여부 측정 |
| **Security Test** | 원문 외부 전송 차단, 인증/권한, 로그 마스킹 | 패킷/로그에서 민감 원문 미검출 |
| **Integration Test** | 클라우드 변경 이벤트 → 로컬 동기화 → 검토 큐 | E2E 시나리오 성공 |
| **Performance Test** | 100페이지 DOCX, 5천 청크 RAG, 문서세트 검사 | 목표 시간 내 완료 또는 degradation 표시 |
| **User Acceptance Test** | RA/QA 검토자 워크플로 | 업로드-보정-검토-승인-export 완료 |
| **Disaster/Recovery Test** | 지식팩 복원, 로컬 DB 백업/복구 | 복구 절차 문서화와 리허설 완료 |

### 12.2 Definition of Done

각 기능은 다음 조건을 모두 충족해야 Done으로 간주한다:
- [ ] 수용 기준 충족
- [ ] 감사로그 구현
- [ ] 오류 처리 구현
- [ ] 사용자 메시지 구현
- [ ] 근거 링크 표시 구현
- **AI 답변 기능:** 근거 없는 답변 차단, confidence 표시, 사용자 승인 단계 필수
- **로컬 설치 패키지:** 고객사 프록시/인증서/오프라인 환경 체크리스트 포함

---

## 13. 구축 순서와 백로그 우선순위

| Epic | 주요 작업 | 산출물 | 우선순위 |
|------|---------|-------|---------|
| **Cloud Knowledge Foundation** | 소스 목록, 크롤러, S3 저장, 문서 해시, 메타 DB | 수집/변경 감지 PoC | P0 |
| **Unified Schema** | 제품/문서/요구사항/위험/증거 엔티티 정의 | schema.json, validator | P0 |
| **Local Ingestion** | DOCX/XLSX 파서, confidence, 보정 UI | 파서 MVP | P0 |
| **Traceability Graph** | 연결 모델, graph rule, finding 생성 | 정합성 검사 MVP | P1 |
| **RAG Assistant** | 지식팩+로컬문서 검색, 근거 출력 | 근거 기반 질의응답 | P1 |
| **Review Workspace** | 검토 큐, 역할/상태, 승인/반려 | 로컬 웹 UI | P1 |
| **Impact Analyzer** | 규제 변경 diff, 제품군 매핑, 큐 생성 | 영향도 리포트 | P2 |
| **Ops/Admin** | 모니터링, 라이선스, export, 백업 | 상용화 운영 기능 | P2 |

---

## 14. Terraform 기준 스니펫

> Cloud Control Plane 기준 IaC 스니펫. 프로덕션에서는 계정/리전/보안정책/IAM 최소권한/비밀관리/상태관리 백엔드/CI 승인 절차를 별도 적용한다.

```hcl
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region = "ap-northeast-2"
}

resource "aws_s3_bucket" "regulatory_brain" {
  bucket        = "global-regulatory-brain-archive-${var.env}"
  force_destroy = false
}

resource "aws_s3_bucket_versioning" "regulatory_brain" {
  bucket = aws_s3_bucket.regulatory_brain.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "regulatory_brain" {
  bucket = aws_s3_bucket.regulatory_brain.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "aws:kms" }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "archive" {
  bucket = aws_s3_bucket.regulatory_brain.id
  rule {
    id     = "archive-public-regulatory-originals"
    status = "Enabled"
    transition { days = 14, storage_class = "DEEP_ARCHIVE" }
  }
}

resource "aws_sqs_queue" "crawler_events" {
  name                       = "regulatory-crawler-events-${var.env}"
  message_retention_seconds  = 1209600
}

resource "aws_sns_topic" "sync_notifier" {
  name = "regulatory-sync-push-topic-${var.env}"
}

resource "aws_budgets_budget" "cost_guard" {
  name         = "ai-ra-cost-guard-${var.env}"
  budget_type  = "COST"
  limit_amount = var.monthly_budget_usd
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.billing_alert_emails
  }
}
```

---

## 참고 근거 및 출처

1. [FDA, Overview of Device Regulation](https://www.fda.gov/medical-devices/device-advice-comprehensive-regulatory-assistance/overview-device-regulation)
2. [FDA, Cybersecurity in Medical Devices: QMS Considerations and Premarket Submissions](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cybersecurity-medical-devices-quality-management-system-considerations-and-content-premarket)
3. [EUR-Lex, Regulation (EU) 2017/745 on medical devices](https://eur-lex.europa.eu/eli/reg/2017/745/oj/eng)
4. [European Commission, Medical Devices Sector / EUDAMED](https://health.ec.europa.eu/medical-devices-sector_en)
5. [MFDS, Medical Device Regulations / Enforcement Rule resources](https://www.mfds.go.kr/eng/brd/m_40/list.do)
6. [AWS, S3 Glacier storage classes](https://aws.amazon.com/s3/storage-classes/glacier/)
7. [AWS, S3 Lifecycle transition documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-transition-general-considerations.html)
8. [AWS, AWS Budgets cost notifications](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)
9. [pgvector, open-source vector similarity search for PostgreSQL](https://github.com/pgvector/pgvector)

---

*버전: v3.0 | 갭 트래커: [SPEC-DOC-001](.moai/specs/SPEC-DOC-001/spec.md)*
