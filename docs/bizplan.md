# 사업계획서 — Global Hybrid AI RA Specialist

> **버전:** v4.0 | **기준일:** 2026-06-05 | **완성도:** 85%+ (SPEC-DOC-001 Run 완료)  
> **분류:** Confidential / Development Version  
> **목적:** 사업화 검토와 MVP/상용화 개발을 동시에 지원하기 위한 실구축 중심 명세  
> **전제:** AI 출력은 RA/QA 전문가 검토를 보조하며, 최종 규제 판단과 제출 책임은 제조사 책임자에게 있음

---

## 1. Executive Summary

본 사업은 의료기기 제조사의 핵심 기술 자료를 퍼블릭 클라우드로 올리지 않으면서,  
FDA · MFDS · EU MDR 등 공개 규제 지식을 클라우드에서 수집·정규화하고  
고객사 내부망에서 문서 정합성 검토와 RAG 기반 초안 생성을 수행하는  
**하이브리드 AI RA 플랫폼**이다.

| 항목 | 내용 |
|------|------|
| **핵심 고객** | X-ray/디텍터/촬영실 SW/피부미용 초음파를 개발하는 스타트업 및 중견 의료기기 제조사 |
| **핵심 문제** | 개발 완료 후 문서 소급 작성 / 문서 간 불일치 / 퍼블릭 SaaS 보안 우려 / 규제 변경 추적 부담 |
| **핵심 해법** | 클라우드 규제 지식팩 + 로컬 Docker 에이전트 + Unified Schema + 추적성 그래프 + 검토 워크스페이스 |
| **포지셔닝** | 일회성 컨설팅 대행이 아닌, 표준화된 셀프서비스 구독형 규제 운영 플랫폼. |
| **초기 전략** | 전 품목 범용 엔진이 아니라, 규제 난도 높고 문서 구조가 반복되는 초기 품목군 집중 |

---

## 2. 팩트 기반 현실성 판단

| 팩트 | 사업 설계 반영 | 현실성 판단 |
|------|-------------|-----------|
| FDA CDRH는 미국 내 의료기기와 X-ray·초음파 등 방사선 발생 전자제품을 규제한다 | X-ray, 디텍터, 초음파를 초기 타깃으로 삼고 FDA 지식팩 1차 구축 | 타깃 도메인 적합성 높음 |
| FDA 사이버보안 가이던스는 사이버보안 설계, 라벨링, 사전시장 제출 문서에 포함할 정보를 권고한다 | 촬영실 SW/PACS/Medical AI 문서에서 보안 요구사항과 증적 추적성을 기능 범위에 포함 | 문서화 자동화 수요 존재 |
| EU MDR 2017/745는 의료기기 규제 체계의 핵심 법령이며, EUDAMED는 MDR/IVDR 구현 EU IT 시스템이다 | EU MDR 지식팩, 문서 근거 링크, 버전 관리를 요구사항에 포함 | 글로벌 지식팩 필요성 명확 |
| MFDS는 의료기기법/시행규칙/허가·심사 규정 등 국내 자료를 운영하며, 한국어 원문이 공식 기준이다 | 한국어 원문 수집·버전 관리와 고객 검토 화면의 근거 링크 제공 필요 | 국내 고객 수용성에 중요 |
| S3 Glacier Deep Archive는 장기 보관에 저비용이나 실시간 조회 불가, 복원 시간 필요 | 원본 공개 규제 자료는 아카이브, 검색 인덱스와 메타데이터는 별도 핫 스토리지 유지 | 비용 절감 가능하나 운영 설계 필요 |
| pgvector는 PostgreSQL 내 벡터 검색 지원으로 규제 지식 검색과 메타데이터 조인이 가능하다 | 중앙 지식 DB에 문서 청크, 버전, 제품군 태그, 임베딩 함께 관리 | 초기 구현 난이도 수용 가능 |

