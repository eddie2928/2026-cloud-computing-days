# AI 일기 QnA 웹 애플리케이션

AI가 하루에 5가지 질문을 던지고, 답변을 바탕으로 일기를 자동 생성하는 AWS 풀스택 웹앱.

---

## 동작 방식

```
브라우저 → nginx (EC2) → FastAPI → Anthropic Claude API
                                 → RDS PostgreSQL
```

| 구성 | 스펙 |
|------|------|
| EC2 | t3.small · Amazon Linux 2023 · 20 GB |
| RDS | PostgreSQL 16 · db.t3.micro |
| AI  | Anthropic API `claude-sonnet-4-6` |
| Backend | FastAPI + SQLAlchemy (async) + Alembic |
| Frontend | React 18 + Vite + TypeScript + FullCalendar |

---

## 사전 준비

**필수 도구**

| 도구 | 버전 |
|------|------|
| AWS CLI | 2.x — `~/.aws/credentials` 설정 완료 |
| Terraform | 1.6+ |

자격증명 확인:
```bash
aws sts get-caller-identity
```

**OneDrive 동기화 중지 (Windows)**

프로젝트가 OneDrive 폴더 안에 있으면, `terraform.tfstate`가 잠겨 apply/destroy가 실패합니다.  
Terraform 명령 전에 반드시 동기화를 일시 중지하세요.

> 시스템 트레이 → OneDrive 아이콘 우클릭 → "동기화 일시 중지"

---

## 배포 (3단계)

### 1. tfvars 작성

`infra/terraform.tfvars` 파일 생성 (`.gitignore`에 포함되어 커밋되지 않음):

```hcl
db_password    = "강력한_DB_비밀번호"
session_secret = "64자_이상_랜덤_문자열"
git_repo_url   = "https://github.com/55002ghals/2026-cloud-computing-days.git"
git_branch     = "master"
```

랜덤 문자열 생성:
```bash
# Linux/Mac
openssl rand -base64 32

# PowerShell
[System.Web.Security.Membership]::GeneratePassword(32, 4)
```

> `app_password` 미지정 시 기본값 `inha-nxt` 사용.

### 2. 배포

```bash
terraform -chdir=infra init
terraform -chdir=infra apply   # "yes" 입력 → 약 8~12분 소요
```

완료 후 출력:
```
app_url       = "http://x.x.x.x"
ssh_command   = "ssh -i infra/qna-diary.pem ec2-user@x.x.x.x"
```

### 3. 부트스트랩 완료 대기 (약 3~5분)

EC2가 뜬 뒤 자동으로 진행됩니다: 패키지 설치 → 코드 클론 → 빌드 → DB 마이그레이션 → 서비스 시작

완료 확인:
```bash
curl http://<EC2_PUBLIC_IP>/api/health
# {"status": "ok"} 응답 시 준비 완료
```

진행 상황 확인 (SSH):
```bash
ssh -i infra/qna-diary.pem ec2-user@<EC2_PUBLIC_IP>
sudo tail -f /var/log/user-data.log
```

---

## 사용법

브라우저에서 `http://<EC2_PUBLIC_IP>` 접속

1. **로그인** — 비밀번호: `inha-nxt` (또는 tfvars에서 설정한 값)
2. **오늘의 일기 작성** — 사이드바에서 선택 → AI 질문 5개에 답변 → 일기 자동 생성
3. **캘린더** — 사이드바에서 선택 → 날짜별 일기 조회

---

## 리소스 삭제

> RDS 데이터를 포함한 **모든 AWS 리소스가 영구 삭제**됩니다.

```bash
terraform -chdir=infra destroy   # "yes" 입력 → 약 8~12분 소요
```

삭제 후 AWS 콘솔에서 잔여 리소스 확인:
- EC2 → Instances
- RDS → Databases
- VPC → Your VPCs (`qna-diary-vpc` 없어야 함)

---

## 로컬 개발

**백엔드**

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

**프론트엔드** (Node.js 20+ 필요)

```bash
cd frontend
npm ci
npm run dev
# → http://localhost:5173
```

**테스트**

```bash
cd backend && .venv/Scripts/pytest -v --tb=short
cd frontend && npm test -- --run
terraform -chdir=infra validate
```
