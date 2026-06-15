# SPEC-AUTHORING-001 — Task Breakdown

Guided Authoring Workspace 구현 태스크. 대상: `customer-runtime/` (FastAPI + PostgreSQL + Ollama + pgvector). 개발 방법론: TDD (RED-GREEN-REFACTOR). 모든 코드 주석은 영어.

관련 문서:
- 요구사항: `spec.md` (REQ-AUTHOR-001~018)
- 인수 기준: `acceptance.md` (AC-001~016)
- 의존 데이터 모델: `../SPEC-TEMPLATE-001/spec.md`

---

## P0 — Critical (Foundation)

세션·섹션 트리·콘텐츠 저장 기초. AI·진행률·내보내기 없이도 빈 페이지 대체 진입 경로 확보.

### T-P0-1: 데이터 모델 마이그레이션
- [ ] AuthoringSession ORM 모델 (session_id, product_profile_id, pack_id, status, created_by, timestamps)
- [ ] AuthoringSectionEntry ORM 모델 (entry_id, session_id, section_id, content, ai_draft, ai_draft_confidence, ai_draft_sources[], status, skip_reason, reviewer_comment, updated_at)
- [ ] status enum 제약: session(draft/in_progress/complete/submitted), entry(empty/ai_draft/human_edited/complete/skipped)
- [ ] FK: AuthoringSectionEntry.session_id → AuthoringSession
- [ ] Alembic 마이그레이션 작성 + 적용 검증
- 대응: 데이터 모델 §2.1, §2.2

### T-P0-2: Pydantic 스키마
- [ ] 세션 생성 요청/응답 (product_profile_id, pack_id, created_by → session_id, status, total_sections)
- [ ] 섹션 트리 응답 (section + entry 합성)
- [ ] 섹션 PATCH 요청 (content, status, skip_reason)
- 대응: API §4.1, §4.3, §4.4

### T-P0-3: 세션 생성 서비스 + 라우터
- [ ] `POST /authoring/sessions` — pack 섹션 트리 읽어 섹션마다 empty entry 생성 (REQ-AUTHOR-001)
- [ ] 미지원 팩(섹션 트리 없음) 404 반환, 세션 미생성 (REQ-AUTHOR-002)
- [ ] `GET /authoring/sessions/{id}` 기본 조회 (진행률은 P1)
- 대응: REQ-AUTHOR-001, 002 / AC-001, 002

### T-P0-4: 섹션 트리 조회 API
- [ ] `GET /authoring/sessions/{id}/sections` — section_id, section_key, title, instructions, placeholder, required, sort_order + entry 상태 (REQ-AUTHOR-003)
- [ ] 필수/선택 구분 필드 노출 (REQ-AUTHOR-004)
- 대응: REQ-AUTHOR-003, 004 / AC-003, 004

### T-P0-5: 콘텐츠 저장 기본 경로
- [ ] `PATCH /authoring/sections/{entry_id}` — content 저장 시 status 최소 human_edited 전이 (REQ-AUTHOR-006)
- 대응: REQ-AUTHOR-006 / AC-006

---

## P1 — High

AI 초안 + 상태 머신 + 진행률 + 저장·재개. P1(스타트업 CTO) 핵심 가치 실현.

### T-P1-1: 섹션 상태 머신 서비스
- [ ] 허용/금지 전이 규칙 구현 (spec.md §3)
- [ ] PATCH 상태 변경 시 전이 검증, 금지 전이 400 (REQ-AUTHOR-005)
- [ ] ai_draft → complete 직접 전이 금지, human_edited 경유 강제 (REQ-AUTHOR-007)
- 대응: REQ-AUTHOR-005, 007 / AC-005, 007

### T-P1-2: AI 초안 생성 (Ollama + pgvector RAG)
- [ ] `POST /authoring/sections/{entry_id}/ai-draft` — empty 상태에서만 허용 (REQ-AUTHOR-008)
- [ ] 로컬 지식 베이스 pgvector RAG 검색 → Ollama 초안 생성 (parser_engine/llm_fallback.py 패턴 재사용)
- [ ] ai_draft, ai_draft_confidence, ai_draft_sources 저장, status ai_draft 전이
- [ ] 클라우드 전송 없음 — 로컬 추론만 (REQ-AUTHOR-009)
- [ ] empty 아닌 entry 대상 409, 콘텐츠 미변경 (REQ-AUTHOR-012)
- [ ] 30초 timeout 상태 반환 (REQ-AUTHOR-013)
- 대응: REQ-AUTHOR-008, 009, 012, 013 / AC-008, 009, 012, 013

### T-P1-3: AI 초안 표기 + 출처
- [ ] ai_draft 응답에 verified:false + "AI generated, not verified" 표기 (REQ-AUTHOR-010)
- [ ] RAG 출처 참조 응답 포함 (REQ-AUTHOR-011)
- 대응: REQ-AUTHOR-010, 011 / AC-010, 011

### T-P1-4: 진행률 추적
- [ ] AuthoringProgress 집계 (total_required_sections, completed_sections, blocking_gaps[], completion_pct)
- [ ] completion_pct = 완료 필수 / 전체 필수, 선택·skip 제외 (REQ-AUTHOR-015)
- [ ] `GET /authoring/sessions/{id}` 응답에 진행률 + blocking gaps (REQ-AUTHOR-016)
- 대응: REQ-AUTHOR-015, 016 / AC-015

### T-P1-5: 저장·재개 영속화
- [ ] draft/in_progress 세션의 모든 entry 변경 영속화 (REQ-AUTHOR-017)
- [ ] 재개 시 부분 콘텐츠·상태 무손실 검증
- 대응: REQ-AUTHOR-017

---

## P2 — Medium

내보내기 + 일괄 초안 + skip + 공유.

### T-P2-1: DOCX/JSON 내보내기
- [ ] `POST /authoring/sessions/{id}/export` — format docx/json (REQ-AUTHOR-018)
- [ ] TemplateDocument.sort_order + TemplateSection.sort_order 순서 보존
- [ ] 미지원 format 400
- 대응: REQ-AUTHOR-018 / AC-016

### T-P2-2: 선택 섹션 skip
- [ ] PATCH skip 전이 + skip_reason 저장 (선택 섹션만)
- [ ] 필수 섹션 skip 시도 400 (REQ-AUTHOR-014)
- 대응: REQ-AUTHOR-014 / AC-014

### T-P2-3: 일괄 AI 초안
- [ ] 세션 내 모든 empty 섹션 1회 호출 초안 생성
- [ ] 동시성 한도 적용 (Open Decision: 로컬 부하 고려)

### T-P2-4: 세션 공유 URL
- [ ] 읽기/편집 공유 링크 발급

---

## 검증 체크리스트 (완료 기준)

- [ ] 전체 REQ-AUTHOR-001~018 대응 테스트 통과
- [ ] AC-001~016 Given/When/Then 시나리오 통과
- [ ] 커버리지 85% 이상
- [ ] ruff 클린
- [ ] AI 초안 클라우드 전송 0건 (네트워크 검증 테스트)
- [ ] 코드 주석 영어
- [ ] SPEC-TEMPLATE-001 데이터 모델 정합성 확인 (section_id/pack_id 참조)

---

## 전문가 자문

- **expert-backend**: 상태 머신 서비스, Ollama + pgvector RAG 비동기 호출, 진행률 집계 쿼리, 30초 timeout
- **expert-frontend**: 섹션 트리 작성 UI (후속 UI SPEC에서 상세)