**현실성 결론:**
- 기술적으로 구현 가능하나, "완전 자동 인허가"가 아니라 **"근거 기반 문서 정리·검토 보조"** 로 포지셔닝해야 한다
- 월 $5 이하 인프라 비용은 초기 개발/저부하 아카이브·알림 제어판에 한정; 운영 규모가 커지면 별도 발생
- **85% 파싱 정확도**는 표준 스키마, 문서 품질, 제한된 품목군, 수동 보정 UI를 전제로 한 목표값

---

## 3. 시장 문제와 고객 가치

| 현장 문제 | 고객 손실 | 제품 가치 |
|---------|---------|---------|
| 개발 후반 문서 소급 작성 | 일정 지연, 설계 변경 재작업, 검토 비용 증가 | 개발 중 문서 증적을 표준 스키마로 누적 |
| 문서 간 수치·용어 불일치 | 보완 요청, 제출 반려, RA/QA 야근 증가 | 추적성 그래프와 가드레일로 제출 전 오류 탐지 |
| 클라우드 업로드 보안 우려 | SaaS 도입 거부, 수동 검토 지속 | 민감 문서는 로컬 처리, 클라우드는 공개 지식팩만 공급 |
| 규제 변경 추적 수동화 | 중요 변경 누락, 대응 지연 | 변경 알림, 제품군 매핑, 영향도 검토 큐 생성 |
| 초기 품질시스템 부재 | 스타트업 인허가 준비 체계 미흡 | 셀프서비스 온보딩과 표준 템플릿 제공 |

---

## 4. 제품/서비스 정의

### 4.1 시스템 아키텍처 (3레이어)

| 레이어 | 배치 위치 | 핵심 구성요소 | 초기 구현 범위 |
|--------|---------|-----------|-------------|
| **Cloud Control Plane** | 공급자 클라우드 (Azure/AWS) | 규제 크롤러, 정규화 파이프라인, PostgreSQL/pgvector, S3 Archive, EventBridge/SQS/SNS | FDA/MFDS/EU MDR 크롤러 우선 |
| **Secure Sync Layer** | 클라우드 ↔ 고객사 경계 | 서명된 지식팩, 증분 매니페스트, 아웃바운드 HTTPS | 테넌트 격리, 버전 관리 |
| **Customer Local Runtime** | 고객사 내부망 | Docker 에이전트, n8n, FastAPI, SQLite/Postgres, Vector Store, Ollama/vLLM, Web UI | Docker Compose 패키지, 파서, Review Workspace, Impact Analyzer 포함 |

**데이터 경계:** 고객 문서 원문·설계치·임상 원자료는 Customer Local Runtime에서만 처리. Cloud Control Plane에는 공개 규제 지식만 저장.

### 4.2 핵심 차별점

1. **데이터 주권** — 설계치, 원본 기술문서, 소스코드, 임상 원자료는 외부 전송 대상에서 제외
2. **표준화** — 고객 양식 무제한 커스터마이징을 지양하고 Unified Schema로 정규화
3. **추적성** — 위험관리 통제수단, SRS, IFU 경고문, 시험증적 간 연결을 그래프로 관리
4. **반복 수익** — 컨설팅 산출물이 아니라 클라우드 지식팩/로컬 에이전트 라이선스로 운영

---

## 5. 타깃 세그먼트와 초기 품목군

| 세그먼트 | 구매 동기 | 우선 제안 메시지 | 판매 난이도 |
|---------|---------|--------------|-----------|
| 의료기기 스타트업 CTO/대표 | 개발 초기 문서 체계 부재, 인허가 일정 압박 | 개발 중 증적 생성과 제출 전 오류 차단 | 중간 |
| RA/QA 실무자 | IFU/SRS/RMS/시험서 간 수동 대조 부담 | 반복 검증 업무 자동화와 근거 링크 확보 | 낮음~중간 |
| 중견 의료기기 기업 품질책임자 | 내부망 보안 정책, 감사 추적성 요구 | 로컬 배포, 감사로그, 관리자 통제 | 중간~높음 |
| 컨설팅/시험기관 파트너 | 반복 문서 검토 효율화, 고객 온보딩 도구 필요 | 표준 패키지 기반 서비스 효율화 | 중간 |

