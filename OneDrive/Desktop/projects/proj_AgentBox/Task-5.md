# Task-5: `agentbox` CLI 사용자 경험 통합 (`set` / `status` 추가) + `/audit` 무토큰 대시보드 분리

> 본 문서는 Task-4 완료(`agentbox init` + Bedrock Agent 2-tool 구조 + Zero-Knowledge 강화) 상태를 전제로,
> ① WSL 한 줄로 "셸 열기 → `claude` 실행 → mitmproxy → Bedrock 검사 → Anthropic API" 가 자동 동작하도록 `agentbox set` 신설(의존성 점검 + AWS/CA/proxy env 자동 구성 + bashrc 영구 통합),
> ② 현재 운영 상태를 한 번에 보여주는 `agentbox status` 신설(SaaS URL · 의존성 · 프록시 on/off · 마지막 init · EC2 connectivity 출력),
> ③ EC2 SaaS 의 `/audit` 가 GET 시 401 을 뱉던 문제를 "HTML 페이지는 무토큰 + JSON API 는 토큰 유지" 구조로 분리,
> ④ 단위/통합 테스트 신규 작성 + 기존 테스트 PASS 유지,
> 를 수행한다.
>
> 모든 변경은 **재실행 가능한 step** 으로 구성되며, 각 단계 종료 시 자동/수동 검증을 통과해야 다음 단계로 넘어간다.
>
> 인코딩: UTF-8 (BOM 없음)
> 작성일: 2026-05-11
> 작성자: Claude (Opus 4.7)

---

## 0. 메타 정보

| 항목 | 값 |
|---|---|
| Task ID | Task-5 |
| 선행 조건 | Task-4 완료. `agentbox init <dir>` 가 동작하고, EC2(app + mcp) 가 active. `.env.endpoint` 와 `.sops.yaml` 이 채워져 있음. |
| 대상 OS | Endpoint: WSL2 Ubuntu 22.04 (1차) / Windows 11 PowerShell (2차) / macOS (best-effort). EC2: Ubuntu 22.04. |
| 핵심 변경 | ① `agentbox set` CLI 신규(의존성+CA+env+bashrc 자동 셋업), ② `agentbox status` CLI 신규(현재 상태 6항목 출력 + 푸터 "Made by JeonMyeonghwan"), ③ `ec2/saas/server.py` 의 `/audit` 라우트를 GET HTML(무토큰) + `/api/audit` JSON(토큰 유지) 로 분리, ④ `~/.agentbox/last_init.json` 기록 신설(init 메타 영속화), ⑤ 신규 단위/통합 테스트 7~9개. |
| Capex 변동 | $0. (EC2 코드만 변경, 인프라 리소스 추가 없음.) Terraform apply 1회로 EC2 user_data 갱신 또는 systemd restart 만으로 반영 가능. |
| 코드 수정 금지 | 본 문서 사용자 검토 및 "Task-5 시작" 명시 지시 전까지 일절 코드 변경 금지. |
| 작업 디렉토리 | `C:\Users\ab550\OneDrive\Desktop\projects\proj_AgentBox` (Windows 경로) / `/mnt/c/Users/ab550/OneDrive/Desktop/projects/proj_AgentBox` (WSL 경로) |
| OneDrive 주의 | terraform.tfstate 작업 시 OneDrive sync 일시중지 필요 (memory: `feedback_onedrive_terraform.md`). 본 Task 는 EC2 코드만 만지므로 terraform apply 가 필요 없으면 무관. |

### 0.1 모든 사용자 결정 사항 요약 (AskUserQuestion 답변 기반)

| 결정 항목 | 값 | 근거 질문 |
|---|---|---|
| `agentbox set` 동작 범위 | **"agentbox 사용 전 환경 점검"** = 의존성 점검 + AWS/region 등 env var 점검 + CA 확인 + bashrc 의 on/off 셸 함수 등록(기존 `agentbox setup` 동작 흡수). **HTTPS_PROXY 영구 export 및 자동 활성화는 추가하지 않음**. | Q1 + 후속 정정 |
| `/audit` 인증 처리 | "대시보드 HTML 은 무토큰, API 는 토큰 유지" = `GET /audit` → HTML 응답(인증 없음), `GET /api/audit` → JSON 응답(`X-Admin-Token` 유지) | Q2 |
| `agentbox status` 출력 항목 | (a) SaaS 대시보드 URL, (b) 의존성 상태(sops/aws/python pkg), (c) 현재 프록시 on/off, (d) 마지막 init 정보(project_id + 업로드 시각), (e) EC2 connectivity(HTTP /healthz + TCP 50051), (f) 푸터 "Made by JeonMyeonghwan" | Q3 |
| WSL → claude 라우팅 메커니즘 | **수동 유지.** 사용자가 매 셸에서 `agentbox on` 을 직접 호출해 HTTPS_PROXY 를 설정한다. `agentbox set` 은 on/off 함수만 bashrc 에 등록할 뿐 자동 활성화는 절대 추가하지 않음. | Q4 + 후속 정정 |

### 0.2 용어 사전 (LLM 재실행 시 일관성 유지용)

| 용어 | 정의 |
|---|---|
| **`agentbox set`** | 본 Task 신규 CLI 서브커맨드. 의존성/CA/env/bashrc 를 한 번에 점검 후 자동 수정. 멱등(idempotent). 기존 `agentbox setup` 과 별개 명령. |
| **`agentbox status`** | 본 Task 신규 CLI 서브커맨드. 6 가지 상태를 사람이 읽기 쉽게 출력. 부수효과(side-effect) 없음. |
| **`agentbox setup`** | 기존 명령(`src/agentbox/__main__.py` 의 `_setup_shell`). bashrc 에 `agentbox on/off` 함수만 추가. 본 Task 에서 **변경/삭제하지 않음** (호환성 보장). `set` 은 setup 의 동작을 내부적으로 호출. |
| **`agentbox on/off`** | bashrc 에 등록된 셸 함수. on → `HTTPS_PROXY=http://127.0.0.1:8080` + `NODE_EXTRA_CA_CERTS=<CA>` export. off → unset. |
| **`X-Admin-Token`** | EC2 SaaS API 의 헤더 인증 토큰. `_ADMIN_TOKEN` 환경변수와 비교. Task-3 부터 도입. |
| **SOPS** | Mozilla 의 secrets 암호화 도구. KMS 키를 사용해 파일별 암호화/복호화. `.sops.yaml` 이 KMS ARN 매핑을 담음. |
| **mitmproxy** | 로컬 TLS 가로채기 프록시. AgentBoxAddon 이 `api.anthropic.com/v1/messages` 요청을 가로채 EC2 gRPC 로 검사 위임. |
| **Bedrock Agent** | AWS 가 호스팅하는 Claude Sonnet 4.6 기반 에이전트. `list_project_files` / `decrypt_and_stage` 2 개 action_group 사용(Task-4). |
| **last_init.json** | 본 Task 신규 메타 파일. 경로: `~/.agentbox/last_init.json` (Unix) / `%USERPROFILE%\.agentbox\last_init.json` (Win). 필드: `project_id`, `src_path`, `s3_uri`, `uploaded_at(UTC ISO-8601)`, `saas_url`. `init_cmd.py` 의 성공 분기에서 기록. `status` 가 읽음. |

---

## 1. 목표

