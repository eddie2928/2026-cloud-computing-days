# AI 일기 QnA 웹 애플리케이션

AWS 위에 구축된 5문답 기반 AI 일기 자동 생성 풀스택 웹 애플리케이션.

## 아키텍처

```
Browser
  │
  ▼ HTTP:80
[ EC2 (AL2023) ]
  ├─ nginx (reverse proxy)
  ├─ FastAPI / uvicorn :8000
  └─ AWS Bedrock (Claude Sonnet) ─► AI 질문/일기 생성
         │
         ▼ :5432
[ RDS PostgreSQL 16 ]
```

- **Backend**: FastAPI (Python 3.11) + SQLAlchemy 2.x async + Alembic
- **Frontend**: React 18 + Vite + TypeScript + FullCalendar
- **AI**: AWS Bedrock (`us.anthropic.claude-sonnet-4-6`)
- **Infra**: Terraform — VPC + EC2 (t3.small) + RDS PostgreSQL (db.t3.micro)

---

## 사전 요건

| 도구 | 버전 |
|------|------|
| AWS CLI | 2.x (자격증명 `~/.aws/credentials` 설정 완료) |
| Terraform | 1.6 이상 |
| Python | 3.11 이상 (로컬 개발 시) |
| Node.js | 20 이상 (로컬 개발 시) |
| Git | 2.x |

AWS CLI 자격증명 확인:
```bash
aws sts get-caller-identity
```

---

## ⚠️ OneDrive 동기화 주의사항

이 프로젝트 디렉토리가 OneDrive 동기화 폴더 안에 있다면, Terraform 명령 실행 전
**반드시 OneDrive 동기화를 일시 중지**하세요.

> 이유: OneDrive가 `terraform.tfstate` 파일을 잠그면 `apply/destroy`가 실패합니다.

시스템 트레이 → OneDrive 아이콘 우클릭 → "동기화 일시 중지"

---

## 1. 인프라 배포 (Terraform)

### 1-1. terraform.tfvars 작성

`infra/` 폴더에 `terraform.tfvars` 파일을 생성합니다 (이 파일은 `.gitignore`에 포함되어 커밋되지 않습니다).

```hcl
# infra/terraform.tfvars

db_password    = "<강력한 DB 비밀번호>"
session_secret = "<64자 이상 랜덤 문자열>"
git_repo_url   = "https://github.com/55002ghals/2026-cloud-computing-days.git"
git_branch     = "main"
```

비밀번호 생성 예시:
```bash
# Linux/Mac
openssl rand -base64 32

# PowerShell
[System.Web.Security.Membership]::GeneratePassword(32, 4)
```

> `app_password`를 지정하지 않으면 기본값 `inha-nxt`가 사용됩니다.

### 1-2. Terraform 초기화

```bash
terraform -chdir=infra init
```

### 1-3. 배포 계획 확인 (선택)

```bash
terraform -chdir=infra plan
```

약 20개 리소스가 생성됩니다:
- VPC, 서브넷, IGW, 라우팅 테이블
- EC2 보안 그룹 (HTTP 80 전체 허용, SSH 22 전체 허용)
- RDS 보안 그룹 (PostgreSQL 5432, EC2에서만 허용)
- RDS PostgreSQL 인스턴스 (db.t3.micro, 20GiB)
- EC2 인스턴스 (t3.small, AL2023)
- RSA 4096 SSH 키페어 → `infra/qna-diary.pem` 로컬 저장

### 1-4. 배포 실행

```bash
terraform -chdir=infra apply
```

`yes` 입력 후 약 **5~10분** 소요됩니다.

완료 후 출력 예시:
```
app_url        = "http://54.210.210.180"
ec2_public_ip  = "54.210.210.180"
rds_endpoint   = "qna-diary-postgres.xxxx.us-east-1.rds.amazonaws.com"
ssh_command    = "ssh -i infra/qna-diary.pem ec2-user@54.210.210.180"
```

