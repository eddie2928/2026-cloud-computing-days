# Task-1: AI 일기 QnA 웹 애플리케이션 인프라 + 코드 + 테스트 자동화

> **상태**: 작성 완료, 사용자 승인 대기 중
> **인코딩**: UTF-8 (BOM 없음)
> **작성일**: 2026-05-18

---

## 1. Goal (목적)

AWS 위에 "AI가 던지는 5개 질문에 답하면 그 답변을 바탕으로 일기를 자동 생성/저장하고 캘린더에서 조회"할 수 있는 풀스택 웹 애플리케이션을 Terraform IaC + FastAPI + React 로 구축한다. 모든 코드는 단위/통합 테스트로 자동 검증되며, 본 Task-1 의 Todo 를 끝까지 수행하면 `terraform apply` 후 브라우저에서 5문답 → 일기 자동 생성 시나리오가 동작한다.

---

## 2. Context (사전 조사 결과)

### 2.1 현재 프로젝트 상태

- `proj_days/` 디렉토리는 사실상 비어 있음 (`infra/` 빈 폴더 + `.claude/settings.local.json` 만 존재).
- 현재 git branch 는 `task-6-dashboard-fix` 인데, 이는 상위 워크트리에서 상속된 컨텍스트이며 본 프로젝트 코드와는 무관. **Phase 0.0 에서 새 branch `task-1-init-infra` 로 분기 후 작업.**
- 자동 메모리에 "OneDrive 가 `terraform.tfstate` 잠금 → terraform 작업 실패" 이슈가 기록되어 있음. 본 프로젝트는 OneDrive 동기화 폴더 (`C:/Users/ab550/OneDrive/Desktop/projects/proj_days/`) 안에 있으므로 **Phase 0.3 에서 `infra/.terraform/` 와 `infra/*.tfstate*` 를 OneDrive 제외 처리하거나, 작업 직전 OneDrive 동기화 일시 중지 절차를 README 에 명시한다.**

### 2.2 사용자 확정 결정사항 (AskUserQuestion 결과)

| 항목 | 결정 |
| --- | --- |
| 백엔드 | FastAPI (Python 3.11+) |
| 프론트엔드 | React 18 + Vite + TypeScript + Axios + react-router v6 + FullCalendar React |
| RAG 방식 | 앱 레벨 수동 RAG (EC2 앱이 RDS 에서 이전 QnA SELECT → Bedrock `InvokeModel` 프롬프트에 주입) |
| 서브넷 | VPC 1개 + Public Subnet 2개 (us-east-1a, us-east-1b). EC2 와 RDS 모두 Public Subnet 배치. RDS 는 `publicly_accessible=false` + SG 로 EC2 SG 만 허용. |
| AWS 리전 | us-east-1 |
| RDS 엔진 | PostgreSQL 16 (`db.t3.micro`, 단일 AZ) |
| 로컬 저장 | 브라우저 `localStorage` (세션 도중 5문답 누적) |
| Terraform state | 로컬 파일 (`infra/terraform.tfstate`), S3 백엔드 없음 |
| 인증 | 공용 비밀번호 `inha-nxt` → 세션 쿠키 발급. 단일 가상 사용자 (`uid=1`). "사용자 정보 수정" 페이지는 dummy. |

### 2.3 Bedrock 모델 ID

요구사항은 "Claude Sonnet 4.6". AWS Bedrock 에서 Anthropic 모델은 일반적으로 두 가지 형태로 제공:

- **직접 모델 ID**: `anthropic.claude-sonnet-4-6-<release-date>-v1:0`
- **Cross-region inference profile**: `us.anthropic.claude-sonnet-4-6-<release-date>-v1:0`

**Phase 0.2 에서 `aws bedrock list-foundation-models --region us-east-1 --query "modelSummaries[?contains(modelId, 'sonnet-4-6')].modelId" --output text` 로 정확한 ID 를 조회하여 `infra/variables.tf` 의 default 와 `backend/app/config.py` 기본값에 박는다.** 만약 us-east-1 에서 Sonnet 4.6 미제공이면 즉시 사용자에게 보고하고 진행 중단.

### 2.4 검증된 오픈소스 채택 결정

다음 라이브러리는 검증된 OSS 가 존재하므로 직접 작성하지 않고 채택:

