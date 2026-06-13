# GitHub Secrets 설정 가이드

이 레포(holee9/hybrid-ra-saas)에 필요한 모든 GitHub Secrets 목록과 설정 방법.

---

## 전체 Secrets 목록

### Azure (인프라 배포용)

| Secret 키 | 용도 | 취득 방법 |
|-----------|------|----------|
| `AZURE_CLIENT_ID` | OIDC 인증 — Service Principal Client ID | Azure Portal → App Registration |
| `AZURE_TENANT_ID` | Azure 테넌트 ID | Azure Portal → Entra ID → Tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure 구독 ID | Azure Portal → Subscriptions |
| `AZURE_RESOURCE_GROUP` | Container App 리소스 그룹명 | `rg-hybrid-ra-saas-staging` |
| `AZURE_CONTAINER_APP_ENV` | Container App Environment 이름 | `cae-hybrid-ra-saas-staging` |
| `AZURE_CONTAINER_REGISTRY` | ACR 로그인 서버 | `acrhybridrasaas.azurecr.io` |
| `TF_VAR_DB_ADMIN_LOGIN` | PostgreSQL 관리자 로그인 | 임의 설정값 (최초 Terraform apply 시 사용한 값) |
| `TF_VAR_DB_ADMIN_PASSWORD` | PostgreSQL 관리자 패스워드 | 임의 설정값 (최초 Terraform apply 시 사용한 값) |

> **현황**: 위 8개는 이미 설정 완료 (2026-06-11 기준)

---

### Cloudflare (DNS 관리용) — 미설정, 추가 필요

| Secret 키 | 용도 | 취득 방법 |
|-----------|------|----------|
| `CLOUDFLARE_API_TOKEN` | DNS 레코드 생성/수정 | Cloudflare 대시보드 → My Profile → API Tokens → Create Token (Zone DNS Edit 권한) |
| `CLOUDFLARE_ZONE_ID` | abyz-lab.work Zone ID | Cloudflare 대시보드 → abyz-lab.work → Overview 우측 하단 Zone ID |

```bash
# 설정 명령 (gh CLI 사용)
gh secret set CLOUDFLARE_API_TOKEN --repo holee9/hybrid-ra-saas
gh secret set CLOUDFLARE_ZONE_ID --repo holee9/hybrid-ra-saas
```

---

### Regula 연동 (hybrid-ra-saas ↔ ra-med-bot)

| Secret 키 | 용도 | 취득/생성 방법 |
|-----------|------|---------------|
| `REGULA_API_KEY` | ra-med-bot → Customer Runtime server-to-server 호출 인증 (`X-Regula-API-Key`) | `openssl rand -hex 32` 등으로 생성 후 양쪽 레포에 동일하게 등록 |
| `REGULA_ALLOWED_TENANTS` | API key 호출 허용 tenant allowlist | 쉼표 구분 tenant ID. Secret이 아니면 Container App env var로 직접 설정 가능 |
| `REGULA_KNOWLEDGE_PUSH_URL` | Cloud Control Plane 크롤 완료 후 ra-med-bot 지식 동기화 수신 URL | ra-med-bot `/api/admin/radar/sync` 배포 URL |
| `CRAWL_PUSH_SECRET` | Cloud Control Plane → ra-med-bot knowledge push 인증 헤더 | `openssl rand -hex 32` 등으로 생성 후 양쪽 레포에 동일하게 등록 |
| `REGULA_AUDIT_WEBHOOK_URL` | Customer Runtime `/audit/webhook` outbound 대상 | ra-med-bot 감사 이벤트 수신 URL |
| `REGULA_IFU_WEBHOOK_URL` | IFU 파싱 완료 후 Regula project context push 대상 | ra-med-bot IFU context 수신 URL |

```bash
gh secret set REGULA_API_KEY --repo holee9/hybrid-ra-saas
gh secret set REGULA_KNOWLEDGE_PUSH_URL --repo holee9/hybrid-ra-saas
gh secret set CRAWL_PUSH_SECRET --repo holee9/hybrid-ra-saas
gh secret set REGULA_AUDIT_WEBHOOK_URL --repo holee9/hybrid-ra-saas
gh secret set REGULA_IFU_WEBHOOK_URL --repo holee9/hybrid-ra-saas
```

> `REGULA_ALLOWED_TENANTS`는 운영 정책 값입니다. 비밀값으로 관리하려면 GitHub Secret/Key Vault에 등록하고, 공개 가능한 tenant ID 목록이면 Container App env var로 직접 설정합니다.

---

## regula.abyz-lab.work 도메인 설정 절차

Secrets 추가 후 아래 순서대로 진행한다.

### 1단계 — Secrets 추가 (위 명령 실행)

```bash
gh secret set CLOUDFLARE_API_TOKEN --repo holee9/hybrid-ra-saas
gh secret set CLOUDFLARE_ZONE_ID --repo holee9/hybrid-ra-saas
```

> Vercel 관련 Secrets는 이 레포에서 불필요합니다.  
> Vercel 도메인 바인딩은 ra-med-bot 레포에서 처리합니다.

### 2단계 — DNS/도메인 설정

현재 이 레포의 실제 workflow는 `ci.yml`, `deploy-staging.yml`, `deploy-prod.yml`, `terraform.yml`입니다.
도메인 자동화 workflow는 현재 이 레포에 없으므로, Cloudflare DNS와 Vercel 도메인 바인딩은 ra-med-bot 레포 또는 수동 운영 절차에서 처리합니다.

필요 DNS:
- Cloudflare DNS: `regula.abyz-lab.work` CNAME → `cname.vercel-dns.com`

### 3단계 — Vercel 측 (ra-med-bot 레포에서 처리)

Vercel 도메인 바인딩은 ra-med-bot 레포의 CI/CD에서 처리합니다.  
이 레포의 워크플로우는 Cloudflare DNS까지만 담당합니다.

### 4단계 — E2E 확인

```
https://regula.abyz-lab.work  →  Regula 로그인 화면 표시
https://regula.abyz-lab.work/api/health  →  {"status":"ok"} 응답
```

---

## ra.abyz-lab.work 도메인 설정 (엔터프라이즈 API용, 선택)

Customer Runtime API(`api-prod`) 외부 테스트용 도메인.  
현재 이 레포에는 엔터프라이즈 API 도메인 바인딩 workflow가 없으므로, 필요 시 Azure Portal/CLI 또는 별도 인프라 workflow로 설정합니다.

> **운영 용도 아님**: 엔터프라이즈 고객은 Docker Compose로 로컬 배포하므로 외부 도메인 불필요.

---

## 보안 참고사항

- `CLOUDFLARE_API_TOKEN`: **Zone DNS Edit** 권한만 부여 (전체 계정 편집 권한 불필요)
- `VERCEL_TOKEN`: 만료 기간 설정 권장 (90일)
- 모든 Secrets는 GitHub의 암호화된 시크릿 저장소에 보관, 로그에 노출되지 않음
- `TF_VAR_*` 시크릿은 Terraform state에만 사용, 소스코드에 절대 하드코딩 금지