1. **agentbox 사용 전 환경 점검을 1회 명령으로.** 사용자가 신규 WSL 환경에서 `agentbox set` 한 줄 → 의존성/CA/env 자동 정비 + `~/.bashrc` 에 `agentbox on/off` 셸 함수 등록까지 일괄. 이후 사용자는 매 셸에서 `agentbox on` 을 직접 호출해 프록시를 활성화한다(=수동 토글 유지). 자동 라우팅은 도입하지 않는다.
2. **운영 가시성 향상.** `agentbox status` 한 줄로 (a) 어디서 대시보드를 봐야 하는지(SaaS URL), (b) 환경이 정상인지(의존성/연결성), (c) 현재 어떤 프로젝트가 마지막으로 등록되었는지(`last_init.json`) 를 즉시 확인. 디버깅 시간 단축.
3. **대시보드 첫인상 개선.** `/audit` URL 을 브라우저로 직접 열어도 401 이 아닌 React/HTML 페이지가 뜬다. 단, **데이터 API(`/api/audit`) 는 여전히 X-Admin-Token 필요** → 보안 회귀 없음.
4. **재실행 가능성.** Task-5 가 §6 TODO 마스터 체크리스트의 가장 최근 미체크(`- [ ]`) Phase 부터 재시작 가능. 각 Phase 가 검증 단계를 포함.
5. **테스트 자동화.** 신규 `set`/`status`/`/audit HTML` 모두에 대해 단위 + 통합 테스트가 통과. 기존 51+ 테스트 PASS 유지.

---

## 2. 아키텍처

### 2.1 변경 전 (Task-4 종료 시점)

```
Endpoint(WSL2)                           AWS
─────────────                            ─────────────────────────────
(셋업 단계)
  agentbox setup     → ~/.bashrc 에 agentbox on/off 셸 함수 추가
  agentbox ca        → 로컬 CA 생성
  agentbox init <dir>→ 프로젝트 암호화/업로드 + EC2 connectivity 확인
                     → 성공 시 SaaS URL stdout 출력(메모리에만 남음)
(런타임)
  사용자가 매 셸마다 명시적으로 'agentbox on' 호출
  → HTTPS_PROXY=http://127.0.0.1:8080
  → claude 호출 시 mitmproxy 가 가로챔 → gRPC → Bedrock → ALLOW/BLOCK

브라우저로 http://<EIP>:8000/audit 접속
  → FastAPI 가 X-Admin-Token 없으면 401 Unauthorized 응답 (사용자가 토큰 보유 안 함)
```

### 2.2 변경 후 (Task-5 목표)

```
Endpoint(WSL2)                           AWS
─────────────                            ─────────────────────────────
(셋업 단계, 1회 — "agentbox 사용 전 점검")
  agentbox set [-y]
   ├─ 의존성 점검(sops/aws/python pkg) + 자동 설치 prompt
   ├─ AWS_REGION/PROJECT_NAME 환경변수 확인 + 누락 시 ~/.bashrc 추가
   ├─ CA 인증서 존재 확인(없으면 agentbox ca 호출)
   ├─ CA 시스템 trust store 등록 확인(없으면 install_ca.sh 안내)
   └─ ~/.bashrc 에 agentbox on/off 함수 추가(=기존 setup 흡수)
       ※ HTTPS_PROXY 영구 export / 자동 활성화는 추가하지 않음.

(매 셸에서 수동 활성화)
  agentbox on   # 사용자가 직접 호출. HTTPS_PROXY=http://127.0.0.1:8080 export.

(원할 때마다)
  agentbox status
   1. SaaS Dashboard URL    : http://<EIP>:8000/audit
   2. Dependencies          : sops OK / aws OK / boto3 OK / pyyaml OK
   3. Proxy state           : ON (HTTPS_PROXY=http://127.0.0.1:8080, mitmproxy :8080 LISTEN)
   4. Last init             : project_id=myrepo, uploaded_at=2026-05-11T..., s3=s3://.../encrypted_code/myrepo/
   5. EC2 connectivity      : SaaS /healthz 200 OK | gRPC :50051 TCP OK
   6. -----------------------
      Made by JeonMyeonghwan

(런타임은 Task-4 와 동일)

브라우저로 http://<EIP>:8000/audit 접속
  → FastAPI 가 HTML 페이지 반환(인증 불필요)
  → 페이지 내부 JS 가 fetch('/api/audit', {X-Admin-Token: localStorage.adminToken})
  → 토큰 미보유 시 React Login 페이지로 라우트(기존 dashboard/src/pages/Login.tsx 재사용)
```

### 2.3 보안/Zero-Knowledge 관점 변경

| 자원 | Task-4 | Task-5 |
|---|---|---|
| `/audit` GET (브라우저) | 401 (토큰 없으면 진입 불가) | 200 HTML (토큰 없어도 페이지는 보임, 데이터는 보이지 않음) |
| `/api/audit` GET (XHR) | 신설 안 됨 (기존 `/audit` 가 JSON 반환) | 200 JSON (X-Admin-Token 필수, 401 시 React 가 Login 으로 redirect) |
| 평문 코드 노출 | 변동 없음 (Task-4 그대로) | 변동 없음 |
| Admin Token 저장 위치 | 변동 없음 (서버 env `_ADMIN_TOKEN`) | 변동 없음 |

> **검증 포인트**: `/audit` 가 HTML 을 주더라도 데이터 행이 비어 있으면 보안 회귀가 아님. 통합 테스트에서 `X-Admin-Token` 없이 `/api/audit` 호출 시 401 임을 확인한다.

---

## 3. 디렉터리 / 파일 변경 매트릭스