| 영역 | 라이브러리 | 채택 이유 |
| --- | --- | --- |
| FastAPI test client | `httpx.AsyncClient` + `ASGITransport` | FastAPI 공식 권장 (`TestClient` 는 동기 한정) |
| AWS 모의 (Bedrock 외 IAM/STS) | `moto[bedrock]` >=5.0 | Bedrock 모의 지원 확인 필요. Bedrock 모의가 불완전하면 `unittest.mock.patch("boto3.client")` 폴백. |
| PostgreSQL 통합 테스트 | `testcontainers[postgres]` | Docker 위 진짜 PostgreSQL 컨테이너 — 가장 신뢰성 높음 |
| DB ORM | SQLAlchemy 2.x + `asyncpg` | async FastAPI 표준 |
| DB 마이그레이션 | Alembic | SQLAlchemy 표준 |
| 프론트 테스트 | Vitest + `@testing-library/react` + `@testing-library/user-event` | Vite 권장, jest-dom 호환 |
| API 모의 (프론트 테스트) | MSW (Mock Service Worker) >=2.0 | 네트워크 레벨 모의, 가장 견고 |
| 캘린더 UI | FullCalendar React (`@fullcalendar/react` + `@fullcalendar/daygrid`) | dayGrid 뷰 충분, MIT |
| Terraform 검증 | `terraform fmt`, `terraform validate`, `terraform plan`, `terraform test` (HCL 네이티브, 1.6+) | 외부 도구 없이 가능 |

직접 작성: 인증 로직, 5문답 사이클 상태 머신, Bedrock 프롬프트 템플릿, RAG 컨텍스트 조립기.

### 2.5 데이터 모델 (확정)

```sql
-- 단일 가상 사용자 시드
INSERT INTO users (id, display_name) VALUES (1, 'default-user');

CREATE TABLE users (
    id          SERIAL PRIMARY KEY,
    display_name TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 하나의 일자(=하나의 일기) 단위 세션
CREATE TABLE qna_sessions (
    id          SERIAL PRIMARY KEY,
    user_id     INT REFERENCES users(id) NOT NULL,
    diary_date  DATE NOT NULL,                          -- 사용자가 선택한 날짜
    status      TEXT NOT NULL,                          -- 'in_progress' | 'completed'
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    UNIQUE (user_id, diary_date)                        -- 같은 날짜 중복 QnA 차단
);

CREATE TABLE qna_items (
    id              SERIAL PRIMARY KEY,
    session_id      INT REFERENCES qna_sessions(id) ON DELETE CASCADE NOT NULL,
    sequence        SMALLINT NOT NULL,                  -- 1..5
    question        TEXT NOT NULL,
    answer          TEXT,
    rag_context     JSONB,                              -- Bedrock 에 넘긴 이전 QnA 참고 스냅샷
    bedrock_meta    JSONB,                              -- 모델ID, usage tokens, latency_ms
    asked_at        TIMESTAMPTZ DEFAULT NOW(),
    answered_at     TIMESTAMPTZ,
    UNIQUE (session_id, sequence)
);

CREATE TABLE diary_entries (
    id              SERIAL PRIMARY KEY,
    session_id      INT REFERENCES qna_sessions(id) UNIQUE NOT NULL,
    user_id         INT REFERENCES users(id) NOT NULL,
    diary_date      DATE NOT NULL,
    body            TEXT NOT NULL,                       -- 500자 이내 자동 생성 일기
    bedrock_meta    JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, diary_date)
);
```

요구사항 "별도 Schema 사용" → `qna_items`(원본 QnA) 와 `diary_entries`(자동 생성 일기) 를 명확히 분리한 점으로 충족.

### 2.6 디렉토리 레이아웃 (Phase 0.3 에서 생성)

```
proj_days/
├── Task-1.md                    # 본 문서
├── README.md                    # OneDrive 주의사항 + 기동 가이드
├── .gitignore
├── infra/                       # Terraform
│   ├── versions.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── vpc.tf
│   ├── security_groups.tf
│   ├── iam.tf
│   ├── ec2.tf
│   ├── rds.tf
│   ├── user_data.sh.tftpl       # templatefile 로 렌더
│   ├── terraform.tfvars.example
│   └── tests/
│       └── plan.tftest.hcl      # terraform test (apply 없이 plan 검증)
├── backend/
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/0001_init.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI 진입점 + StaticFiles
│   │   ├── config.py            # Pydantic Settings (.env)
│   │   ├── db.py                # async engine + session
│   │   ├── models.py            # SQLAlchemy 모델
│   │   ├── schemas.py           # Pydantic I/O
│   │   ├── auth.py              # 비밀번호 검증 + 세션 쿠키
│   │   ├── bedrock.py           # boto3 wrapper + 프롬프트 템플릿
│   │   └── routers/
│   │       ├── auth.py
│   │       ├── qna.py
│   │       ├── diary.py
│   │       └── calendar.py
│   ├── conftest.py
│   └── tests/
│       ├── unit/
│       │   ├── test_auth.py
│       │   ├── test_bedrock_prompt.py
│       │   ├── test_rag_context.py
│       │   └── test_schemas.py
│       └── integration/
│           ├── test_login_flow.py
│           ├── test_qna_full_cycle.py
│           ├── test_diary_generation.py
│           └── test_calendar_query.py
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── index.html
    ├── src/
    │   ├── main.tsx
    │   ├── App.tsx
    │   ├── api/client.ts
    │   ├── hooks/useAuth.ts
    │   ├── components/
    │   │   ├── Sidebar.tsx
    │   │   └── ProtectedRoute.tsx
    │   └── pages/
    │       ├── Login.tsx
    │       ├── QnA.tsx
    │       ├── CalendarPage.tsx
    │       └── Profile.tsx
    └── tests/
        ├── setup.ts             # MSW + jest-dom
        ├── Login.test.tsx
        ├── QnA.test.tsx
        └── CalendarPage.test.tsx
```

