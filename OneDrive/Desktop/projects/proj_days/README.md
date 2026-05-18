# AI 일기 QnA 웹 애플리케이션

AWS 위에 구축된 5문답 기반 AI 일기 자동 생성 풀스택 웹 애플리케이션.

## 기술 스택

- **Backend**: FastAPI (Python 3.11+) + SQLAlchemy 2.x + Alembic + PostgreSQL 16
- **Frontend**: React 18 + Vite + TypeScript + FullCalendar
- **AI**: AWS Bedrock (`us.anthropic.claude-sonnet-4-6`)
- **Infra**: Terraform (AWS VPC + EC2 + RDS)

---

## ⚠️ OneDrive 동기화 주의사항

이 프로젝트는 OneDrive 동기화 폴더(`C:/Users/.../OneDrive/Desktop/projects/proj_days/`) 안에 있습니다.

**Terraform 명령 실행 전 반드시 다음 중 하나를 수행하세요:**

1. **OneDrive 동기화 일시 중지**: 시스템 트레이 → OneDrive 아이콘 우클릭 → "동기화 일시 중지"
2. **또는** `infra/` 폴더를 OneDrive 제외 폴더로 지정

> **이유**: OneDrive가 `terraform.tfstate` 파일을 잠그면 `terraform apply/destroy` 명령이 실패합니다.
> 과거 이 문제로 작업이 중단된 사례가 있습니다.

---

## 로컬 개발 기동 순서

### 사전 요건

- Python 3.11+
- Node.js 20+
- Docker (통합 테스트용 testcontainers)
- Terraform 1.6+
- AWS CLI + 자격증명 (us-east-1)

### 1. 환경 변수 설정

```bash
cp backend/.env.example backend/.env
# .env 파일을 열어 실제 값 입력
```

### 2. 로컬 DB 기동 (Docker)

```bash
docker compose -f docker-compose.dev.yml up -d
```

### 3. 백엔드

```bash
cd backend
python3.11 -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/alembic upgrade head
.venv/Scripts/uvicorn app.main:app --reload
```

### 4. 프론트엔드

```bash
cd frontend
npm ci
npm run dev
```

브라우저: `http://localhost:5173` → 비밀번호: `inha-nxt`

---

## 테스트 실행

```powershell
# 백엔드
cd backend; .venv/Scripts/pytest -v --tb=short

# 프론트엔드
cd frontend; npm test -- --run

# Terraform
terraform -chdir=infra fmt -check -recursive
terraform -chdir=infra validate
terraform -chdir=infra test
```

---

## AWS 배포

```bash
# terraform.tfvars 작성 후
terraform -chdir=infra apply
```

자세한 내용은 `Task-1.md` 참조.