| 경로 | 동작 | 비고 |
|---|---|---|
| `src/agentbox/__main__.py` | 수정 | `argparse` 에 `set` 과 `status` 서브커맨드 추가. 각각 `agentbox.set_cmd:run_set` / `agentbox.status_cmd:run_status` 호출. 기존 `run`/`ca`/`setup`/`init` 분기 유지. |
| `src/agentbox/set_cmd.py` | **신규** | `agentbox set` 본체. 단계: 1) 의존성(`init_deps.DEPS` 재사용), 2) env var(`AWS_REGION`/`PROJECT_NAME`/`HITL_TIMEOUT`), 3) CA(`agentbox.proxy.ca.ensure_ca`), 4) bashrc 통합(`_install_shell_integration` ─ 기존 `__main__._setup_shell` 로직을 함수로 추출하여 재사용). **자동 활성화 단계 없음**. 모든 단계는 별도 함수로 분리 → 단위 테스트 가능. 로깅: `logs/agentbox-set-<ts>.log`. |
| `src/agentbox/status_cmd.py` | **신규** | `agentbox status` 본체. 출력 항목 6개를 순서대로 stdout 에 라인 단위 출력. 부수효과 없음. 모든 외부 호출(socket/requests/subprocess) 은 timeout 5초 + try/except. 한 항목 실패해도 다른 항목은 출력. JSON 출력 옵션(`--json`) 도 추가하여 자동화 친화. |
| `src/agentbox/last_init.py` | **신규** | `last_init.json` 읽기/쓰기 유틸. `write(meta: dict) -> None` 과 `read() -> dict | None`. 경로: `Path.home() / ".agentbox" / "last_init.json"`. UTF-8 + `json.dumps(ensure_ascii=False, indent=2)`. atomic write(`tempfile` + `Path.replace`). |
| `src/agentbox/init_cmd.py` | 수정 | Step 6 (성공 출력) 직전에 `last_init.write({...})` 호출 추가. 필드: `project_id`, `src_path`(절대경로), `s3_uri`(`s3://<bucket>/encrypted_code/<pid>/`), `uploaded_at`(UTC ISO-8601, `datetime.now(timezone.utc).isoformat()`), `saas_url`. 실패 분기(returncode != 0)에서는 쓰지 않음. |
| `ec2/saas/server.py` | 수정 | 1) 기존 `@app.get("/audit")` 의 JSON 반환 로직을 **`@app.get("/api/audit")` 로 경로만 변경**(`_require_admin` 의존성 그대로 유지). 2) 신규 `@app.get("/audit", response_class=HTMLResponse)` 추가 — **`_require_admin` 의존성 없음**. 응답: 단일 HTML 페이지(dashboard 빌드 산출물이 `/opt/agentbox/dashboard/dist/index.html` 에 존재하면 그 파일 read 후 반환, 없으면 fallback inline HTML). 3) `/healthz`/`/`/`/pipeline/stream`/`/settings/*` 는 변경 없음. |
| `dashboard/src/pages/Audit.tsx` | 수정 | fetch URL 을 `/audit` → `/api/audit` 로 변경(이미 코드는 `/api/audit` 사용 중이므로 사실상 변경 없음 — 5C-1 에서 grep 으로 재확인). |
| `dashboard/src/pages/Login.tsx` | 수정 | 토큰 검증용 호출도 `/api/audit?limit=1` 로 변경(이미 `/api/audit` 사용 중이므로 변경 없음 — 5C-1 에서 grep 재확인). |
| `dashboard/src/components/AuthProvider.tsx` | 미변경 | 토큰 storage 로직 유지. |
| `infra/userdata-app.sh.tpl` | 수정(소폭) | `dashboard/dist` 가 빌드되어 `/opt/agentbox/dashboard/dist` 에 배치되는 단계 추가. `cd /opt/agentbox/dashboard && npm ci && npm run build` 호출(없으면 skip, fallback HTML 사용). EC2 디스크 사용량 +50MB 이내. |
| `scripts/deploy.sh` | 미변경 | code zip 에 `dashboard/dist` 가 포함되는지 5D-2 에서 zip 명세 확인. 빠져 있으면 archive_file include glob 에 추가(`infra/code_dist.tf`). |
| `infra/code_dist.tf` | 수정 가능성 | `dashboard/dist/**` 를 zip 에 포함하도록 source_dir 또는 include 패턴 조정. dashboard 가 EC2 에서 직접 빌드되는 옵션을 택하면 변경 없음. **택일은 5D-1 에서 결정.** |
| `tests/unit/test_set_cmd.py` | **신규** | `_check_deps_step`, `_check_env_step`, `_install_shell_integration`, `_append_auto_on` 각 함수 단위 테스트. subprocess/file IO 는 mock. tmp `HOME` 사용(`monkeypatch.setenv("HOME", str(tmp_path))`). |
| `tests/unit/test_status_cmd.py` | **신규** | `_get_saas_url`, `_get_deps_status`, `_get_proxy_state`, `_get_last_init`, `_get_connectivity` 각각 단위 테스트. requests/socket/subprocess mock. last_init.json 은 tmp_path 기반. |
| `tests/unit/test_last_init.py` | **신규** | `write` 후 `read` 가 동일 dict 반환. 파일 없으면 `read() == None`. 손상된 JSON 이면 `read() == None` + 경고 로그. atomic write 검증(`tempfile.NamedTemporaryFile` 가 잔류하지 않음). |
| `tests/unit/test_saas_audit_html.py` | **신규** | EC2 SaaS FastAPI TestClient. `GET /audit` (헤더 없음) → 200 + `text/html` content-type + body 에 `<html` 포함. `GET /api/audit` (헤더 없음) → 401. `GET /api/audit` (X-Admin-Token=<known>) → 200 + JSON 리스트. |
| `tests/integration/test_set_e2e.py` | **신규** | tmp `HOME` + tmp project. `agentbox set -y --skip-deps-install` 호출(설치는 mock) → ~/.bashrc 내용에 `agentbox on/off` 함수 + AWS_REGION export 가 포함되는지 검증. `--auto-on` 추가 케이스도 검증. |
| `tests/integration/test_status_e2e.py` | **신규** | 1) last_init.json 있는 경우: `agentbox status` 호출 → stdout 에 SaaS URL, project_id, "Made by JeonMyeonghwan" 포함. 2) last_init.json 없는 경우: stdout 에 "No previous init" 포함. 3) `--json` 옵션 시 JSON 파싱 가능. |
| `tests/integration/test_audit_html_e2e.py` | **신규** | EC2 SaaS 를 별도 프로세스로 띄울 수는 없으므로 `httpx.AsyncClient(app=app)` ASGI in-process 테스트. fixture: `monkeypatch.setenv("ADMIN_TOKEN","testtok")` + DynamoDB mock(moto). 동일 검증 + dashboard HTML 응답 길이 > 0. |
| `pyproject.toml` / `requirements-dev.txt` | 미변경 | 신규 의존성 없음. 기존 fastapi/pytest/moto/responses/httpx 그대로. |
| `~/.agentbox/last_init.json` (사용자 환경) | 신규 (runtime) | 본 Task 가 도입하는 영속 파일. 디렉토리 미존재 시 자동 생성. |
| `~/.bashrc` (사용자 환경) | 수정 (runtime) | `agentbox set` 이 idempotent 하게 추가. marker 문자열 `# AgentBox shell integration` 으로 중복 방지 (기존 `_setup_shell` 패턴 재사용). |

---

## 4. 단계별 작업 계획 (Phase)

> 각 Phase 는 **자체 완결 검증** 을 가진다. Plan 이 중간에 끊겨도 §6 TODO 마스터 체크리스트의 가장 최근 미체크(`- [ ]`) Phase 부터 재시작 가능.
> Phase 간 의존성: 5A → 5B → 5C → 5D → 5E → 5F → 5G.
> 단, 5E(단위 테스트) 는 각 Phase 종료 시점에 점진적으로 작성. 5F(통합) 는 5A~5D 완료 후만.

---

### Phase 5A — `agentbox set` CLI 신설

**목적**: 사용자가 1회 실행으로 의존성 + AWS env + CA + bashrc 통합 모두 완료. 멱등.

