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

### Vercel (regula.abyz-lab.work 도메인 바인딩용) — 미설정, 추가 필요

| Secret 키 | 용도 | 취득 방법 |
|-----------|------|----------|
| `VERCEL_TOKEN` | Vercel API 인증 토큰 | Vercel 대시보드 → Settings → Tokens → Create |
| `VERCEL_PROJECT_ID` | ra-med-bot Vercel 프로젝트 ID | Vercel 대시보드 → ra-med-bot 프로젝트 → Settings → General → Project ID |

```bash
# 설정 명령 (gh CLI 사용)
gh secret set VERCEL_TOKEN --repo holee9/hybrid-ra-saas
gh secret set VERCEL_PROJECT_ID --repo holee9/hybrid-ra-saas
```

> **참고**: ra-med-bot(holee9/ra-med-bot) 레포에도 동일한 `VERCEL_TOKEN`, `VERCEL_PROJECT_ID`가 설정되어 있음.  
> Vercel 대시보드에서 값을 확인하거나 ra-med-bot에서 사용 중인 동일한 값을 입력.

---

## regula.abyz-lab.work 도메인 설정 절차

Secrets 추가 후 아래 순서대로 진행한다.

### 1단계 — Secrets 추가 (위 명령 실행)

```bash
gh secret set CLOUDFLARE_API_TOKEN --repo holee9/hybrid-ra-saas
gh secret set CLOUDFLARE_ZONE_ID --repo holee9/hybrid-ra-saas
gh secret set VERCEL_TOKEN --repo holee9/hybrid-ra-saas
gh secret set VERCEL_PROJECT_ID --repo holee9/hybrid-ra-saas
```

### 2단계 — 워크플로우 실행

GitHub Actions → **`setup-regula-domain.yml`** → "Run workflow"  
`dry_run: false` 선택 후 실행

워크플로우가 자동으로 처리하는 내용:
- Cloudflare DNS: `regula.abyz-lab.work` CNAME → `cname.vercel-dns.com`
- Vercel: `regula.abyz-lab.work` 도메인 바인딩
- Vercel: `NEXTAUTH_URL=https://regula.abyz-lab.work` 환경변수 업데이트

### 3단계 — Vercel 검증 및 재배포

1. Vercel 대시보드 → ra-med-bot → Domains → `regula.abyz-lab.work` 상태 "Valid" 확인
2. Deployments → 최신 배포 → Redeploy (NEXTAUTH_URL 환경변수 적용)

### 4단계 — E2E 확인

```
https://regula.abyz-lab.work  →  Regula 로그인 화면 표시
https://regula.abyz-lab.work/api/health  →  {"status":"ok"} 응답
```

---

## ra.abyz-lab.work 도메인 설정 (엔터프라이즈 API용, 선택)

Customer Runtime API(`api-prod`) 외부 테스트용 도메인.  
`domain-setup.yml` 워크플로우 실행 — Azure OIDC 권한 필요.

> **운영 용도 아님**: 엔터프라이즈 고객은 Docker Compose로 로컬 배포하므로 외부 도메인 불필요.

---

## 보안 참고사항

- `CLOUDFLARE_API_TOKEN`: **Zone DNS Edit** 권한만 부여 (전체 계정 편집 권한 불필요)
- `VERCEL_TOKEN`: 만료 기간 설정 권장 (90일)
- 모든 Secrets는 GitHub의 암호화된 시크릿 저장소에 보관, 로그에 노출되지 않음
- `TF_VAR_*` 시크릿은 Terraform state에만 사용, 소스코드에 절대 하드코딩 금지
