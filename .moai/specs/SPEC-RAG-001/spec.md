---
id: SPEC-RAG-001
version: 0.1.0
status: planned
created_at: 2026-06-20
updated: 2026-06-20
author: drake.lee
priority: high
issue_number: 54
---

# SPEC-RAG-001: GAP-05 RAG 라우팅 계약 및 서버 측 라우팅 구현

## HISTORY

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|-----------|--------|
| 0.1.0 | 2026-06-20 | 최초 작성 | drake.lee |

## 개요

| 항목 | 내용 |
|------|------|
| 목적 | Customer Runtime RAG와 ra-med-bot/Regula RAG 간 라우팅 책임 확정 및 백엔드 계약 구현 |
| 범위 | hybrid-ra-saas 백엔드 API/계약 작업 (RAG 라우팅 UI 제외) |
| 의존 SPEC | 없음 |
| 관련 이슈 | #54 |
| prereq | SPEC-OPS-001의 선행 조건 |

## 배경

`docs/integration-plan.md`의 GAP-05가 P1로 미해결 상태이다. 어떤 질의가 Customer Runtime local RAG로 가고 어떤 질의가 Regula RAG로 가는지 불명확하다. ra-med-bot이 호출할 수 있는 안정적인 계약이 필요하다.

## EARS 요구사항

### 라우팅 정책

**REQ-RAG-001**: WHEN RAG 질의가 수신될 때, local-only / regula-only / hybrid(fallback) 세 가지 라우팅 모드 중 하나가 선택되어야 한다.

**REQ-RAG-002**: IF 라우팅 모드가 hybrid/fallback으로 설정되어 있고 local RAG 결과가 임계값 미만이면, Regula RAG로 자동 fallback되어야 한다.

**REQ-RAG-003**: WHEN Regula RAG timeout이 발생하면, 명시적인 degraded 응답이 반환되어야 하며 silent failure가 발생하지 않아야 한다.

### API 계약

**REQ-RAG-004**: WHEN ra-med-bot이 RAG API를 호출할 때, request에 라우팅 힌트(routing_mode 또는 context 필드)를 포함할 수 있어야 한다.

**REQ-RAG-005**: WHEN RAG 응답이 반환될 때, 실제 사용된 라우팅 경로(local/regula/hybrid), 소스 출처, confidence 정보가 포함되어야 한다.

**REQ-RAG-006**: WHEN API error가 발생할 때, error code, message, retry 가능 여부가 명시된 표준 오류 응답이 반환되어야 한다.

### 구현

**REQ-RAG-007**: WHEN Customer Runtime 백엔드에 라우팅 hook이 구현될 때, 프론트엔드 변경 없이 ra-med-bot이 서버 계약만으로 구현을 진행할 수 있어야 한다.

**REQ-RAG-008**: WHEN E2E smoke test가 실행될 때, local-only / regula-only / hybrid fallback 세 시나리오 모두 검증되어야 한다.

## 기술 접근 방법

1. 라우팅 정책 정의 문서 작성 (routing_mode 파라미터 스키마)
2. `docs/integration-contract.md`에 RAG routing contract 섹션 추가
3. Customer Runtime 백엔드 라우팅 hook 구현 (routing_mode 기반 분기)
4. timeout/retry/fallback 로직 구현
5. 응답 스키마 확장: `routing_used`, `sources`, `confidence` 필드
6. E2E smoke test 시나리오 작성 및 실행

## 영향 파일

- `customer-runtime/src/app/routers/` — RAG 라우팅 endpoint
- `customer-runtime/src/app/services/` — RAG 서비스 계층
- `docs/integration-contract.md` — RAG routing contract 추가
- `docs/integration-plan.md` — GAP-05 상태 갱신

## 제외 범위

- RAG 라우팅 UI 구현 (ra-med-bot 담당)
- Regula RAG 서버 내부 구현
- embedding 모델 변경