**1차 품목군:** X-ray 시스템, 디지털 디텍터, 촬영실 SW/PACS, 피부미용 초음파  
**선정 이유:** 하드웨어·소프트웨어·전기안전·사용적합성·라벨링·위험관리 문서가 결합되어 추적성 자동화 효과가 크다  
**제외 범위:** IVD 전 품목, 치과용 전 품목, 임상시험 데이터 원자료 분석, 해외 제출 대행 서비스

---

## 6. 수익 모델과 가격 정책

| 플랜 | 가격 | 대상 | 구성 | 수익/운영 가정 |
|------|------|------|------|-------------|
| **Core SaaS** | 월 $299 | 스타트업/초기팀 | 규제 변경 알림, 기본 지식팩, 표준 스키마 템플릿, 제한된 문서 검토 | 낮은 CAC, 셀프 온보딩 중심 |
| **Advanced Hybrid** | 연 $12,000 | 중견/내부망 기업 | 로컬 Docker 에이전트, 정합성 가드레일, 관리자 대시보드, 감사로그 | 고객당 지원비 관리 필요 |
| **Setup & Enablement** | 별도 견적 | 초기 배포 고객 | 고객 환경 점검, 로컬 설치, 초기 문서 스키마 정리, 교육 | 반복 판매보다 초기 도입 장벽 해소용 |
| **Regulatory Pack Add-on** | 제품군/국가별 과금 | 확장 고객 | 추가 품목군·국가별 규제 지식팩 | 제품군 확장 후 업셀링 |

**가격 현실성:**
- 월 $299 플랜은 실제 문서 대행이 아니라 셀프서비스 지식팩/템플릿/알림 중심이어야 손익이 맞는다
- 연 $12,000 플랜은 로컬 배포와 정합성 검사를 포함하되, 고객별 양식 커스터마이징을 제한해야 한다
- 초기 PoC에서는 셋업 비용을 별도 산정하여 무상 컨설팅으로 변질되는 것을 방지한다

---

## 7. Go-To-Market 및 실행 로드맵

| 단계 | 기간(가정) | 목표 | 핵심 산출물 | 성공 기준 |
|------|----------|------|-----------|---------|
| **Phase 1 Infra** | 0~8주 | 클라우드 지식 수집/저장/동기화 PoC | 크롤러, 원문 저장소, 지식팩 버전, 웹훅 알림 | 3개 기관 소스 자동 수집 및 변경 감지 |
| **Phase 2 Logic** | 8~16주 | 초기 품목군 스키마와 파서 튜닝 | Unified Schema v0.9, DOCX/XLSX 파서, 수동 보정 UI | 핵심 필드 85%+ 목표 검증 |
| **Phase 3 Product** | 16~28주 | 로컬 런타임/검토 워크스페이스 제품화 | Docker 패키지, Review UI, Traceability Graph | 파일럿 고객 2~3곳 현장 검증 |
| **Phase 4 Scale** | 28주~ | 품목/국가/파트너 확장 | Add-on 지식팩, 파트너 운영 메뉴얼 | 유료 전환 및 재사용률 확보 |

---

## 8. 재무 가정과 손익분기점

> **기준일:** 2026-06-05 | **출처:** shared-facts.md 기준 가격 × 시장 가정 시나리오

초기 재무 가정은 인프라 비용보다 **인건비, 고객 온보딩, 품목별 지식팩 유지보수**가 비용의 대부분을 차지한다는 관점으로 설정.

### 8.1 가격 전제 (출처: shared-facts.md)

| 플랜 | 가격 | ARR 기여 (고객당) |
|------|------|----------------|
| Core SaaS | 월 $299 = 연 $3,588 | $3,588/고객 |
| Advanced Hybrid | 연 $12,000 | $12,000/고객 |
| Regulatory Pack Add-on | 연 $3,000~5,000 (추정) | 업셀 기여 |