- [ ] **5A-1** `src/agentbox/set_cmd.py` 작성 — 메인 함수 `run_set(args) -> int`
  - 파일 헤더 `"""agentbox set — unified environment provisioning."""` + logger 셋업(`logs/agentbox-set-<ts>.log`, `init_cmd._setup_file_logger` 패턴 재사용 후 logger 이름만 `"agentbox.set"` 로 변경).
  - **Step 1 — 의존성 점검**:
    - `from agentbox.init_deps import DEPS, PYTHON_PACKAGES, check_dep, check_python_pkg, try_auto_install`.
    - 각 dep 에 대해 `check_dep` → 실패한 것 모음.
    - 실패한 dep 가 있고 `args.skip_deps_install` 가 False:
      - `args.yes` 면 자동 설치 진행. 아니면 prompt `"누락된 의존성: {names}. 자동 설치할까요? [y/N]: "`.
      - `try_auto_install(dep)` 호출. 실패 시 `install_hint` 출력 후 `return 4`.
    - PYTHON_PACKAGES 는 출력만(현재 venv 에 import 가능했다 = OK).
  - **Step 2 — 환경변수 점검**:
    - 점검 대상: `AWS_REGION`, `PROJECT_NAME`. (선택) `HITL_TIMEOUT`.
    - 현재 셸 `os.environ` 에 없거나 빈 문자열이면 prompt 로 값 받음(`args.yes` 면 기본값 사용 — `AWS_REGION=us-east-1`, `PROJECT_NAME=agentbox`).
    - 받은 값을 ~/.bashrc 에 `export AWS_REGION=...` 형태로 idempotent append.
    - marker 문자열 `# AgentBox environment` 로 중복 방지.
  - **Step 3 — CA 인증서**:
    - `from agentbox.proxy.ca import ensure_ca` + `from agentbox.config import cfg` + `from pathlib import Path`.
    - `_resolve_paths()` (기존 `__main__._resolve_paths` 와 동일 로직: cfg.CA_DIR 이 relative 면 _PROJ_ROOT 와 결합). 본 모듈 내 헬퍼로 동일 함수 정의(import 가능하면 import).
    - `ca_crt, ca_key = ensure_ca(Path(cfg.CA_DIR))`. 이미 있으면 변경 없이 그대로 반환.
    - 시스템 trust store 등록 확인: `openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt <ca_crt>` 실행. exit 0 이 아니면 안내 메시지("`sudo bash scripts/install_ca.sh` 를 실행해 주세요.") 출력. 강제 실행하지 않음(sudo 필요).
  - **Step 4 — bashrc 통합 (on/off 함수)**:
    - `__main__._setup_shell` 의 본문을 `_install_shell_integration() -> bool` 함수로 추출(in `set_cmd.py`). 반환값 = 새로 추가했는지 여부.
    - 호출. 이미 추가되어 있으면 그대로 두고 "shell integration already installed" 출력.
    - **HTTPS_PROXY 자동 export / 자동 활성화 라인은 절대 추가하지 않음.** `agentbox on` 은 사용자가 매 셸에서 수동으로 호출하는 명령으로 유지.
  - **Step 5 — 완료 안내**:
    - `print("[agentbox] set 완료. 'source ~/.bashrc' 후 매 셸에서 'agentbox on' 으로 프록시를 활성화하세요.")`.
    - `return 0`.
  - 검증: `pytest tests/unit/test_set_cmd.py -v` PASS (5A-3 에서 작성).

- [ ] **5A-2** `src/agentbox/__main__.py` 의 `main()` 에 `set` 서브커맨드 추가
  - sub.add_parser 호출:
    ```python
    p_set = sub.add_parser(
        "set",
        help="Unified environment setup (deps + CA + env + bashrc integration)",
        description=(
            "Pre-check the environment before using agentbox.\n\n"
            "Steps performed (idempotent):\n"
            "  1. Check sops, aws CLI, boto3, pyyaml — auto-install on prompt\n"
            "  2. Check AWS_REGION / PROJECT_NAME — add to ~/.bashrc if missing\n"
            "  3. Generate CA cert if missing (calls 'agentbox ca' internally)\n"
            "  4. Register 'agentbox on/off' shell helpers in ~/.bashrc\n\n"
            "Activation stays manual: run 'agentbox on' in each shell where\n"
            "you want the proxy enabled."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_set.add_argument("-y","--yes",action="store_true",help="Auto-accept all prompts")
    p_set.add_argument("--skip-deps-install",action="store_true",help="Check deps but don't install")
    ```
  - `args.cmd == "set"` 분기 추가:
    ```python
    elif args.cmd == "set":
        from agentbox.set_cmd import run_set
        sys.exit(run_set(args))
    ```
  - 검증: `agentbox --help` 출력에 `set` 이 표시되고, `agentbox set --help` 가 위 description 을 보여줌.

- [ ] **5A-3** `tests/unit/test_set_cmd.py` 작성 — 5A-1 의 5단계 각각 단위 테스트
  - fixture: `tmp_home(tmp_path, monkeypatch) -> Path` — `monkeypatch.setenv("HOME", str(tmp_path))` + `(tmp_path/".bashrc").write_text("")`.
  - 테스트 케이스:
    - `test_step1_deps_all_present` — `check_dep` 를 monkeypatch 로 항상 True 리턴 → 설치 시도 0회.
    - `test_step1_deps_missing_no_install` — sops 가 fail → `--skip-deps-install` → 종료 코드 비 0 (혹은 경고만 출력 후 0, 본 Task 에서 결정 — **5A-1 작성 시 명시: skip 이면 경고만 출력하고 0 으로 진행**).
    - `test_step2_env_missing` — `monkeypatch.delenv("AWS_REGION", raising=False)` + `-y` → bashrc 에 `export AWS_REGION=us-east-1` 추가됨.
    - `test_step2_idempotent` — 이미 marker 존재 시 중복 추가 안 됨.
    - `test_step3_ca_missing` — `cfg.CA_DIR` 가 tmp 경로 → 함수 실행 후 `agentbox-ca.crt` 가 생성됨.
    - `test_step4_shell_integration` — bashrc 에 `# AgentBox shell integration` 마커 + `agentbox()` 함수 정의 포함.
    - `test_no_auto_activation_added` — bashrc 어디에도 `agentbox on` 자동 실행 라인이나 `export HTTPS_PROXY=` 라인이 없음(자동 활성화 금지 검증).
  - 명시: `try_auto_install` 은 항상 mock(`monkeypatch.setattr("agentbox.set_cmd.try_auto_install", lambda d: True)`).
  - 검증: `pytest tests/unit/test_set_cmd.py -v` 8개 PASS.

---

### Phase 5B — `agentbox status` CLI 신설

**목적**: 사용자가 현재 운영 상태를 1초 안에 파악.

- [ ] **5B-1** `src/agentbox/last_init.py` 작성 — read/write 유틸
  - 경로: `_DEFAULT_PATH = Path.home() / ".agentbox" / "last_init.json"`.
  - 함수 `write(meta: dict, path: Path | None = None) -> None`:
    - target = path or _DEFAULT_PATH.
    - `target.parent.mkdir(parents=True, exist_ok=True)`.
    - tmp = `target.with_suffix(".tmp")` → `tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")` → `tmp.replace(target)`.
  - 함수 `read(path: Path | None = None) -> dict | None`:
    - target = path or _DEFAULT_PATH.
    - 파일 없거나 JSON 파싱 실패 시 None + `logger.warning` (logger 이름 `"agentbox.last_init"`).
  - 검증: `pytest tests/unit/test_last_init.py` PASS (5B-4 에서 작성).

- [ ] **5B-2** `src/agentbox/init_cmd.py` 의 Step 6 직전에 last_init 기록 추가
  - 정확한 위치: 현재 `init_cmd.py` 의 라인 ~203 `_log(f"[agentbox] init OK. ...")` **직전**.
  - 추가 코드:
    ```python
    from datetime import timezone
    from agentbox import last_init as _last_init

    s3_bucket = env["PROJECT_S3_BUCKET"]
    _last_init.write({
        "project_id": pid,
        "src_path": str(src),
        "s3_uri": f"s3://{s3_bucket}/encrypted_code/{pid}/",
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "saas_url": saas_url,
    })
    ```
  - 실패 분기(각 return 2~7)에서는 호출 안 됨(이미 위치상 분기 후이므로 자동).
  - 검증: 기존 `tests/integration/test_init_e2e.py` 의 성공 케이스 직후 `Path.home()/".agentbox"/"last_init.json"` 존재 + project_id 값 일치 → 본 Task 의 5E-1 통합 테스트에서 추가 검증.

