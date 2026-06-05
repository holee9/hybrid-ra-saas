# Product: Global Hybrid AI RA Specialist

## Overview

의료기기 제조사를 위한 하이브리드 AI 기반 규제 운영(RA) 플랫폼.
글로벌 규제 지식(FDA, MFDS, EU MDR)을 클라우드에서 중앙 관리하고,
민감 문서는 고객 내부망(Local Runtime)에서만 처리하는 Data Sovereignty 아키텍처.

## Target Market

- **주요 고객**: 의료기기 스타트업 및 중견 제조사
- **타깃 품목**: X-ray, 디텍터, 촬영실 SW, 피부미용 초음파
- **핵심 페인포인트**: 개발 후반 문서 소급 작성, 문서 간 불일치, 퍼블릭 SaaS 업로드 보안 우려, 규제 추적 수동화

## Architecture

### Cloud Control Plane
- 규제 크롤러/수집 (FDA, MFDS, EU MDR)
- 정규화 파이프라인
- PostgreSQL + pgvector
- S3/Archive
- Webhook Notifier
- Monitoring & Budget Guard

### Secure Sync Layer
- 아웃바운드 HTTPS only
- 증분 ID/메타데이터 동기화
- 지식팩 버전관리
- 고객사별 분리

### Customer Local Runtime
- n8n Orchestrator
- Dynamic Parser
- Unified Schema Store
- Traceability Graph
- Ollama/vLLM RAG Engine
- Review UI & Audit Log

## Business Model

| Tier | Price | Description |
|------|-------|-------------|
| Core SaaS | $299/월 | 규제 알림 + 기본 지식팩 |
| Advanced Hybrid | $12,000/년 | 내부망 패키지 + 정합성 검사 |
| Setup & Enablement | 별도 견적 | 초기 배포·온보딩·데이터 정리 |

## Key Metrics Targets

- 문서 준비 시간 단축: 30~50%
- 핵심 필드 파싱 정확도: 85%+
- 핵심 문서세트 검토 속도: 10분 이내
- 표준 패키지 배포: 1일 설치

## Roadmap

| Phase | Name | Focus |
|-------|------|-------|
| Phase 1 | Infra | 규제 수집기, 저장소, 동기화 PoC |
| Phase 2 | Logic | 제품군별 스키마, Parser, Guardrail |
| Phase 3 | Product | 셀프서비스 UX, 관리자 기능 |
| Phase 4 | Scale | 타 품목 확장, 파트너십 |

## Document Package

| File | Type | Status |
|------|------|--------|
| 01_사업계획서_v3.0.docx | Business Plan | 점검 필요 |
| 02_MRD_v3.0.docx | Market Requirements Document | 점검 필요 |
| 03_PRD_v3.0.docx | Product Requirements Document | 점검 필요 |
| 04_리뷰용_제안서.html | Review Proposal | 분석 기준 문서 |

## Positioning

컨설팅 대행이 아닌, 표준화된 셀프서비스 규제 운영 플랫폼
