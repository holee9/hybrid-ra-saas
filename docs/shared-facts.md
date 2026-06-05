# Shared Facts — Global Hybrid AI RA Specialist

<!-- 단일 출처 파일. 모든 문서의 가격·지표·품목·포지셔닝은 이 파일에서 정의됨 -->
<!-- 기준일: 2026-06-05 | 업데이트 시 전 문서 참조값 동기화 필요 -->

## 가격 정책 (Pricing)

| 플랜 | 가격 | 대상 | 구성 |
|------|------|------|------|
| Core SaaS | 월 $299 | 스타트업/초기팀 | 규제 변경 알림, 기본 지식팩, 표준 스키마 템플릿, 제한된 문서 검토 |
| Advanced Hybrid | 연 $12,000 | 중견/내부망 기업 | 로컬 Docker 에이전트, 정합성 가드레일, 관리자 대시보드, 감사로그 |
| Setup & Enablement | 별도 견적 | 초기 배포 고객 | 고객 환경 점검, 로컬 설치, 초기 문서 스키마 정리, 교육 |
| Regulatory Pack Add-on | 제품군/국가별 과금 | 확장 고객 | 추가 품목군·국가별 규제 지식팩 |

## 핵심 지표 (Key Metrics)

| 지표 | 목표 | 비고 |
|------|------|------|
| 핵심 필드 파싱 정확도 | 85%+ | 표준 문서·양호 품질 기준 |
| 핵심 문서세트 검토 속도 | 10분 이내 | IFU/SRS/RMS/시험요약 기준 |
| 표준 패키지 설치 | 1일 이내 | 고객 네트워크 정책 예외 가능 |
| 규제 변경 알림 | 24시간 이내 | 소스 변경 후 큐 생성 기준 |
| 문서 준비 기간 단축 | 30~50% | 파일럿 목표, 보증 아님 |

## 개발 품목 및 연동 대상 (Product Scope)

**개발 대상 (직접 개발):**
- X-ray 시스템
- 디지털 디텍터
- 촬영실 SW (PACS 연동 대상)
- 피부미용 초음파

**연동 대상 (직접 개발 아님):**
- PACS — 외부 시스템 연동(interoperability) 대상. 개발 품목은 "촬영실 SW"이며 PACS는 연동 범위에 포함

**제외 범위:** IVD, 치과용 전 품목, 임상시험 원자료 분석, 해외 제출 대행

## 포지셔닝 문장 (Canonical Positioning)

> 일회성 컨설팅 대행이 아닌, 표준화된 셀프서비스 구독형 규제 운영 플랫폼.

이 문장을 모든 문서(BizPlan, MRD, PRD, product.md, README)에 문자 단위 동일 적용한다.

## 아키텍처 정본 (Architecture Canonical)

**3레이어 구조:**
1. **Cloud Control Plane** — 규제 크롤러/수집, 정규화, PostgreSQL/pgvector, S3 Archive, EventBridge/SQS/SNS
2. **Secure Sync Layer** — 지식팩 서명/버전 관리, 증분 동기화, 아웃바운드 HTTPS
3. **Customer Local Runtime** — Docker 에이전트, 파서, RAG, 정합성 검사, 웹 UI
   - 하위 컴포넌트: Review Workspace, Impact Analyzer

## 시장 규모 (TAM/SAM/SOM)

**데이터 출처:** Grand View Research, MarketsandMarkets, Strategic Market Research

| 구분 | 규모 | CAGR | 비고 |
|------|------|------|------|
| TAM (글로벌 의료기기 QMS/RA 소프트웨어) | $6.75B (2024) → $11.66B (2030) | 9.55% (2025~2030) | 출처: Grand View Research, MarketsandMarkets (2024-2030 예측) |
| SAM (SaaS+하이브리드 배포 가능 세그먼트) | ~$3.5B | — | TAM의 약 50% 추정 (하이브리드 배포 가능한 중소형 고객사) |
| SOM Y1 (한국+미국 스타트업/중견, 초기 품목군) | $12M~18M | — | Advanced 10개 + Core 50개 시나리오 기준 |
| SOM Y3 (확장 후) | $50M~80M | — | Advanced 30개 + Core 300개 시나리오 기준 |

**시장 선택 근거:**
- 의료기기 규제 요건 강화 (FDA 510(k), EU MDR 전환 진행 중) → 문서 자동화 수요 증가
- 하이브리드 AI 도구 도입 의지: 클라우드 전면 전환 불가 기업 증가
- 초기 집중 품목군 (X-ray/디텍터/촬영실 SW/피부미용 초음파): 규제 문서 구조 반복성 높음

**Sources:**
- [Grand View Research - Medical Device Regulatory Affairs Market, 2030](https://www.grandviewresearch.com/industry-analysis/medical-device-regulatory-affairs-market)
- [MarketsandMarkets - Medical Device Regulatory Affairs Market Size & Growth Forecast 2025](https://www.strategicmarketresearch.com/market-report/medical-device-regulatory-affairs-market)
- [Research and Markets - Medical Device Regulatory Affairs Market Size Report](https://www.researchandmarkets.com/reports/5415527/medical-device-regulatory-affairs-market-size)

## 경쟁 벤더 분석

| 벤더 | 주요 기능 | 가격대 | 타깃 | 약점 | 본 제품 포지션 |
|------|---------|------|------|------|------------|
| **Veeva Vault Quality** | eQMS, 문서 관리, CAPA, 규제 제출 지원 | 엔터프라이즈 (연 $50K+) | 대형 제약/의료기기 | 고비용·장기 도입, 클라우드 전용, AI 지식팩 약함 | 초기 품목군 특화 경량 하이브리드 |
| **Sparta Systems TrackWise** | QMS, 통합 컴플라이언스 관리 | 엔터프라이즈 | 대형 제조사 | 커스터마이징 비용 높음, AI 자동화 부족 | 셀프서비스 + 자동 규제 지식 연동 |
| **MasterControl** | QMS/DMS, 문서 제어, 교육 관리 | 중견-대형 ($20K+/년) | 의료기기·제약 | 온프레미스 복잡, SaaS 이전 지연 | 로컬 런타임 우선 + AI 보조 |
| **Qara (구 Greenlight Guru)** | 의료기기 특화 QMS, Design Control | 중소형-중견 ($12K~30K/년) | 의료기기 스타트업 | 규제 지식팩 없음, 문서 AI 약함 | AI 규제 지식 연동 차별화 |
| **전통 RA 컨설팅** | 전문가 판단, 제출 경험 | 프로젝트당 $5K~50K | 전 규모 | 비용 높고 지식 내재화 안됨 | 컨설팅 보조/표준화 운영 플랫폼 |

**차별화 포인트:** 하이브리드 배포(데이터 주권) + 규제 지식팩 자동 동기화 + 초기 품목군(X-ray/디텍터/촬영실 SW/피부미용 초음파) 특화.

Sources:
- [IntuitionLabs - GxP Compliance Software eQMS Platform Comparison 2026](https://intuitionlabs.ai/articles/gxp-compliance-software-eqms-comparison-2026)
- [G2 - Veeva Vault QMS Reviews 2026](https://www.g2.com/products/veeva-vault-qms/reviews)
- [Capterra - TrackWise Digital vs Vault Quality Suite 2025](https://www.capterra.com/quality-management-software/compare/175662-178567/Trackwise-Digital-vs-Vault-Quality-Suite)