- [ ] **5B-3** `src/agentbox/status_cmd.py` 작성
  - 헤더: `"""agentbox status — print current AgentBox runtime state."""`.
  - 함수 분할:
    - `_get_saas_url() -> str | None` — last_init 의 `saas_url` 우선. 없으면 `init_cmd.get_terraform_output("saas_url")` 시도. 없으면 `.env.endpoint` 에서 `EC2_GRPC_HOST` 읽어 `http://<ip>:8000` 구성. 모두 실패 시 None.
    - `_get_deps_status() -> dict[str, bool]` — `DEPS` + `PYTHON_PACKAGES` 각각 OK/MISSING.
    - `_get_proxy_state() -> dict` — `{"https_proxy_env": os.environ.get("HTTPS_PROXY"), "listening_8080": <bool>}`. listening 확인은 socket.create_connection("127.0.0.1", 8080) 시도(timeout 0.5s).
    - `_get_last_init() -> dict | None` — `last_init.read()` 호출.
    - `_get_connectivity(saas_url, grpc_host) -> dict` — `{"saas_healthz": <status_code or err>, "grpc_tcp": <bool or err>}`. requests.get(saas_url + "/healthz", timeout=3) + socket.create_connection((grpc_host, 50051), timeout=3).
  - `run_status(args) -> int`:
    - 위 함수들을 순서대로 호출.
    - `--json` 옵션이면 모든 결과를 dict 로 합쳐 `json.dumps(..., ensure_ascii=False, indent=2)` 출력. 그 외에는 사람이 읽기 좋은 형태로 줄단위 출력.
    - 사람용 출력 예시:
      ```
      AgentBox Status
      ==================================================
      1. SaaS Dashboard URL : http://54.165.51.239:8000/audit
      2. Dependencies        : sops OK | aws OK | boto3 OK | pyyaml OK
      3. Proxy state         : ON  (HTTPS_PROXY=http://127.0.0.1:8080, :8080 LISTEN)
      4. Last init           : project_id=myrepo (2026-05-11T03:21:18+00:00)
                               s3=s3://agentbox-encrypted-code/encrypted_code/myrepo/
      5. EC2 connectivity    : /healthz=200 | gRPC :50051=TCP OK
      --------------------------------------------------
      Made by JeonMyeonghwan
      ```
    - 각 라인은 해당 정보 실패 시에도 다른 라인 출력은 계속 진행(전체 호출은 항상 0 반환).
    - "Made by JeonMyeonghwan" 푸터는 `--json` 모드에서는 출력하지 않음(파싱 방해 회피). 단, `--json` 결과 dict 의 `"meta"` 필드에 `{"author":"JeonMyeonghwan"}` 포함.
  - 검증: `pytest tests/unit/test_status_cmd.py` PASS (5B-5 에서 작성).

- [ ] **5B-4** `src/agentbox/__main__.py` 에 `status` 서브커맨드 추가
  - sub.add_parser:
    ```python
    p_status = sub.add_parser(
        "status",
        help="Print current AgentBox runtime state (URL, deps, proxy, last init, connectivity)",
        description=(
            "Read-only diagnostic. Prints 5 status lines and a 'Made by' footer.\n"
            "Use --json for machine-readable output."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_status.add_argument("--json", action="store_true", help="Output as JSON")
    ```
  - `elif args.cmd == "status": from agentbox.status_cmd import run_status; sys.exit(run_status(args))`.

- [ ] **5B-5** `tests/unit/test_last_init.py` + `tests/unit/test_status_cmd.py` 작성
  - `test_last_init.py`:
    - `test_write_then_read_roundtrip` — dict 기록 후 동일 값 read.
    - `test_read_missing_returns_none`.
    - `test_read_corrupted_returns_none` — invalid JSON 작성 후 read.
    - `test_atomic_write_no_tmp_residual` — write 후 `.tmp` 잔류 없음.
  - `test_status_cmd.py`:
    - 모든 외부 호출 mock(requests/socket/subprocess/Path.home).
    - `test_get_saas_url_from_last_init` — last_init 가 saas_url 보유 시 그 값 반환.
    - `test_get_saas_url_fallback_terraform` — last_init None 일 때 terraform output 사용.
    - `test_get_deps_status_all_ok` / `test_get_deps_status_sops_missing`.
    - `test_get_proxy_state_on` (env 있고 8080 listen) / `test_get_proxy_state_off`.
    - `test_run_status_includes_footer` — stdout capture 후 "Made by JeonMyeonghwan" 포함.
    - `test_run_status_json_no_footer_in_stdout` — `--json` 시 푸터 문자열 없음 + meta.author 존재.
  - 검증: `pytest tests/unit/test_last_init.py tests/unit/test_status_cmd.py -v` 10+ PASS.

---

### Phase 5C — EC2 SaaS `/audit` HTML/API 분리

**목적**: 브라우저로 `/audit` 진입 시 401 대신 React 페이지(또는 fallback HTML) 반환. 데이터 API 는 토큰 유지.

- [ ] **5C-1** dashboard 코드 사전 확인
  - `grep -n "/audit\|/api/audit" dashboard/src/pages/Audit.tsx dashboard/src/pages/Login.tsx`.
  - 현재 두 파일 모두 `/api/audit` 사용 중임을 재확인(이미 사전 조사에서 확인됨, 5C-1 은 변경 없을 가능성 높음).
  - 만약 어떤 파일이라도 `/audit` (api 접두사 없이) 를 호출하면 `/api/audit` 으로 수정.

- [ ] **5C-2** `ec2/saas/server.py` 수정
  - 기존 `@app.get("/audit")` 데코레이터를 `@app.get("/api/audit")` 로 변경(함수 본문/`_require_admin` 의존성 유지).
  - 신규 핸들러 추가(파일 끝, `if __name__ == "__main__":` 전):
    ```python
    from fastapi.responses import HTMLResponse
    from pathlib import Path as _Path

    _DASHBOARD_DIST = _Path("/opt/agentbox/dashboard/dist/index.html")
    _FALLBACK_HTML = """<!doctype html><html><head><meta charset=utf-8>
    <title>AgentBox Audit</title></head><body>
    <div id=root></div>
    <script>document.getElementById('root').innerHTML='Dashboard bundle not built. See README.';</script>
    </body></html>"""

    @app.get("/audit", response_class=HTMLResponse)
    async def audit_page():
        if _DASHBOARD_DIST.exists():
            return _DASHBOARD_DIST.read_text(encoding="utf-8")
        return _FALLBACK_HTML
    ```
  - 같은 패턴으로 SPA 깊은 라우트(`/pipeline`, `/prompt`, `/settings`) 도 동일 HTML 반환하도록 catch-all 추가(`@app.get("/{full_path:path}", response_class=HTMLResponse)` 는 다른 라우트와 충돌 가능 → **본 Task 에서는 `/audit` 만 처리, SPA 라우팅은 5C-3 에서 결정**).

- [ ] **5C-3** SPA fallback 결정
  - 옵션 A: `/audit` HTML 응답 1개만 추가하고, React 가 push state 로 `/audit` 내에서만 라우트.
  - 옵션 B: catch-all `/{path}` 라우트 추가하여 모든 비 API 경로가 HTML 응답.
  - **기본 채택: 옵션 A** (보안 회귀 위험 최소, 본 Task 범위 = `/audit` 만 해결).
  - 옵션 B 가 필요하면 후속 Task 로 분리.

- [ ] **5C-4** dashboard 빌드 산출물 배치
  - `infra/userdata-app.sh.tpl` 의 `unzip ... /opt/agentbox` 이후에 다음 단계 추가:
    ```bash
    # Dashboard build (best-effort)
    if [ -f /opt/agentbox/dashboard/package.json ]; then
      apt-get install -y nodejs npm
      cd /opt/agentbox/dashboard
      npm ci --silent || true
      npm run build || true
      cd /opt/agentbox
    fi
    ```
  - **빌드 실패해도 fallback HTML 로 동작** 하므로 `|| true` 로 비차단.
  - 본 단계는 user_data 재실행을 요구. EC2 재배포는 Phase 5G 에서.