### 8.2 3개 시나리오 ARR 예측

| 시나리오 | Y1 가정 | Y1 ARR | Y2 가정 | Y2 ARR | Y3 가정 | Y3 ARR |
|---------|--------|--------|--------|--------|--------|--------|
| **보수 (Conservative)** | Core 10개, Advanced 1개 | $47,880 | Core 25개, Advanced 3개 | $125,700 | Core 50개, Advanced 6개 | $251,400 |
| **기준 (Base)** | Core 20개, Advanced 3개 | $107,760 | Core 50개, Advanced 8개 | $275,400 | Core 100개, Advanced 18개 | $574,800 |
| **낙관 (Optimistic)** | Core 40개, Advanced 6개 | $215,520 | Core 100개, Advanced 15개 | $538,800 | Core 200개, Advanced 35개 | $1,137,600 |

### 8.3 비용 구조 가정

| 비용 항목 | 월 고정비 (Y1 기준) | 비고 |
|---------|---------------|------|
| 클라우드 인프라 (AWS/Azure) | $150~400 | RDS/pgvector/S3/Lambda 기준 |
| 핵심 개발 인력 (2~4명) | $8,000~15,000 | 한국 기준 공동창업자 포함 |
| RA 자문/외부 전문가 | $1,000~3,000 | 파트타임 기준 |
| 합계 | $9,150~18,400/월 | |

### 8.4 손익분기점 (BEP)

| 시나리오 | BEP 조건 | BEP 도달 시점 |
|---------|---------|-------------|
| 보수 | Advanced 8개 또는 Core 120개 | Y2 후반 |
| 기준 | Advanced 5개 또는 Core 80개 | Y2 중반 |
| 낙관 | Advanced 3개 또는 Core 50개 | Y1 후반 |

**Gross Margin 목표:** 셀프서비스 성숙 후 75%+. 초기 고지원 단계는 50~65%.

**주요 리스크:** 기준/낙관 시나리오는 영업·파트너십 채널 확보를 전제. 파일럿 전환율 50% 이상 달성 필요.

---

## 9. 팀 및 조직

> **구조 완성, 내용 미기재** — 창업자 실명·경력은 투자 제안 단계에서 추가 예정. 현재 역할 구조만 확정.

| 역할 | 핵심 요구 역량 | 채용 시점 | 담당 예정 내용 |
|------|-------------|---------|-------------|
| **CEO/제품 총괄** | 의료기기 산업 이해, 사업화 경험 | 창업 시 | 전략·파트너십·고객 개발 |
| **CTO/AI 엔지니어** | LLM/NLP, Python, 로컬 런타임 배포 | 창업 시 | 파서·RAG·Docker 패키지 |
| **RA/도메인 전문가** | FDA/MFDS/EU MDR 실무 경험 | Y1 초기 | 지식팩 정확성, 고객 온보딩 가이드 |
| **백엔드/DevOps** | FastAPI, PostgreSQL, AWS/Azure | Y1 | Cloud Control Plane, Sync Layer |
| **프론트엔드** | React 또는 Vue, UX | Y1 중반 | Review Workspace, Admin UI |

**창업자 프로필:** `[기재 필요]` — 의료기기/RA/SaaS 관련 경험 기재 예정

**어드바이저 (목표 2~3명):**

| 역할 | 전문 분야 | 현황 |
|------|---------|------|
| 규제 어드바이저 1 | FDA/MFDS 제출 경험 | `[기재 필요]` |
| 규제 어드바이저 2 | EU MDR / CE 마킹 | `[기재 필요]` |
| 기술 어드바이저 | 의료 AI/NLP | `[기재 필요]` |

---

## 10. 시장 규모 (TAM/SAM/SOM)

> **기준일:** 2026-06-05 | **출처:** shared-facts.md — BizPlan §8과 동일 수치 사용 (출처: shared-facts.md)

### TAM — 글로벌 의료기기 규제 관련 소프트웨어 시장