### 2.7 EC2 부팅 시퀀스 (`user_data.sh.tftpl`)

1. amazon-linux-2023 기준. `dnf install -y python3.11 python3.11-pip nodejs git nginx postgresql15`.
2. `/opt/app` 에 git clone 또는 S3 sync (Task-1 에서는 git clone 가정, 리포지토리 URL 변수).
3. `cd backend && python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
4. `cd frontend && npm ci && npm run build` → `frontend/dist` 생성.
5. systemd unit `qna-api.service` 등록 (uvicorn 8000, `Environment=APP_PASSWORD=...` 등 주입).
6. nginx reverse proxy: `:80` → `:8000` (`/` 는 `frontend/dist` 정적, `/api/*` 는 uvicorn 으로 프록시).
7. Alembic 자동 마이그레이션 (`alembic upgrade head`).
8. 서비스 enable + start.

환경변수 주입 항목: `APP_PASSWORD`, `SESSION_SECRET`, `DB_URL`, `BEDROCK_MODEL_ID`, `AWS_REGION`.

### 2.8 보안 그룹 / IAM (확정)

| SG | Ingress | Egress |
| --- | --- | --- |
| `ec2-sg` | 80/tcp from 0.0.0.0/0, 22/tcp from `var.my_ip_cidr` | all |
| `rds-sg` | 5432/tcp from `ec2-sg` 만 | all |

IAM Role `ec2-bedrock-role` 정책:
- `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream` (Resource: 해당 모델 ARN)
- `bedrock:ListFoundationModels` (디버깅용, Resource: `*`)

---

## 3. Open Questions

없음 (모든 결정사항 사용자 확인 완료, 2.3 의 모델 ID 만 Phase 0.2 에서 CLI 조회로 확정).

---

## 4. Approach (구현 전략)

1. **상향식 개발**: Terraform 코드부터 작성 → `terraform validate`/`plan` 으로 구문 + 의존 검증 → 백엔드 코드 + 단위테스트 → 프론트 코드 + 단위테스트 → 통합테스트(로컬 docker-compose Postgres) → 실 AWS 배포 E2E.
2. **모든 모듈에 대해 "작성 → 검증 명령 실행 → 통과 확인 → 로컬 커밋"** 사이클로 진행. 한 todo 당 1 커밋 원칙.
3. **Bedrock 호출은 모두 `app/bedrock.py` 한 곳에 격리**해서 모의 가능하게 함. 라우터는 인터페이스만 의존.
4. **5문답 사이클 상태 머신**: `qna_sessions.status` + `qna_items.sequence` 만으로 결정. 별도 in-memory 세션 상태 금지 (서버 재기동 시 복원 가능해야 함).
5. **RAG 컨텍스트 조립**: 사용자 ID 의 최근 N(기본 10) 개 `qna_items`(다른 날짜 포함) + 현재 세션의 답변된 item 들을 시간순으로 정렬해 프롬프트에 주입. "실시간 반영 안 됨"은 허용 — 새 답변이 RDS 에 commit 된 후 다음 질문 생성 시 즉시 SELECT 되므로 사실상 실시간이지만, Bedrock Knowledge Base 의 임베딩 지연은 회피.
6. **일기 생성**: 5번째 답변 완료 시점에 `diary` 엔드포인트 자동 호출 → Bedrock 에 5문답 전체 + "500자 이내 한국어 일기로 변환" 프롬프트 → `diary_entries` insert.

---

## 5. Todo List (원자 단위, 재실행 가능)

> 각 todo 는 한 번에 1 커밋. **모든 todo 끝에 "Verify:" 항목이 있고, 그 명령의 출력이 통과해야 다음 todo 로 진행.** 실패 시 해당 todo 의 코드만 수정 후 재실행.

### Phase 0 — 사전 준비

- [x] **0.0** 새 branch `task-1-init-infra` 생성
  - 실행: `git -C C:/Users/ab550/OneDrive/Desktop/projects/proj_days checkout -b task-1-init-infra`
  - Verify: `git branch --show-current` → `task-1-init-infra` ✓

- [x] **0.1** AWS 자격증명 + region 확인
  - 실행: `aws sts get-caller-identity --region us-east-1`
  - Verify: Account=729403197556, user=jmh-1 ✓

- [x] **0.2** Bedrock Sonnet 4.6 모델 ID 조회
  - 실행: `aws bedrock list-foundation-models --region us-east-1 --query "modelSummaries[?contains(modelId, 'sonnet-4-6')].modelId" --output text` 및 `aws bedrock list-inference-profiles --region us-east-1 --query "inferenceProfileSummaries[?contains(inferenceProfileId, 'sonnet-4-6')].inferenceProfileId" --output text`
  - 결과: foundation=`anthropic.claude-sonnet-4-6`, 채택 ID=`us.anthropic.claude-sonnet-4-6` (US cross-region inference profile)
  - Verify: 두 소스 모두 ID 출력 확인 ✓

- [x] **0.3** 디렉토리 + `.gitignore` + `README.md` 작성
  - 작성: `proj_days/.gitignore` 에 `infra/.terraform/`, `infra/*.tfstate*`, `infra/*.tfplan`, `backend/.venv/`, `backend/__pycache__/`, `frontend/node_modules/`, `frontend/dist/`, `.env`, `.env.*`.
  - 작성: `README.md` 에 OneDrive 주의사항 + 기동 가이드 명시.
  - Verify: README.md, .gitignore 모두 untracked 확인 ✓

### Phase 1 — Terraform 인프라 코드

- [x] **1.1** `infra/versions.tf`
  - 내용: `terraform { required_version = ">= 1.6" }` + AWS provider `~> 5.0`
  - Verify: `terraform -chdir=infra init -backend=false` 성공 ✓ (aws 5.100.0 설치됨)

- [x] **1.2** `infra/variables.tf`
  - 변수: `aws_region` (default `us-east-1`), `vpc_cidr` (`10.20.0.0/16`), `public_subnet_cidrs` (`["10.20.1.0/24","10.20.2.0/24"]`), `azs` (`["us-east-1a","us-east-1b"]`), `ec2_instance_type` (`t3.small`), `db_instance_class` (`db.t3.micro`), `db_username` (`appuser`), `db_password` (sensitive, no default), `app_password` (sensitive, default `"inha-nxt"`), `session_secret` (sensitive, no default), `bedrock_model_id` (default = `us.anthropic.claude-sonnet-4-6`), `my_ip_cidr` (string, no default), `git_repo_url` (string, no default), `git_branch` (default `main`).
  - Verify: `terraform validate` 성공 ✓

- [x] **1.3** `infra/vpc.tf`
  - 리소스: `aws_vpc`, `aws_internet_gateway`, 2x `aws_subnet` (각 AZ, `map_public_ip_on_launch=true`), `aws_route_table` + `aws_route` (0.0.0.0/0 → IGW), 2x `aws_route_table_association`.
  - Verify: `terraform validate` 성공 ✓

- [x] **1.4** `infra/security_groups.tf`
  - `aws_security_group.ec2_sg`: ingress 80/0.0.0.0/0, 22/`var.my_ip_cidr`.
  - `aws_security_group.rds_sg`: ingress 5432/security_groups=[ec2_sg.id].
  - Verify: `terraform validate` 성공 ✓

- [x] **1.5** `infra/iam.tf`
  - `aws_iam_role` (assume `ec2.amazonaws.com`), `aws_iam_policy` (bedrock 권한), `aws_iam_role_policy_attachment`, `aws_iam_instance_profile`.
  - Verify: `terraform validate` 성공 ✓

- [x] **1.6** `infra/rds.tf`
  - `aws_db_subnet_group` (Public Subnet 2개 참조), `aws_db_instance`: engine `postgres`, version `16`, class `var.db_instance_class`, `allocated_storage=20`, `publicly_accessible=false`, `vpc_security_group_ids=[rds_sg.id]`, `skip_final_snapshot=true`, `deletion_protection=false`, `enabled_cloudwatch_logs_exports = []`.
  - Verify: `terraform validate` 성공 + grep `enabled_cloudwatch_logs_exports = []` 확인 ✓

- [x] **1.7** `infra/user_data.sh.tftpl` + `infra/ec2.tf`
  - 템플릿에 8단계 작성. 변수 보간: `db_url`, `app_password`, `session_secret`, `bedrock_model_id`, `aws_region`, `git_repo_url`, `git_branch`.
  - `aws_instance`: AMI = `data.aws_ami.al2023` (`name=al2023-ami-*-x86_64`), `vpc_security_group_ids`, `subnet_id`, `iam_instance_profile`, `user_data = templatefile(...)`.
  - Verify: `terraform validate` 성공 ✓

- [x] **1.8** `infra/outputs.tf`
  - 출력: `ec2_public_ip`, `ec2_public_dns`, `rds_endpoint`, `app_url`(`"http://${ec2_public_ip}"`).
  - Verify: `terraform validate` 성공 ✓

- [x] **1.9** `infra/terraform.tfvars.example` 작성 (실제 `terraform.tfvars` 는 gitignore)
  - Verify: 파일 존재 ✓

- [x] **1.10** Terraform 정적 검증 일괄
  - 실행: `terraform -chdir=infra fmt -check -recursive && terraform -chdir=infra validate`
  - Verify: 둘 다 exit 0 ✓ (ec2.tf 정렬 자동 수정됨)

- [x] **1.11** `infra/tests/plan.tftest.hcl` 작성
  - `run "plan_resources_count"` 블록에서 변수 주입 후 `command = plan` 실행, `assert` (a) EC2 1개, (b) RDS 1개, (c) Public Subnet 2개, (d) EC2 SG port 80 ingress 확인.
  - Verify: `terraform test` 1 passed, 0 failed ✓

### Phase 2 — Backend (FastAPI) 코드

- [x] **2.1** `backend/requirements.txt` + `requirements-dev.txt` + `pyproject.toml`
  - runtime: `fastapi==0.115.*`, `uvicorn[standard]`, `sqlalchemy>=2.0`, `asyncpg`, `alembic`, `pydantic-settings`, `boto3`, `python-multipart`, `itsdangerous`.
  - dev: `pytest`, `pytest-asyncio`, `httpx`, `moto[sts]>=5.0` (bedrock extra 없음→unittest.mock 폴백), `testcontainers[postgres]`, `freezegun`.
  - Verify: `python -m venv .venv && pip install` 성공 ✓ (Python 3.13.13, moto 5.2.1)

- [x] **2.2** `backend/app/config.py`
  - `class Settings(BaseSettings)`: `app_password`, `session_secret`, `db_url`, `bedrock_model_id`, `aws_region`. `model_config = SettingsConfigDict(env_file=".env")`. module-level 인스턴스 대신 `@lru_cache get_settings()` 패턴 사용.
  - Verify: Settings 직접 인스턴스화 성공 ✓

- [x] **2.3** `backend/app/db.py` + `backend/app/models.py`
  - 2.5 SQL 을 SQLAlchemy 2.x 선언적 모델로 옮김. async engine + `async_sessionmaker`. TIMESTAMPTZ→DateTime(timezone=True) 수정.
  - Verify: User/QnASession/QnAItem/DiaryEntry import 성공 ✓

- [x] **2.4** Alembic 초기화 + 0001 마이그레이션
  - `alembic init alembic` 후 `env.py` async 모드로 수정 + `target_metadata=Base.metadata`. `0001_init.py` 수동 작성 (4개 테이블 + default-user 시드).
  - Verify: `alembic upgrade head` → 3.1 conftest testcontainers 에서 검증 예정 ✓ (파일 작성 완료)

- [x] **2.5** `backend/app/auth.py`
  - `verify_password`, `create_session_cookie`, `verify_session_cookie`, `require_session` 구현.
  - Verify: 3.2 단위테스트에서 검증 예정 ✓ (파일 작성 완료)

- [x] **2.6** `backend/app/bedrock.py`
  - `BedrockClient`: `generate_question(rag_items, session_so_far, next_sequence)`, `generate_diary(qna_items)`. 모두 `asyncio.to_thread` + `(text, meta)` 튜플 반환.
  - Verify: 3.3 단위테스트에서 mock 검증 예정 ✓ (파일 작성 완료)

- [x] **2.7** `backend/app/schemas.py` (Pydantic I/O)
  - `LoginRequest`, `QnAStartRequest`, `QnAStartResponse`, `QnAAnswerRequest`, `QnAAnswerResponse`, `CalendarResponse`, `DiaryResponse` 구현.
  - Verify: import 성공 ✓

- [x] **2.8** `backend/app/routers/auth.py`
  - `POST /api/login` (Set-Cookie HttpOnly SameSite=Lax), `POST /api/logout`, `GET /api/me`.
  - Verify: 3.4 통합테스트에서 검증 예정 ✓ (파일 작성 완료)

- [x] **2.9** `backend/app/routers/qna.py`
  - `POST /api/qna/start` (409 on completed, 재개 on in_progress), `POST /api/qna/answer` (sequence 검증, 5회 완료 시 diary finalize 호출).
  - Verify: 3.5 통합테스트에서 검증 예정 ✓ (파일 작성 완료)

- [x] **2.10** `backend/app/routers/diary.py` + `routers/calendar.py`
  - `GET /api/diary/{date}` (404 if not found), `GET /api/calendar?month=YYYY-MM`, `finalize_session(session, db)` 내부 함수.
  - Verify: 3.6 통합테스트에서 검증 예정 ✓ (파일 작성 완료)

- [x] **2.11** `backend/app/main.py`
  - FastAPI + CORS + 4개 라우터 + StaticFiles (frontend/dist 존재 시) + `/api/health`. 
  - Verify: routes 12개 등록 확인 ✓ (uvicorn 기동은 Phase 6.2에서 검증)

### Phase 3 — Backend 테스트

- [x] **3.1** `backend/conftest.py`
  - fixture `pg_container`/`db_session`/`app`/`client`/`bedrock_mock` 모두 구현.
  - Verify: `pytest --collect-only` 에러 없이 0 items collected ✓

- [x] **3.2** `tests/unit/test_auth.py`
  - 케이스 5개 (정답/오답/roundtrip/tampered/expired) 모두 구현.
  - Verify: `pytest tests/unit/test_auth.py -v` 5 passed ✓

- [x] **3.3** `tests/unit/test_bedrock_prompt.py`
  - 케이스 3개 (빈 rag/최신순 정렬/partial session) 구현.
  - Verify: `pytest tests/unit/test_bedrock_prompt.py -v` 3 passed ✓

- [x] **3.4** `tests/integration/test_login_flow.py`
  - 케이스 4개 (정답/오답/비인증/인증) 구현.
  - Verify: `pytest tests/integration/test_login_flow.py -v` 4 passed (testcontainers+alembic) ✓

- [x] **3.5** `tests/integration/test_qna_full_cycle.py`
  - 케이스 5개 (start/5사이클/409/재개/400 sequence) 모두 구현.
  - Verify: `pytest tests/integration/test_qna_full_cycle.py -v` 5 passed ✓

- [x] **3.6** `tests/integration/test_diary_calendar.py`
  - 케이스 4개 (diary 200/404/calendar 포함/미포함) 구현.
  - Verify: `pytest tests/integration/test_diary_calendar.py -v` 4 passed ✓

- [x] **3.7** 전체 백엔드 테스트 일괄
  - 실행: `cd backend && pytest -v --tb=short`
  - Verify: 21 passed, 0 failed, exit 0 ✓

### Phase 4 — Frontend (React + Vite + TS) 코드

- [x] **4.1** Vite 프로젝트 생성 + 의존성 설치
  - react-ts 템플릿 + runtime/dev 의존성 모두 설치. `vitest/config` 에서 import 하여 test 설정.
  - Verify: `npm run build` exit 0 (193KB JS 번들) ✓

- [ ] **4.2** `src/api/client.ts`
  - `axios.create({ baseURL: '/api', withCredentials: true })`.
  - response interceptor: 401 → `window.location='/login'`.
  - Verify: 5.x 에서 사용됨.

- [ ] **4.3** `src/hooks/useAuth.ts` + `src/components/ProtectedRoute.tsx`
  - `useAuth`: `login(password)`, `logout()`, `isAuthed` (서버 `/api/me` ping 으로 판단).
  - `ProtectedRoute`: 미인증시 `<Navigate to="/login" />`.
  - Verify: 5.2 단위테스트.

- [ ] **4.4** `src/pages/Login.tsx`
  - 비밀번호 input + 제출. 성공시 `/qna` 로 이동.
  - Verify: 5.2 단위테스트.

- [ ] **4.5** `src/components/Sidebar.tsx`
  - 좌측 고정 사이드바: "QnA 작성", "캘린더", "프로필".
  - Verify: 빌드 성공.

- [ ] **4.6** `src/pages/QnA.tsx`
  - 1단계: 날짜 선택 (`<input type="date">`). 2단계: 시작 버튼 → `POST /api/qna/start`. 3단계: 질문 표시 + 답변 textarea + 제출 → `POST /api/qna/answer`. 매 사이클 후 응답을 `localStorage[`qna:${diary_date}`]` 에 누적 저장. 5번째 답변 후 응답에 `diary` 가 오면 결과 화면.
  - 같은 날짜에 이미 completed 면 시작 버튼 비활성 + 안내.
  - Verify: 5.3 단위테스트.

- [ ] **4.7** `src/pages/CalendarPage.tsx`
  - FullCalendar dayGrid 마운트. `datesSet` 콜백에서 `GET /api/calendar?month=...` 호출 → 이벤트로 표시. 날짜 클릭 → `/diary/${date}` 라우트로 이동.
  - 별도 `src/pages/DiaryView.tsx` 추가: `GET /api/diary/{date}` 결과 표시.
  - Verify: 5.4 단위테스트.

- [ ] **4.8** `src/pages/Profile.tsx` (dummy)
  - 정적 폼 (저장 버튼은 noop 또는 toast).
  - Verify: 빌드 성공.

- [ ] **4.9** `src/App.tsx` + `src/main.tsx` (react-router 통합)
  - 라우트: `/login`, `/qna`, `/calendar`, `/diary/:date`, `/profile`, `/` redirect to `/qna`.
  - Sidebar 는 `/login` 외에서 노출.
  - Verify: `npm run build` 성공.

### Phase 5 — Frontend 테스트

- [ ] **5.1** `tests/setup.ts` + MSW 핸들러
  - `setupServer(...handlers)` + `beforeAll/afterAll/afterEach` 표준.
  - `tests/handlers.ts` 에 `/api/login`, `/api/qna/start`, `/api/qna/answer`, `/api/calendar`, `/api/diary/:date` 모의.
  - Verify: `npm test -- --run --reporter=verbose tests/setup.ts` 통과 (or empty test pass).

- [ ] **5.2** `tests/Login.test.tsx`
  - 케이스: ① 정답 입력 → 페이지 이동 ② 오답 → 에러 메시지 ③ 빈 입력 → 제출 비활성.
  - Verify: `npm test Login` pass.

- [ ] **5.3** `tests/QnA.test.tsx`
  - 케이스: ① 날짜 선택 후 시작 → 질문 표시 ② 답변 5회 사이클 → diary 표시 ③ 매 사이클 후 `localStorage` 에 누적 저장 확인 ④ 이미 완료된 날짜 → 안내 메시지.
  - Verify: `npm test QnA` pass.

- [ ] **5.4** `tests/CalendarPage.test.tsx`
  - 케이스: ① 마운트 시 calendar API 호출 ② API 응답의 날짜에 이벤트 점 표시 ③ 날짜 클릭 → `/diary/:date` 이동.
  - Verify: `npm test CalendarPage` pass.

- [ ] **5.5** 전체 프론트 테스트 일괄
  - 실행: `cd frontend && npm test -- --run`
  - Verify: 모든 테스트 pass.

### Phase 6 — 로컬 통합 검증 (사람 손으로 한 번 확인)

- [ ] **6.1** `docker-compose.dev.yml` (Postgres 16 + .env 예시)
  - Verify: `docker compose -f docker-compose.dev.yml up -d` 후 `pg_isready` 성공.

- [ ] **6.2** 백엔드 로컬 기동 + 마이그레이션
  - 실행: `cd backend && .venv/Scripts/alembic upgrade head && .venv/Scripts/uvicorn app.main:app --reload`
  - Verify: `curl http://localhost:8000/api/health` 200.

- [ ] **6.3** 프론트 dev server + 수동 5문답 1회
  - 실행: `cd frontend && npm run dev` → 브라우저 `http://localhost:5173/login` → 비번 `inha-nxt` → QnA 5회 → 일기 확인 → 캘린더 확인.
  - Verify: 일기 한 건 생성, 캘린더에 점 표시.

### Phase 7 — AWS 실배포 + E2E

- [ ] **7.1** `infra/terraform.tfvars` 작성 (gitignore 됨)
  - 채우기: `db_password`, `session_secret`, `my_ip_cidr` (`curl ifconfig.me`), `git_repo_url`, `git_branch`.
  - Verify: 파일 존재.

- [ ] **7.2** `terraform apply`
  - 실행: `terraform -chdir=infra apply -auto-approve`
  - Verify: outputs 에 `ec2_public_ip` 비어있지 않음. AWS 콘솔에서 EC2/RDS running 상태 확인.

- [ ] **7.3** EC2 부트스트랩 완료 대기 + health check
  - 실행: `curl --retry 30 --retry-delay 10 http://$(terraform -chdir=infra output -raw ec2_public_ip)/api/health`
  - Verify: 200 OK.

- [ ] **7.4** 브라우저 수동 E2E
  - 실행: `http://${ec2_public_ip}` 접속 → 비번 → QnA 5회 → 일기 자동 생성 → 캘린더에 점 → 클릭 시 일기 본문 표시.
  - Verify: 모든 단계 동작 + RDS 에 SELECT 로 데이터 확인 (`psql` 또는 RDS Query Editor).

- [ ] **7.5** 정리 결정
  - 옵션: 유지 (다음 Task 에서 재사용) 또는 `terraform -chdir=infra destroy -auto-approve`.
  - Verify: 사용자 결정 기록.

---

## 6. Test Plan

### 6.1 단위 테스트 (입력 → 기대출력 표)

| Test | Input | Expected |
| --- | --- | --- |
| `test_auth.test_verify_correct` | `"inha-nxt"` | `True` |
| `test_auth.test_verify_wrong` | `"wrong"` | `False` |
| `test_auth.test_cookie_roundtrip` | 발급 후 즉시 검증 | `user_id=1` |
| `test_auth.test_cookie_tampered` | 1바이트 변조 | `BadSignature` 처리 |
| `test_bedrock_prompt.test_empty_rag` | rag=[], session=[] | 프롬프트에 "이전 일기 없음" 포함 |
| `test_bedrock_prompt.test_rag_order` | rag=10개 시간순 셔플 | 프롬프트 안에서 최신순 정렬 |
| `test_bedrock_prompt.test_session_partial` | session sequence 1,2 답변 완료 | 1,2 만 포함, 3-5 부재 |
| `test_rag_context.test_select_recent_n` | DB 에 30개 item | 최신 10개만 반환 |
| `Login.test_submit_correct` | 비번 입력 후 submit | navigate to `/qna` 호출 |
| `Login.test_submit_wrong` | 오답 + MSW 401 | 에러 메시지 노출 |

### 6.2 통합 테스트 (시나리오 → 최종 상태)

| Scenario | Final state |
| --- | --- |
| 로그인 → QnA start → 5회 answer | `qna_sessions.status='completed'`, `qna_items` 5개, `diary_entries` 1개 |
| 같은 날짜로 두 번째 start | HTTP 409 |
| in_progress 상태에서 같은 날짜 재진입 | sequence 가 다음 번호인 질문 반환 |
| diary 저장 후 GET /api/diary/{date} | 200 + body |
| diary 저장 후 GET /api/calendar | 해당 날짜 포함 |
| Bedrock 호출 실패 (moto 가 예외 raise) | HTTP 502 + session in_progress 유지 (idempotent retry 가능) |
| 프론트 5회 cycle | `localStorage["qna:YYYY-MM-DD"]` 에 5개 누적 |

### 6.3 자동화 명령 (한 줄)

```powershell
# 백엔드
cd backend; .venv/Scripts/pytest -v --tb=short

# 프론트
cd frontend; npm test -- --run

# Terraform
terraform -chdir=infra fmt -check -recursive; `
terraform -chdir=infra validate; `
terraform -chdir=infra test
```

세 그룹 모두 exit 0 일 때 Phase 6 진행 가능.

### 6.4 테스트가 필요로 하는 외부 의존성

- Docker (Phase 3 통합테스트 의 testcontainers 용)
- Node.js 20+ (프론트 테스트/빌드)
- Python 3.11+
- AWS CLI + 자격증명 (Phase 0.1, 0.2, 7.x)
- Terraform 1.6+
- 인터넷 (npm/pip/docker pull)

준비되지 않은 항목 발견 시 해당 Phase 시작 전에 사용자에게 보고.

---

## 7. Resume Protocol (중단 후 재개)

세션이 중단되었을 때 다음 절차로 항상 같은 지점에서 안전하게 재개한다.

1. **현재 위치 파악**
   - `git -C C:/Users/ab550/OneDrive/Desktop/projects/proj_days log --oneline -20` 로 가장 최근 todo 커밋 메시지 확인 (커밋 메시지 규칙: `task1: <Phase>.<n> <짧은 설명>`).
   - 같은 커밋 메시지의 todo 항목을 본 문서에서 찾아 그 다음 미체크 박스부터 재개.

2. **상태 검증 (다음 todo 시작 전 필수)**
   - Terraform 단계 도중 중단: `terraform -chdir=infra validate` + `terraform -chdir=infra plan` 실행해 drift 없음을 확인.
   - Backend 단계 도중 중단: `cd backend && .venv/Scripts/pytest -v --tb=short --collect-only` 후 마지막 통과 테스트까지 실제 실행.
   - Frontend 단계 도중 중단: `cd frontend && npm run build` + `npm test -- --run` 으로 회귀 확인.

3. **외부 자원 정합성**
   - Phase 7 진행 중 중단 시 `terraform -chdir=infra show` 로 현재 인프라 상태 확인. `aws ec2 describe-instances --filters Name=tag:Project,Values=qna-diary` 로 실제 리소스 존재 여부 교차 검증.

4. **재개 후 첫 동작**
   - 검증 통과 → 본 문서의 미체크 박스 중 가장 위 항목 1개 수행 → Verify 명령 실행 → 통과시 체크 + 커밋 → 다음 todo.
   - 검증 실패 → 실패 원인 디버깅 후 재실행, 새 todo 시작 금지.

5. **본 문서 수정 규칙**
   - Todo 가 완료되면 `[ ]` 를 `[x]` 로 바꾸고, 같은 커밋에 코드 변경 포함.
   - 계획 변경이 필요하면 본 문서를 먼저 수정 + 커밋 한 후 코드 작업 진행 (계획-코드 분리 커밋).

---

## 8. Hand-off

Task-1.md 작성 완료. 확인해 주세요. **시작하라고 말씀하시기 전까지 코드는 절대 수정하지 않습니다.**
