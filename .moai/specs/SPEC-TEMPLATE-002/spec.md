---
id: SPEC-TEMPLATE-002
version: 0.1.0
status: completed
created_at: 2026-06-20
updated: 2026-06-20
author: drake.lee
priority: medium
issue_number: 55
---

# SPEC-TEMPLATE-002: Authoring/Checklist Template Stub 제거 및 TEMPLATE_API_URL 실제 연동

## HISTORY

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|-----------|--------|
| 0.1.0 | 2026-06-20 | 최초 작성 | drake.lee |

## 개요

| 항목 | 내용 |
|------|------|
| 목적 | 운영 경로에서 authoring/checklist template stub fallback 제거 및 실제 Template API 연동 |
| 범위 | hybrid-ra-saas 백엔드 서비스 구현 (템플릿 선택/표시 UI 제외) |
| 의존 SPEC | SPEC-CRAWLER-002, SPEC-RAG-001 완료 후 진행 권장 |
| 관련 이슈 | #55 |

## 배경

현재 잔여 지점:
- `customer-runtime/src/app/routers/authoring.py`: Template section stub/cloud resolver
- `customer-runtime/src/app/services/checklist/generator.py`: `@MX:TODO: implement live httpx call to TEMPLATE_API_URL`

운영 환경에서 stub data가 사용되어 실제 템플릿이 적용되지 않는 위험이 있다.

## EARS 요구사항

### 실제 연동

**REQ-TEMPLATE-002-001**: WHEN TEMPLATE_API_URL이 설정된 운영 환경에서 authoring draft 생성 요청이 수신될 때, stub 데이터가 아닌 TEMPLATE_API_URL에서 가져온 실제 template이 사용되어야 한다.

**REQ-TEMPLATE-002-002**: WHEN TEMPLATE_API_URL이 설정된 운영 환경에서 checklist 생성 요청이 수신될 때, live httpx call을 통해 실제 template contract가 호출되어야 한다.

**REQ-TEMPLATE-002-003**: WHEN checklist generation과 authoring draft 생성이 모두 실행될 때, 동일한 template contract를 사용해야 한다.

### 오류 처리

**REQ-TEMPLATE-002-004**: WHEN TEMPLATE_API_URL 호출이 실패할 때, deterministic한 오류 응답 또는 명시적 fallback 정책이 적용되어야 한다.

**REQ-TEMPLATE-002-005**: IF TEMPLATE_API_URL 호출 시 timeout이 발생하면, 설정된 retry 횟수 이후 오류가 반환되어야 한다.

### stub 제한

**REQ-TEMPLATE-002-006**: WHEN 운영 환경에서 실행될 때, stub/placeholder template이 사용되지 않아야 한다.

**REQ-TEMPLATE-002-007**: IF test-only 또는 local 환경에서 실행될 때, stub fallback이 명시적으로 test-only/local-only로 제한되어야 한다.

### 운영 설정

**REQ-TEMPLATE-002-008**: WHEN README 또는 docs를 참조할 때, TEMPLATE_API_URL 운영 설정 방법이 명시되어 있어야 한다.

## 기술 접근 방법

1. `authoring.py` cloud resolver stub을 live httpx call로 교체
2. `generator.py` `@MX:TODO` 구현: httpx async call to TEMPLATE_API_URL
3. 공통 template client 모듈 생성 (authoring + checklist 공유)
4. timeout/retry 설정 (환경변수 기반)
5. error mapping: HTTP error → 애플리케이션 오류 코드
6. test-only stub을 pytest fixture 또는 환경변수 조건으로 명시적 분리
7. README/docs 운영 설정 가이드 추가

## 영향 파일

- `customer-runtime/src/app/routers/authoring.py`
- `customer-runtime/src/app/services/checklist/generator.py`
- `customer-runtime/src/app/services/template_client.py` (신규 또는 기존)
- `README.md` 또는 `docs/` — 운영 설정 가이드

## 제외 범위

- 템플릿 선택/표시 UI (ra-med-bot 담당)
- Template API 서버 내부 구현