| 구분 | 규모 | CAGR | 비고 |
|------|------|------|------|
| TAM (글로벌 의료기기 QMS/RA 소프트웨어) | $6.75B (2024) → $11.66B (2030) | 9.55% (2025~2030) | 출처: Grand View Research, MarketsandMarkets |
| SAM (SaaS+하이브리드 배포 가능 세그먼트) | ~$3.5B | — | TAM의 약 50% 추정 (하이브리드 배포 가능 중소형 고객사) |
| SOM Y1 (한국+미국 스타트업/중견, 초기 품목군) | $12M~18M | — | Advanced 10개 + Core 50개 시나리오 기준 |
| SOM Y3 (확장 후) | $50M~80M | — | Advanced 30개 + Core 300개 시나리오 기준 |

### 시장 선택 근거

- 의료기기 규제 요건 강화 (FDA 510(k), EU MDR 전환 진행 중) → 문서 자동화 수요 증가
- 하이브리드 AI 도구 도입 의지: 클라우드 전면 전환 불가 기업 증가
- 초기 집중 품목군 (X-ray/디텍터/촬영실 SW/피부미용 초음파): 규제 문서 구조 반복성 높음

**Sources:**
- [Grand View Research - Medical Device Regulatory Affairs Market, 2030](https://www.grandviewresearch.com/industry-analysis/medical-device-regulatory-affairs-market)
- [MarketsandMarkets - Medical Device Regulatory Affairs Market Size & Growth Forecast 2025](https://www.strategicmarketresearch.com/market-report/medical-device-regulatory-affairs-market)

---

## 11. 경쟁 분석

> **기준일:** 2026-06-05 | **출처:** shared-facts.md 기준 벤더 목록 및 분석

### 주요 경쟁 벤더 비교

| 벤더 | 주요 기능 | 가격대 | 타깃 | 약점 | 본 제품 포지션 |
|------|---------|------|------|------|------------|
| **Veeva Vault Quality** | eQMS, 문서 관리, CAPA, 규제 제출 지원 | 엔터프라이즈 (연 $50K+) | 대형 제약/의료기기 | 고비용·장기 도입, 클라우드 전용, AI 지식팩 약함 | 초기 품목군 특화 경량 하이브리드 |
| **Sparta Systems TrackWise** | QMS, 통합 컴플라이언스 관리 | 엔터프라이즈 | 대형 제조사 | 커스터마이징 비용 높음, AI 자동화 부족 | 셀프서비스 + 자동 규제 지식 연동 |
| **MasterControl** | QMS/DMS, 문서 제어, 교육 관리 | 중견-대형 ($20K+/년) | 의료기기·제약 | 온프레미스 복잡, SaaS 이전 지연 | 로컬 런타임 우선 + AI 보조 |
| **Qara (구 Greenlight Guru)** | 의료기기 특화 QMS, Design Control | 중소형-중견 ($12K~30K/년) | 의료기기 스타트업 | 규제 지식팩 없음, 문서 AI 약함 | AI 규제 지식 연동 차별화 |
| **전통 RA 컨설팅** | 전문가 판단, 제출 경험 | 프로젝트당 $5K~50K | 전 규모 | 비용 높고 지식 내재화 안됨 | 컨설팅 보조/표준화 운영 플랫폼 |

### 포지셔닝 매트릭스

| 구분 | 규제 특화 지식 | 하이브리드(로컬) 배포 | 가격 접근성 | AI 자동화 |
|------|------------|-----------------|-----------|--------|
| **본 제품** | ★★★★★ | ★★★★★ | ★★★★☆ | ★★★★☆ |
| Veeva Vault | ★★★★☆ | ★★☆☆☆ (클라우드 중심) | ★★☆☆☆ | ★★★☆☆ |
| MasterControl | ★★★★☆ | ★★★☆☆ | ★★★☆☆ | ★★☆☆☆ |
| Qara | ★★★★☆ | ★★☆☆☆ | ★★★★☆ | ★★★☆☆ |

**핵심 차별점:** 하이브리드 배포(Data Sovereignty) + 규제 지식팩 자동 동기화 + 초기 품목군 특화 경량 도구.

Sources:
- [IntuitionLabs - GxP Compliance Software eQMS Platform Comparison 2026](https://intuitionlabs.ai/articles/gxp-compliance-software-eqms-comparison-2026)
- [G2 - Veeva Vault QMS Reviews 2026](https://www.g2.com/products/veeva-vault-qms/reviews)
- [Capterra - TrackWise Digital vs Vault Quality Suite 2025](https://www.capterra.com/quality-management-software/compare/175662-178567/Trackwise-Digital-vs-Vault-Quality-Suite)

---

## 12. 리스크와 대응 전략

| 리스크 | 영향 | 대응 | 소유자 |
|--------|------|------|--------|
| 규제 원문 구조 변화 | 크롤러 오류, 변경 누락 | 소스별 파서 버전관리, 실패 알림, 수동 검수 큐 | Cloud Lead |
| 고객 문서 편차 | 파싱 정확도 저하 | 표준 스키마 강제, 수동 보정 UI, 샘플 문서 기반 튜닝 | Product/RA |
| AI 환각/부정확 답변 | 신뢰도 저하, 법적 리스크 | 근거 링크 필수, confidence 표시, 승인 워크플로 | AI Lead |
| 로컬 배포 복잡성 | 도입 지연 | Docker compose, 체크리스트, 헬스체크, 오프라인 설치 가이드 | DevOps |
| 컨설팅화 | 마진 악화 | 고객별 양식 대행 금지, 셋업 별도 과금, 제품군 템플릿 재사용 | CEO/Product |
| 규제 책임 오해 | 고객 클레임 | 면책/역할 명시, RA 전문가 검토 단계 필수화 | Legal/QA |

---

## 13. 의사결정 권고

1. MVP는 "지식팩 수집/동기화 + 로컬 문서 정규화 + 정합성 가드레일 + 검토 대시보드"까지로 제한한다
2. 첫 파일럿은 최소한 IFU/SRS/위험관리 문서를 보유하고 개선 의지가 있는 고객을 선택한다
3. 규제 대행/컨설팅을 매출로 끌어오더라도 제품 내재화 가능한 패턴만 채택한다
4. 데이터 보안과 근거 추적성을 판매 메시지의 1순위로 둔다
5. 고객별 양식 무제한 커스터마이징을 지양하고 Unified Schema로 수렴시킨다

---

## 참고 근거 및 출처

> 실제 제출 문서 작성 시에는 해당 기관의 최신 원문과 국내 공식 번역본/고시를 재확인해야 합니다.

1. [FDA, Overview of Device Regulation](https://www.fda.gov/medical-devices/device-advice-comprehensive-regulatory-assistance/overview-device-regulation)
2. [FDA, Cybersecurity in Medical Devices: QMS Considerations and Premarket Submissions](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cybersecurity-medical-devices-quality-management-system-considerations-and-content-premarket)
3. [EUR-Lex, Regulation (EU) 2017/745 on medical devices](https://eur-lex.europa.eu/eli/reg/2017/745/oj/eng)
4. [European Commission, Medical Devices Sector / EUDAMED](https://health.ec.europa.eu/medical-devices-sector_en)
5. [MFDS, Medical Device Regulations / Enforcement Rule resources](https://www.mfds.go.kr/eng/brd/m_40/list.do)
6. [AWS, Amazon S3 Glacier storage classes](https://aws.amazon.com/s3/storage-classes/glacier/)
7. [AWS, S3 Lifecycle transition documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-transition-general-considerations.html)
8. [AWS, AWS Budgets cost notifications](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)
9. [pgvector, open-source vector similarity search for PostgreSQL](https://github.com/pgvector/pgvector)

---

*버전: v3.0 | 갭 트래커: [SPEC-DOC-001](.moai/specs/SPEC-DOC-001/spec.md)*
