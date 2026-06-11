# Hybrid RA — Customer Local Runtime 설치 가이드

## 시스템 요구사항

| 항목 | 최소 사양 |
|------|----------|
| OS | Linux, macOS, Windows (WSL2) |
| Docker | 24.0 이상 |
| Docker Compose | v2.0 이상 (`docker compose` 또는 `docker-compose`) |
| RAM | 8GB 이상 (Ollama 모델 실행 시 16GB 권장) |
| Disk | 20GB 이상 (Ollama 모델 포함) |

## 설치

### 1. 소스 다운로드

```bash
git clone https://github.com/holee9/hybrid-ra-saas.git
cd hybrid-ra-saas/customer-runtime
```

또는 zip 다운로드 후 압축 해제.

### 2. 환경 설정

```bash
./setup.sh
```

또는 수동 설정:

```bash
cp .env.example .env
# .env 파일 편집: JWT_SECRET, DB_PASSWORD, CLOUD_SYNC_ENDPOINT 등 설정
```

**필수 설정값:**

| 변수 | 설명 |
|------|------|
| `JWT_SECRET` | 최소 32자 랜덤 문자열. `openssl rand -hex 32` 로 생성 |
| `DB_PASSWORD` | PostgreSQL 비밀번호 |
| `CLOUD_SYNC_ENDPOINT` | Hybrid RA 클라우드 API URL |
| `ORG` | 조직 식별자 |

### 3. 서비스 시작

```bash
make up
# 또는: docker-compose up -d
```

### 4. Ollama 모델 다운로드 (최초 1회)

```bash
make pull-model
# 약 5GB 다운로드. 완료까지 수분 소요.
```

### 5. 동작 확인

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

UI: http://localhost:8080

## 주요 명령어

| 명령 | 설명 |
|------|------|
| `make up` | 모든 서비스 시작 |
| `make down` | 모든 서비스 중지 |
| `make logs` | 로그 스트리밍 |
| `make status` | 서비스 상태 확인 |
| `make clean` | 서비스 중지 + 볼륨 삭제 (데이터 초기화) |

## 아키텍처

```
Customer 환경 (로컬)                    Hybrid RA Cloud
┌──────────────────────────────────┐    ┌──────────────────────┐
│  UI (:8080)                      │    │                      │
│  API (:8000) ─────────────────────────▶  Cloud API           │
│  PostgreSQL (:5432)              │    │  (규정 문서 동기화)   │
│  MinIO (:9000)                   │    │                      │
│  Ollama (:11434)                 │    └──────────────────────┘
└──────────────────────────────────┘
```

- **API**: RA 문서 파싱, 필드 추출, 검수 워크플로우
- **PostgreSQL**: 문서 메타데이터, 작업 이력
- **MinIO**: 원본 문서 파일 저장
- **Ollama**: 로컬 LLM (llama3.1:8b)
- **Cloud Sync**: 최신 규정 문서 동기화

## 문제 해결

### 서비스가 시작하지 않는 경우

```bash
docker-compose logs api
docker-compose logs postgres
```

### Ollama 모델이 없는 경우

```bash
docker-compose exec ollama ollama list  # 설치된 모델 확인
make pull-model                          # 모델 다운로드
```

### API에 접근 불가

```bash
make status  # 컨테이너 상태 확인
curl http://localhost:8000/health
```