### 1-5. EC2 부트스트랩 완료 대기

EC2 인스턴스가 시작된 후 자동으로 다음 작업이 수행됩니다 (약 **3~5분** 추가 소요):
- 시스템 패키지 설치 (`python3.11`, `nginx`, `nodejs`, `postgresql15`)
- git clone → Python venv + `pip install` → `npm ci && npm run build`
- Alembic DB 마이그레이션
- nginx + FastAPI systemd 서비스 시작

부트스트랩 완료 확인:
```bash
# 헬스체크 엔드포인트 (HTTP 200 응답 시 준비 완료)
curl http://<EC2_PUBLIC_IP>/api/health

# EC2에 SSH 접속하여 로그 확인
ssh -i infra/qna-diary.pem ec2-user@<EC2_PUBLIC_IP>
sudo tail -f /var/log/user-data.log
```

### 1-6. SSH 키 권한 설정 (Linux/Mac)

```bash
chmod 600 infra/qna-diary.pem
```

> Windows에서는 파일 속성 → 보안 → 고급에서 현재 사용자만 접근 허용으로 설정하거나,
> PowerShell에서 `icacls infra\qna-diary.pem /inheritance:r /grant:r "$env:USERNAME:(R)"` 실행

---

## 2. PoC (서비스 검증)

브라우저에서 `http://<EC2_PUBLIC_IP>` 접속

### 2-1. 로그인

- 비밀번호: `inha-nxt` (또는 `terraform.tfvars`에서 설정한 `app_password`)

### 2-2. AI 일기 QnA 세션

1. 사이드바에서 **"오늘의 일기 작성"** 클릭
2. AI가 오늘 하루에 관한 질문을 5개 순서대로 제시
3. 각 질문에 답변 입력 → **전송** (또는 Enter 키)
4. 5번째 답변 완료 시 AI가 일기를 자동 생성

### 2-3. 캘린더 확인

- 사이드바에서 **"캘린더"** 클릭
- 일기가 작성된 날짜에 **"일기 확인"** 버튼 표시
- 버튼 클릭 시 해당 날짜의 일기 내용 조회

### 2-4. API 헬스체크

```bash
curl http://<EC2_PUBLIC_IP>/api/health
# → {"status": "ok"}

curl http://<EC2_PUBLIC_IP>/api/diary/calendar?year=2026&month=5 \
  -H "Cookie: session=<your_session_cookie>"
```

---

## 3. 인프라 삭제 (Teardown)

> **주의**: 아래 명령은 EC2, RDS, VPC 등 생성한 **모든 AWS 리소스를 영구 삭제**합니다.
> RDS 데이터는 복구할 수 없습니다.

```bash
terraform -chdir=infra destroy
```

`yes` 입력 후 약 **5~10분** 소요됩니다.

삭제 후 AWS 콘솔에서 잔여 리소스가 없는지 확인하세요:
- EC2 → Instances
- RDS → Databases
- VPC → Your VPCs (`qna-diary-vpc` 없어야 함)

---

## 로컬 개발 기동

### 환경 변수 설정

```bash
cp backend/.env.example backend/.env
# .env 파일을 열어 실제 값 입력
```

### 로컬 DB 기동 (Docker)

```bash
docker compose -f docker-compose.dev.yml up -d
```

### 백엔드

```bash
cd backend
python3.11 -m venv .venv
# Windows
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\alembic upgrade head
.venv\Scripts\uvicorn app.main:app --reload
# Linux/Mac
.venv/bin/pip install -r requirements.txt
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload
```

### 프론트엔드

```bash
cd frontend
npm ci
npm run dev
```

브라우저: `http://localhost:5173`

---

## 테스트 실행

```bash
# 백엔드 (pytest)
cd backend && .venv/Scripts/pytest -v --tb=short

# 프론트엔드
cd frontend && npm test -- --run

# Terraform 형식/유효성 검사
terraform -chdir=infra fmt -check -recursive
terraform -chdir=infra validate
```