- [ ] **5C-5** `tests/unit/test_saas_audit_html.py` 작성
  - fastapi.testclient.TestClient 사용. `ec2/saas/server.py` 의 `app` 직접 import.
  - 환경변수 fixture: `monkeypatch.setenv("ADMIN_TOKEN", "testtok")` + `monkeypatch.setenv("AWS_REGION", "us-east-1")` + DynamoDB는 moto mock 또는 boto3 client mock.
  - 케이스:
    - `test_audit_page_no_token_returns_html` — `GET /audit` 헤더 없음 → 200, content-type `text/html`, body `<html` 포함.
    - `test_api_audit_no_token_returns_401` — `GET /api/audit` 헤더 없음 → 401.
    - `test_api_audit_with_token_returns_json` — `GET /api/audit` 헤더 `X-Admin-Token: testtok` → 200, JSON 리스트 응답(빈 리스트 허용).
    - `test_audit_page_uses_dist_if_exists` — `_DASHBOARD_DIST` 가 가리키는 경로를 tmp 파일로 monkeypatch + 임시 파일 작성 → 응답에 그 내용 포함.
  - 검증: `pytest tests/unit/test_saas_audit_html.py -v` PASS.

---

### Phase 5D — dashboard 빌드 산출물 zip 포함 (필요 시)

**목적**: EC2 가 `npm run build` 를 매번 돌리지 않아도 되도록, deploy.sh 가 빌드된 `dashboard/dist` 를 zip 에 포함.

- [ ] **5D-1** 빌드 위치 결정 — 로컬 빌드 vs EC2 빌드
  - **결정**: 일단 5C-4 의 EC2 빌드 경로(best-effort) 를 유지. 로컬 빌드 zip 포함은 후속 Task 로 분리. 본 Phase 는 검증만 진행.
  - 근거: 본 Task 의 핵심은 `/audit` 가 무토큰 HTML 을 주는 것. fallback HTML 만으로도 1차 검증 충족. dist 가 있으면 더 좋고, 없어도 동작.

- [ ] **5D-2** `infra/code_dist.tf` 검토
  - 현재 archive_file 의 `source_dir` 이 무엇인지 확인.
  - 만약 `proj_AgentBox` 전체를 zip 하고 있다면 `dashboard/dist` 가 자동 포함됨 → 로컬에서 미리 `npm run build` 후 `terraform apply` 하면 zip 에 들어감.
  - exclude 패턴에 `node_modules` 가 있는지 확인(없으면 zip 비대화).
  - 변경 필요 시 별도 commit. **본 Phase 에서 실제 수정은 안 함** (선택적).

---

### Phase 5E — 단위 테스트 전체 PASS 확인 + 마이그레이션 영향 점검

**목적**: 신규 8~10개 단위 테스트 + 기존 51+ 테스트 PASS.

- [ ] **5E-1** 신규 단위 테스트 일괄 실행
  - `pytest tests/unit/test_set_cmd.py tests/unit/test_status_cmd.py tests/unit/test_last_init.py tests/unit/test_saas_audit_html.py -v`.
  - 모두 PASS. 실패 1개라도 있으면 5A~5C 로 돌아가 수정.

- [ ] **5E-2** 기존 단위 테스트 회귀 확인
  - `pytest tests/unit/ -v` 전체 실행.
  - 특히 영향 받을 수 있는 파일:
    - `tests/unit/test_init_cmd.py` — `init_cmd.py` 의 Step 6 직전에 `last_init.write` 호출 추가됨. 기존 테스트가 통과하는지 + `Path.home()` 이 mock 되어 tmp 로 가는지 확인. 안 되어 있으면 `monkeypatch.setattr("agentbox.init_cmd._last_init.write", lambda meta: None)` 로 우회 추가 또는 fixture 정비.
    - `tests/unit/test_init_deps.py` — 변경 없음, 영향 없음.
  - PASS 안 되면 5B-2 의 패치 위치/방식 조정.

- [ ] **5E-3** 커버리지 확인
  - `pytest tests/unit/ --cov=agentbox --cov-report=term-missing` 출력에서 `set_cmd.py`, `status_cmd.py`, `last_init.py` 의 line coverage 가 각각 80% 이상인지.
  - 미달 시 5A-3 / 5B-5 에 케이스 추가.

---

### Phase 5F — 통합 테스트

**목적**: CLI → 파일시스템 → SaaS HTTP 까지 end-to-end 검증.

- [ ] **5F-1** `tests/integration/test_set_e2e.py` 작성
  - fixture `tmp_home` (tmp_path 기반 HOME) + `tmp_proj_root` (tmp_path 기반 _PROJ_ROOT mock).
  - 케이스:
    - `test_set_idempotent` — `agentbox set -y --skip-deps-install` 를 두 번 호출 → bashrc 라인 개수가 같음(중복 추가 없음).
    - `test_set_writes_env_exports` — bashrc 에 `export AWS_REGION=` 및 `export PROJECT_NAME=` 라인 존재.
    - `test_set_does_not_auto_activate` — bashrc 에 `agentbox on` 자동 실행 라인이나 `export HTTPS_PROXY=` 라인이 **없음**.
    - `test_set_registers_shell_functions` — bashrc 에 `agentbox()` 셸 함수와 on/off case 분기가 존재.
    - `test_set_returns_zero_on_success` — exit code 0.
  - 호출 방식: `subprocess.run([sys.executable, "-m", "agentbox", "set", "-y", "--skip-deps-install"], env={..., "HOME": str(tmp_home)}, capture_output=True)`.

- [ ] **5F-2** `tests/integration/test_status_e2e.py` 작성
  - 케이스:
    - `test_status_no_last_init` — `Path.home()/".agentbox"` 비어 있음 → stdout 에 `"No previous init"` 또는 `last_init=None` 표시 + 푸터 존재.
    - `test_status_with_last_init` — last_init.json 미리 작성 → stdout 에 project_id + uploaded_at + saas_url 모두 포함.
    - `test_status_json_output` — `--json` → stdout 을 `json.loads` 가능 + `meta.author == "JeonMyeonghwan"`.
    - `test_status_connectivity_failures_dont_crash` — saas_url 가 unreachable → exit code 0 + "connectivity" 라인에 에러 문자열.

- [ ] **5F-3** `tests/integration/test_audit_html_e2e.py` 작성
  - httpx.AsyncClient(app=app) ASGI in-process.
  - fixture: moto DynamoDB mock + `monkeypatch.setenv("ADMIN_TOKEN","testtok")`.
  - 케이스:
    - `test_audit_html_no_auth` — GET /audit (no header) → 200 + text/html.
    - `test_api_audit_requires_token` — GET /api/audit (no header) → 401.
    - `test_api_audit_with_token` — GET /api/audit (with X-Admin-Token) → 200 + JSON list.
    - `test_audit_html_serves_dist_when_present` — monkeypatch 로 `_DASHBOARD_DIST` 를 tmp 경로로 가리키게 + 내용 작성 → 응답이 그 내용 포함.

- [ ] **5F-4** 통합 테스트 일괄 실행
  - `pytest tests/integration/test_set_e2e.py tests/integration/test_status_e2e.py tests/integration/test_audit_html_e2e.py -v`.
  - 모두 PASS.

- [ ] **5F-5** 기존 통합 테스트 회귀 확인
  - `pytest tests/integration/ -v` 전체.
  - 특히 `tests/integration/test_init_e2e.py` 가 last_init.json 신규 IO 로 인해 깨지지 않는지 확인. tmp HOME 이 fixture 에 있는지 검토.
  - PASS 안 되면 5B-2 의 import 경로/위치 재조정.

---

### Phase 5G — 실 환경 검증 + EC2 재배포

**목적**: 로컬 테스트 PASS 가 실제 WSL2/EC2 에서도 동일한 효과를 내는지 확인.

- [ ] **5G-1** 로컬 WSL2 에서 `agentbox set` 실행
  - 가상환경 활성화 후 `pip install -e .` 재설치(setup.py 변경 시).
  - `agentbox set -y --skip-deps-install` 호출 → exit code 0.
  - `cat ~/.bashrc | tail -30` 으로 marker 2개(`# AgentBox shell integration`, `# AgentBox environment`) 확인.
  - 새 WSL 셸 열기 → `echo $HTTPS_PROXY` 는 **빈 문자열**(자동 활성화 금지) 인지 확인.
  - `agentbox on` 을 수동으로 호출 → `echo $HTTPS_PROXY` 가 `http://127.0.0.1:8080` 으로 바뀌는지 확인.

- [ ] **5G-2** 로컬에서 `agentbox status` 실행
  - 출력 6항목 모두 사람이 보기에 정상.
  - "Made by JeonMyeonghwan" 푸터 표시.

- [ ] **5G-3** EC2 재배포 (필요 시)
  - `ec2/saas/server.py` 변경 → EC2 의 systemd 서비스 재시작 또는 user_data 갱신 필요.
  - **간단 경로**: SSH 로 EC2 접속 → `cd /opt/agentbox && git pull`(가능하면) 또는 `aws s3 cp s3://.../code.zip . && unzip -o code.zip && systemctl restart agentbox-saas`.
  - **terraform 경로**: `./scripts/deploy.sh` 호출 → archive_file 가 새 zip 생성 → user_data 가 새 zip 다운로드. **OneDrive sync 일시중지 필수** (memory: `feedback_onedrive_terraform.md`).
  - 선택: 5C-4 의 npm 빌드 단계까지 포함하려면 user_data 재실행(EC2 termination + replacement 또는 cloud-init rerun) 필요.

- [ ] **5G-4** 브라우저로 `http://<EIP>:8000/audit` 접속
  - 401 이 아닌 HTML 페이지가 표시되는지 확인.
  - 페이지 내부 fetch 가 401 이면 React Login 컴포넌트로 라우트 — 토큰 입력 시도 → 정상 동작 확인.

- [ ] **5G-5** WSL 에서 `claude` 실행 round-trip
  - 새 WSL 셸 → `claude --print "테스트 프롬프트"` → 응답 수신.
  - SaaS 대시보드 `/audit` 페이지 새로고침 시 새 이벤트 1개 추가.
  - Bedrock verdict(ALLOW) 가 행에 표시.

---

## 5. 인코딩 및 환경 규약

1. **모든 신규 파일은 UTF-8(BOM 없음)** 으로 저장. Python 파일은 PEP 263 magic comment 불필요(Python 3.x 기본).
2. **`Write` 도구 사용 시** content 에 `\n` 줄바꿈 사용(Windows CRLF 회피). Python 코드 내 `open(..., encoding="utf-8")` 명시.
3. **JSON 직렬화**: 한글 보존이 필요한 경우 `ensure_ascii=False`. `last_init.json` 도 동일.
4. **로그**: `logs/agentbox-<cmd>-<timestamp>.log`. timestamp 형식 `%Y%m%d-%H%M%S`. 핸들러는 `logging.FileHandler` (rotation 없음, 본 Task 범위에서 불필요).
5. **subprocess 호출 시** `shell=True` 회피 가능한 곳은 회피. `check=False` 명시(returncode 별도 처리).
6. **PowerShell 환경 호환성**: Windows 에서 `agentbox set` 호출되면 ~/.bashrc 가 없을 수 있으므로 `Path.home() / ".bashrc"` 존재 확인 후 안내 메시지("Windows native shell 에서는 PowerShell profile 사용 권장") 만 출력하고 통과. 본 Task 의 1차 타겟은 WSL2.

---

## 6. TODO 마스터 체크리스트

> Plan 이 중단된 후 재실행 시 **가장 윗줄부터 순서대로** 미체크 항목을 진행. 각 항목 옆 `[ ]` 가 `[x]` 로 바뀌어야 다음 항목 시작.

### Phase 5A — agentbox set CLI
- [x] 5A-1: `src/agentbox/set_cmd.py` 작성 (4단계 함수 + run_set, 자동 활성화 없음)
- [x] 5A-2: `src/agentbox/__main__.py` 에 set 서브커맨드 추가
- [x] 5A-3: `tests/unit/test_set_cmd.py` 작성 + PASS

### Phase 5B — agentbox status CLI
- [x] 5B-1: `src/agentbox/last_init.py` 작성
- [x] 5B-2: `init_cmd.py` 의 Step 6 직전 `last_init.write` 호출 추가
- [x] 5B-3: `src/agentbox/status_cmd.py` 작성 (6 항목 출력 + 푸터)
- [x] 5B-4: `src/agentbox/__main__.py` 에 status 서브커맨드 추가
- [x] 5B-5: `tests/unit/test_last_init.py` + `tests/unit/test_status_cmd.py` 작성 + PASS

### Phase 5C — /audit HTML 무토큰화
- [x] 5C-1: dashboard `/api/audit` 사용 grep 재확인 (변경 없음 확인)
- [x] 5C-2: `ec2/saas/server.py` 의 `/audit` → `/api/audit` 변경 + `/audit` HTML 핸들러 신규
- [x] 5C-3: SPA fallback 옵션 A 채택(추가 작업 없음)
- [x] 5C-4: `infra/userdata-app.sh.tpl` 에 npm build 단계 추가(best-effort)
- [x] 5C-5: `tests/unit/test_saas_audit_html.py` 작성 + PASS

### Phase 5D — dashboard zip 포함 (선택)
- [x] 5D-1: 빌드 위치 결정 (= EC2 빌드 best-effort 유지, 본 Task 변경 없음)
- [x] 5D-2: `infra/code_dist.tf` 검토만(수정 없음)

### Phase 5E — 단위 테스트 + 회귀
- [x] 5E-1: 신규 단위 테스트 일괄 PASS (27개)
- [x] 5E-2: 기존 단위 테스트 전체 PASS (122개 모두 PASS)
- [x] 5E-3: 신규 모듈 커버리지 80%+ (last_init 100%, set_cmd 81%, status_cmd 96%)

### Phase 5F — 통합 테스트
- [x] 5F-1: `tests/integration/test_set_e2e.py` 작성 + PASS
- [x] 5F-2: `tests/integration/test_status_e2e.py` 작성 + PASS
- [x] 5F-3: `tests/integration/test_audit_html_e2e.py` 작성 + PASS
- [x] 5F-4: 신규 통합 테스트 일괄 PASS (13개)
- [x] 5F-5: 기존 통합 테스트 회귀 PASS (179개 전체 PASS)

### Phase 5G — 실 환경 검증 + 배포
- [ ] 5G-1: 로컬 WSL2 `agentbox set` 동작 확인
- [ ] 5G-2: 로컬 `agentbox status` 출력 확인
- [x] 5G-3: EC2 재배포 완료 (SSM → pre-signed URL → server.py 교체 → systemctl restart agentbox-saas → active)
- [x] 5G-4: `GET /audit` → 200 HTML (무토큰) / `GET /api/audit` → 401 (무토큰) 확인
- [ ] 5G-5: WSL 에서 `claude --print` round-trip 확인

### Phase 5H — 커밋
- [x] 5H-1: `git status` 로 변경 파일 확인
- [x] 5H-2: Phase별 4개 커밋 완료 (5A/5B/5C/5F+5H)
- [ ] 5H-3: 사용자에게 PR 생성 여부 확인(자동 push 금지).

---

## 7. 재실행/재개 규약

1. **세션이 중단된 후 새 세션에서 재개할 때**:
   - 본 Task-5.md 의 §6 체크리스트를 위에서 아래로 훑어 첫 `[ ]` 항목을 식별.
   - 그 항목의 Phase 본문(§4)을 참조하여 단계별 지시 그대로 실행.
   - 신규 파일을 만들기 전 `Read` 또는 `Glob` 으로 동일 파일이 이미 일부 존재하는지 확인. 존재하면 **덮어쓰지 말고 `Edit` 로 패치**.
2. **테스트 실패 시**:
   - 가능한 한 같은 Phase 내에서 원인 분석(import 누락/mock 누락 등). 분석 후 fixture 만 추가하면 PASS 인지 검토.
   - Phase 의 작성 지침과 명확히 모순되는 환경 사실이 발견되면 본 Task-5.md 자체에 `## 부록: 진행 중 발견사항` 섹션을 추가하고 거기에 사실을 기록한 뒤 사용자에게 보고.
3. **사용자 결정이 더 필요한 시점**:
   - 5C-3 SPA fallback 옵션 변경 필요 → 사용자 질문.
   - 5G-3 EC2 재배포 방식 변경 필요(예: terraform 전체 재apply 가 OneDrive lock 으로 실패) → 사용자 질문 + 우회 제안.
   - 그 외에는 본 문서 지시를 신뢰.
4. **본 문서가 갱신될 때**:
   - 코드 변경 commit 과 분리하여 별도 commit. 메시지 `docs(task-5): refine plan based on <reason>`.

---

## 8. 검수 기준 (Definition of Done)

| # | 항목 | 검증 명령 / 절차 |
|---|---|---|
| 1 | `agentbox --help` 가 set, status 를 표시 | `python -m agentbox --help \| grep -E "set\|status"` 가 두 줄 출력 |
| 2 | `agentbox set` 멱등 동작 | 두 번 호출해도 bashrc 라인 개수 동일 |
| 3 | `agentbox status` 가 6항목 + 푸터 출력 | stdout 에 `Made by JeonMyeonghwan` 포함 |
| 4 | `agentbox status --json` 파싱 가능 | `agentbox status --json \| python -c "import json,sys;json.load(sys.stdin)"` 가 무에러 |
| 5 | `last_init.json` 가 `agentbox init` 성공 후 생성 | `cat ~/.agentbox/last_init.json` 가 5개 필드 포함 |
| 6 | EC2 `/audit` 가 토큰 없이 200 HTML | `curl -s -o /dev/null -w "%{http_code}\n" http://<EIP>:8000/audit` → `200` |
| 7 | EC2 `/api/audit` 가 토큰 없이 401 | `curl -s -o /dev/null -w "%{http_code}\n" http://<EIP>:8000/api/audit` → `401` |
| 8 | EC2 `/api/audit` 가 토큰 있을 때 200 JSON | `curl -H "X-Admin-Token: $T" http://<EIP>:8000/api/audit \| python -c "import json,sys;json.load(sys.stdin)"` 가 무에러 |
| 9 | 신규 단위 테스트 8~10개 PASS | `pytest tests/unit/test_set_cmd.py tests/unit/test_status_cmd.py tests/unit/test_last_init.py tests/unit/test_saas_audit_html.py -v` |
| 10 | 신규 통합 테스트 3개 PASS | `pytest tests/integration/test_set_e2e.py tests/integration/test_status_e2e.py tests/integration/test_audit_html_e2e.py -v` |
| 11 | 기존 테스트 회귀 없음 | `pytest -v` 가 Task-4 종료 시점 대비 통과 개수 ≥ |
| 12 | 신규 모듈 커버리지 80%+ | `pytest --cov=agentbox.set_cmd --cov=agentbox.status_cmd --cov=agentbox.last_init` |
| 13 | WSL2 round-trip 성공 (수동 `agentbox on` 후) | 5G-5 의 `claude --print` 가 응답 수신 + `/audit` 에 이벤트 행 표시 |
| 14 | `agentbox set` 후 새 셸의 HTTPS_PROXY 가 자동으로 설정되지 **않음** | `bash -c 'echo $HTTPS_PROXY'` 출력이 빈 문자열 (자동 활성화 금지 검증) |

---

## 9. 위험 요소 및 완화

| 위험 | 영향 | 완화책 |
|---|---|---|
| EC2 user_data 가 dashboard 빌드 단계에서 timeout(npm install 느림) | EC2 부팅 실패 가능 | `\|\| true` 로 비차단. fallback HTML 로 동작. |
| `~/.bashrc` 가 사용자 커스텀으로 가득해 marker 추가가 충돌 | `agentbox on/off` 함수가 다른 함수에 가려짐 | marker 기반 중복 검사. 추가 시 파일 마지막에 append. 사용자가 알 수 있도록 stdout 출력. |
| OneDrive sync 가 terraform.tfstate 잠금 | deploy.sh 실패 (memory: feedback_onedrive_terraform.md) | 5G-3 에서 사용자에게 "OneDrive 일시중지 후 진행" 명시. systemctl restart 우회 경로 우선 제안. |
| `/audit` 가 HTML 을 주면 봇/스크래퍼가 페이지를 인덱싱 | 정보 노출(미미) | HTML 안에 실제 데이터 없음. robots.txt 추가는 후속 Task. |
| Windows 에서 `agentbox set` 호출 시 ~/.bashrc 미존재 | 동작 실패 | Windows 감지 시 "WSL 안에서 실행하세요" 안내 후 비차단 종료(exit 0 또는 1, 결정은 5A-1 시 사용자 확인). |
| `dashboard/dist` 가 빌드되지 않은 채 zip 됨 | `/audit` 가 fallback HTML 만 표시 | 옵션 A 유지. dist 가 없어도 로그인 후 `/api/audit` JSON 직접 호출 가능(curl/Postman). |

---

## 10. 작성 시 주의사항 (사용자 명시)

1. **함수 이름만 보지 말고 본문 직접 확인** — `ensure_ca`, `_setup_shell`, `_require_admin` 등은 모두 본문을 §3 의 변경 매트릭스 작성 전 확인 완료.
2. **애매한 부분은 AskUserQuestion** — 4가지 질문 진행, 답변 §0.1 에 반영.
3. **모호한 부분 없도록** — 각 5A-X / 5B-X 단계가 어떤 함수를 만들고 어떤 인자를 받는지 명시. 검증 명령 포함.
4. **UTF-8 획일화** — §5 참조. 코드 / JSON / 로그 / 본 문서 모두 UTF-8.
5. **재실행 가능** — §6 체크리스트 + §7 재실행 규약 참조.

---

> **다음 단계**: 사용자가 본 Task-5.md 를 검토 후 "Task-5 시작" 을 명시하면 §6 의 5A-1 부터 순차 실행. 그 전까지 코드 변경 일절 금지.
