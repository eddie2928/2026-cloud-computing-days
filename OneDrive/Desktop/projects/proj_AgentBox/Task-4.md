# Task-4: `agentbox init` 명령 + MCP Tool 2종 (list_project_files / decrypt_and_stage chunked) + Bedrock Agent 재구성

> 본 문서는 Task-3 완료(Bedrock Agent + MCP 분리 + 토큰 카운터/cleanup 호출 추가) 상태를 전제로,
> ① 사용자 CLI **`agentbox init <dir>`** 신설(프로젝트 전체 .enc 업로드 + 설정/의존성 확인 + EC2 연결성 점검 + 대시보드 URL 출력),
> ② MCP Server에 **`list_project_files`** 신규 + **`decrypt_and_stage`** 시그니처 변경(files 리스트·start_byte·max_bytes로 chunked 응답),
> ③ Lambda mcp_bridge / Bedrock Agent action_group / Agent system instruction 동기 갱신,
> ④ kb_staging 버킷·관련 IAM·코드 경로 **완전 제거**,
> ⑤ pytest + moto + responses 기반 단위/통합 테스트 추가,
> ⑥ 재배포 + 실 AWS 라운드트립 검증을 수행한다.
>
> 모든 변경은 **재실행 가능한 step** 으로 구성되며, 각 단계 종료 시 자동/수동 검증을 통과해야 다음 단계로 넘어간다.
>
> 인코딩: UTF-8 (BOM 없음)
> 작성일: 2026-05-11

---

## 0. 메타 정보

| 항목 | 값 |
|---|---|
| Task ID | Task-4 |
| 선행 조건 | Task-3 Phase 3A~3G 완료. `infra/` apply 가 끝나 있고, app-EC2/mcp-EC2 가 active 상태. Bedrock Agent 가 `decrypt_and_stage` 1개 action_group 으로 동작 중. |
| 대상 OS | Endpoint: WSL2 Ubuntu 22.04 / Windows 11(파이썬 직접 실행도 허용) / App-EC2: Ubuntu 22.04 / MCP-EC2: Ubuntu 22.04 |
| 핵심 변경 | ① `agentbox init <dir>` CLI 추가(설정 확인 → 의존성 확인+자동설치 프롬프트 → 암호화/업로드 → EC2 연결성 확인 → 대시보드 URL 출력), ② MCP에 `GET /mcp/list_files/{project_id}` 신설(Markdown flat list 반환), ③ `POST /mcp/decrypt_and_stage` 시그니처 변경(`files: List[str], start_byte: int = 0, max_bytes: int = 20480` + 응답 `files: [{path, content, is_binary, size, returned_bytes, next_offset, truncated}]`), ④ Lambda mcp_bridge 가 Bedrock Action Group 파라미터를 위 두 인터페이스에 매핑, ⑤ infra/bedrock.tf 에 action_group 2개로 분리 + Agent instruction 증분 갱신, ⑥ kb_staging 버킷 + IAM 정책 + put/cleanup 경로 모두 제거, ⑦ 단위/통합 테스트 신규 작성. |
| Capex 변동 | $0 (리소스 추가 없음, kb_staging 제거로 오히려 S3 PUT 비용 ↓). Bedrock Agent prepare 호출 1회만 추가. |
| 코드 수정 금지 | 본 문서 사용자 검토 및 "Task-4 시작" 명시 지시 전까지 일절 코드 변경 금지. |

### 0.1 모든 사용자 결정 사항 요약 (AskUserQuestion 답변 기반)

| 결정 항목 | 값 | 근거 질문 |
|---|---|---|
| PROJECT_ID 결정 방식 | `Path(dir).resolve().name` (dir의 basename 그대로) | Q1 |
| 대시보드 URL | 기존 SaaS URL(`http://<app_public_ip>:8000`) 그대로 출력 | Q2 |
| MCP Tool #2 파일 선택 인터페이스 | `files: List[str]` (다중 상대경로) | Q3 |
| Dependency 처리 범위 | 확인 + 자동설치 (프롬프트 후) | Q4 |
| EC2 Connectivity 확인 | SaaS :8000 `/healthz` HTTP GET + gRPC :50051 `socket.connect()` TCP 도달 | Q5 |
| Bedrock 응답 전달 방식 | **KB 안 씀.** 파일 내용을 tool 응답 본문에 직접 담아 반환 (chunked) | Q6 |
| MCP Tool #1 출력 포맷 | Markdown flat list (path · size · is_binary · modified) | Q7 |
| Agent Prompt 변경 정책 | 기존 prompt 유지 + 신규 tool 사용 방법 섹션만 증분 추가 | Q8 |
| Bedrock Agent 갱신 방법 | `infra/bedrock.tf` 수정 후 `terraform apply` (Agent / Action Group 재생성) | Q9 |
| Chunking 인터페이스 | `decrypt_and_stage(files, start_byte, max_bytes)` 단일 tool. 응답에 `next_offset`/`truncated`. | Q10 |
| kb_staging 처리 | **완전 제거** (terraform 리소스 삭제 + 코드 경로 제거) | Q11 |
| 이진 파일 처리 | 텍스트 파일만 본문 반환. 이진은 `{"is_binary": true, "size": N}` 메타데이터만. base64 인코딩 안 함. | Q12 |
| 테스트 도구 | 기존 스택 유지: pytest + moto + responses (추가 의존성 없음) | Q13 |

---

## 1. 목표

1. **사용자 진입점 단순화**: 사용자가 신규 프로젝트 `~/code/myapp` 을 검사 대상에 등록하려면 `agentbox init ~/code/myapp` 한 줄이면 충분. 내부에서 의존성 점검 → 암호화 업로드 → EC2 연결성 확인 → SaaS URL 출력까지 자동.
2. **Bedrock Agent 가 평문 파일 접근 가능**: KB 우회. Bedrock Agent 가 (a) `list_project_files(project_id)` 호출로 파일 목록을 받고, (b) 의심스러운 파일들에 대해 `decrypt_and_stage(files=[...], start_byte=0, max_bytes=20480)` 를 호출하면 **MCP 가 SOPS 복호화 → 평문 본문을 응답에 포함**해 반환. 대용량 파일은 LLM 이 `next_offset` 으로 재호출.
3. **kb_staging 의존 완전 제거**: 평문이 더 이상 S3 에 영구/임시 보관되지 않는다. MCP 내부 temp 파일은 zero-fill 후 unlink, 응답 송신 직후 garbage collect. 평문이 디스크 영구화되는 경로 없음(=Zero-Knowledge 보장 강화).
4. **재배포 1-커맨드 유지**: Task-3 의 `./scripts/deploy.sh` 가 신규 코드 zip 만 새로 만들어 동일하게 동작. terraform apply 가 Agent action_group/Lambda code/EC2 user_data 를 갱신.
5. **테스트 자동화**: 신규 두 tool + 변경된 Lambda + 변경된 `agentbox init` 에 대한 단위/통합 테스트 신규 작성 + 기존 테스트 전부 PASS 유지.

---

## 2. 아키텍처

### 2.1 변경 전 (Task-3 종료 시점)

```
Endpoint(WSL2)                            AWS
─────────────                             ─────────────────────────────
mitmproxy → gRPC client → app-EC2:50051
                              │
                              ▼ (Bedrock InvokeAgent)
                        Bedrock Agent (Claude Sonnet 4.6)
                              │ action_group: decrypt_and_stage(project_id)
                              ▼
                        Lambda mcp_bridge (in VPC)
                              │ POST /mcp/decrypt_and_stage
                              ▼
                        MCP-EC2 :8080
                              │ ① S3 list_objects (encrypted_code/<pid>/)
                              │ ② SOPS decrypt 전체
                              │ ③ kb_staging put 전체   ← 평문이 S3 보관됨
                              │ ④ response {kb_bucket, prefix}
                              ▼
                        Bedrock Agent → KB 검색 시도 (현재 KB attach 안돼있어 사실상 사용 안됨)
                              │
                              ▼ verdict JSON
                        app-EC2 ← DELETE /mcp/cleanup/{event_id}
```

### 2.2 변경 후 (Task-4 목표)

```
Endpoint(WSL2/Win)                        AWS
─────────────                             ─────────────────────────────
agentbox init <dir>
  ├─ deps check + auto-install prompt
  ├─ scripts/encrypt_and_upload.sh <dir>  ───► s3://agentbox-encrypted-code/encrypted_code/<basename>/*.enc
  ├─ EC2 connectivity check
  │    GET http://<app_public_ip>:8000/healthz   (HTTP)
  │    socket.connect((<app_public_ip>, 50051))  (TCP)
  └─ print SaaS dashboard URL

(이후 mitmproxy 라이프사이클)
mitmproxy → gRPC client → app-EC2:50051
                              │
                              ▼ Bedrock InvokeAgent
                        Bedrock Agent (Claude Sonnet 4.6)
                              │
                              ├── action_group: list_project_files(project_id)        ← 신규
                              │       Lambda → MCP GET /mcp/list_files/{pid}
                              │       MCP → S3 list_objects → Markdown 응답
                              │
                              ├── action_group: decrypt_and_stage(files,start_byte,   ← 시그니처 변경
                              │                                  max_bytes)
                              │       Lambda → MCP POST /mcp/decrypt_and_stage
                              │       MCP → S3 GetObject (files만) → SOPS decrypt
                              │              → 텍스트 본문(≤ max_bytes) + next_offset
                              │              → 응답 직후 평문 zero-fill (S3 보관 X)
                              │
                              └── verdict 결정
                              ▼
                        app-EC2 (cleanup 호출 제거 — kb_staging 없음)
```

### 2.3 Zero-Knowledge 관점 변경

| 자원 | Task-3 | Task-4 |
|---|---|---|
| 평문 디스크 보관 위치 | mcp-EC2 의 `/tmp/*.enc` (subprocess 동안) + S3 `kb-staging` (cleanup 전까지) | mcp-EC2 의 `/tmp/*.enc` (subprocess 1회 동안) **만** |
| 평문 수명 | cleanup API 호출까지 (수십초~분) | tool 응답 송신 직후 (수밀리초) |
| 외부 노출 면적 | KB 데이터소스(`kb-staging` S3 GetObject) | 없음 (Lambda → MCP HTTP 응답 본문에만 평문 존재, VPC private 통신) |

---

## 3. 디렉터리 / 파일 변경 매트릭스

| 경로 | 동작 | 비고 |
|---|---|---|
| `src/agentbox/__main__.py` | 수정 | `argparse` 에 `init` subparser 추가. `dir` positional + `--project-id` optional + `--skip-deps` flag. `_init(dir, project_id, skip_deps)` 함수 호출. |
| `src/agentbox/init_cmd.py` | **신규** | `agentbox init` 본체. 단계: 1) 의존성 점검(`_check_deps`), 2) 사용자 프롬프트(`_prompt_install`), 3) 암호화/업로드(`_encrypt_upload`), 4) EC2 연결성(`_check_connectivity`), 5) URL 출력. 모든 단계는 별도 함수로 분리되어 단위 테스트 가능. |
| `src/agentbox/init_deps.py` | **신규** | 의존성 매트릭스 정의. `DEPS = [Dep(name="sops",check_cmd="sops --version",install_hint="...")]`. macOS/Linux/Windows 분기. boto3/pyyaml 등 pip 패키지는 `importlib.metadata.version` 으로 확인. |
| `ec2/mcp_server/server.py` | 수정 | 1) `decrypt_and_stage` 시그니처 전면 변경(`files: list[str], start_byte: int = 0, max_bytes: int = 20480`), 2) 신규 엔드포인트 `GET /mcp/list_files/{project_id}` (Markdown 응답), 3) `kb_staging` put/cleanup 코드 전부 삭제, 4) `DELETE /mcp/cleanup/{session_id}` 엔드포인트 자체 삭제(연쇄 정리). 5) 이진 파일 감지(`_is_binary_bytes` 헬퍼: 첫 8KB 안에 NULL 바이트 또는 비ASCII 비율 30%↑). |
| `ec2/grpc_server/server.py` | 수정 | `requests.delete(f"{_MCP_SERVER_URL}/mcp/cleanup/...")` 호출 제거(Phase 3C-2 에서 추가했던 것). 토큰 카운터(`_increment_token_count`) 호출은 유지. |
| `lambda/mcp_bridge.py` | 수정 | Bedrock event 의 `function` 필드로 분기. `list_project_files` 면 `GET /mcp/list_files/{pid}`, `decrypt_and_stage` 면 `POST /mcp/decrypt_and_stage` (body: files/start_byte/max_bytes). 응답을 `responseBody.TEXT.body` 에 JSON 또는 Markdown 으로 직렬화. **응답 크기 25600 자 초과 시 `truncated:true` + `next_offset` 보존 책임은 MCP 가 짐, Lambda 는 그대로 패스스루.** |
| `infra/bedrock.tf` | 수정 | 1) `aws_bedrockagent_agent_action_group.decrypt_and_stage` 의 `function_schema.functions` 에 `start_byte`/`max_bytes`/`files` 파라미터 정의(기존 `project_id` 제거). 2) `aws_bedrockagent_agent_action_group.list_project_files` 신규 리소스(파라미터: `project_id`). 3) `aws_bedrockagent_agent.inspector.instruction` 의 system prompt 끝에 "## Tools" 섹션 증분 추가(별도 파일 `infra/bedrock_tools_addendum.txt` 로 분리하여 `file()` concat). 4) `aws_bedrockagent_agent_alias.live` 는 그대로(prepare 자동 트리거). |
| `infra/bedrock_tools_addendum.txt` | **신규** | system instruction 증분 텍스트. 정확한 문구는 §4.5 Phase 4D-2 에 명시. |
| `infra/s3.tf` | 수정 | `aws_s3_bucket.kb_staging` 및 관련 `aws_s3_bucket_policy`, `aws_s3_bucket_server_side_encryption_configuration`, `aws_s3_bucket_public_access_block` 모두 **삭제**. |
| `infra/ec2.tf` | 수정 | mcp-role 의 inline policy 에서 kb_staging 버킷에 대한 PutObject/DeleteObject/GetObject/ListBucket 권한 statement 삭제. encrypted-code 의 GetObject 권한은 유지. |
| `infra/kms.tf` | 미변경 | KMS 키 정책은 mcp-role 만 Decrypt 권한. 변경 없음. |
| `infra/lambda.tf` | 미변경 | `MCP_SERVER_URL` 환경변수 유지. Action group lambda 함수 ARN 동일. |
| `scripts/encrypt_and_upload.sh` | 수정(소폭) | 1) `PROJECT_ID` 결정 로직을 명시 출력(`echo "[agentbox] PROJECT_ID=$PROJECT_ID"`). 2) 텍스트 vs 이진 구분 없이 모두 SOPS 로 암호화(SOPS 자체는 binary 도 처리 가능, `--input-type binary --output-type binary`). 3) `--encrypted-suffix .enc` 옵션은 SOPS 가 자동 처리하지 않으므로 기존처럼 `.enc` 를 stdin/output 리다이렉트로 부착. **본 스크립트는 `agentbox init` 내부에서 `subprocess.run` 으로 호출**. 4) Windows 환경에서도 Git Bash/WSL 경유 호출 가능하도록 path 정규화는 init_cmd.py 가 담당. |
| `scripts/deploy.sh` | 미변경 | code_dist.tf 가 archive_file 로 코드 zip 을 재생성하므로 init_cmd.py 추가만으로 자동 반영. |
| `tests/unit/test_init_cmd.py` | **신규** | `_check_deps`/`_encrypt_upload`/`_check_connectivity`/`_print_url` 단위 테스트. subprocess/socket/requests 모두 mock. tmp_path 로 fake project dir 생성. |
| `tests/unit/test_init_deps.py` | **신규** | DEPS 매트릭스 각 항목별로 `check_cmd` 가 정상/실패할 때의 동작 검증. |
| `tests/unit/test_mcp_list_files.py` | **신규** | moto S3 mock + FastAPI TestClient. encrypted_code/<pid>/*.enc 3개 fixture → `GET /mcp/list_files/<pid>` 결과 Markdown 파싱 → 3개 row, path/size/is_binary 컬럼 검증. |
| `tests/unit/test_mcp_decrypt_chunked.py` | **신규** | (a) 소형 텍스트 파일 1개 → `start_byte=0, max_bytes=20480` → 전체 본문 반환 + `truncated=false`. (b) 30KB 파일 1개 → 첫 호출 `truncated=true, next_offset=20480` → 두 번째 호출로 잔여 본문. (c) 이진 파일 1개 → `is_binary=true, content=null`. (d) 존재하지 않는 path → `error: "not found"`. |
| `tests/unit/test_lambda_mcp_bridge_v2.py` | **신규** | Bedrock event `function="list_project_files"` 분기 + `function="decrypt_and_stage"` 분기 각각 검증. responses 로 MCP 응답 mock. |
| `tests/integration/test_init_e2e.py` | **신규** | moto S3+KMS mock. `tmp_path` 에 fake project(텍스트 2개 + 이진 1개) → `agentbox init <tmp_path>` 호출 → S3 에 .enc 3개 생성 확인 → connectivity 단계는 monkeypatch 로 성공 응답 주입 → SaaS URL stdout 검증. |
| `tests/integration/test_mcp_full_flow_v2.py` | **신규** | 실제 sops 바이너리(없으면 skip) + moto S3+KMS. encrypted_code 에 SOPS 로 암호화한 텍스트 3개 업로드 → MCP FastAPI TestClient → list_files → decrypt 첫 chunk → decrypt 두 번째 chunk(next_offset 사용) → 모든 응답 정합성 검증. |
| `tests/integration/test_terraform_plan_v2.py` | **신규** | Task-3 `tests/terraform/test_plan_resources.py` 의 8개 assert 외에, kb_staging 관련 리소스가 plan 에 **존재하지 않음** assert + action_group 리소스가 정확히 2개 존재 assert. |
| `tests/unit/test_grpc_no_cleanup.py` | **신규** | grpc_server `Inspect` 호출 후 `requests.delete` 가 호출되지 **않음** 을 검증(responses.calls 비어있음). 토큰 카운터는 여전히 1회 호출. |
| `pyproject.toml` 또는 `requirements-dev.txt` | 미변경 | 의존성 추가 없음. 기존 pytest/moto/responses 그대로. |

---

## 4. 단계별 작업 계획 (Phase)

> 각 Phase 는 **자체 완결 검증** 을 가진다. Plan 이 중간에 끊겨도 §8 TODO 마스터 체크리스트의 가장 최근 미체크(`- [ ]`) Phase 부터 재시작 가능.
> Phase 간 의존성: 4A → 4B → 4C → 4D → 4E → 4F → 4G.
> 단, 4E(단위 테스트) 는 4B 완료 후 부분 시작 가능. 4F(통합) 는 4E 완료 후만.

---

### Phase 4A — `agentbox init` CLI 신설

**목적**: 사용자 단일 명령으로 의존성 점검 → 암호화/업로드 → EC2 연결성 → 대시보드 URL 출력 완료.

- [ ] **4A-1** `src/agentbox/init_deps.py` 작성
  - 모듈 상단에 `@dataclass(frozen=True) class Dep: name: str; check_cmd: list[str]; install_hint_linux: str; install_hint_macos: str; install_hint_windows: str; required: bool = True`.
  - `DEPS` 리스트:
    ```python
    DEPS = [
        Dep("sops", ["sops", "--version"],
            install_hint_linux="curl -fsSL https://github.com/getsops/sops/releases/download/v3.12.2/sops-v3.12.2.linux.amd64 -o /usr/local/bin/sops && chmod +x /usr/local/bin/sops",
            install_hint_macos="brew install sops",
            install_hint_windows="winget install -e --id Mozilla.Sops"),
        Dep("aws", ["aws", "--version"],
            install_hint_linux="sudo apt-get install -y awscli",
            install_hint_macos="brew install awscli",
            install_hint_windows="winget install -e --id Amazon.AWSCLI"),
    ]
    PYTHON_PACKAGES = ["boto3", "pyyaml"]  # importlib.metadata.version 로 확인
    ```
  - 함수 `check_dep(dep: Dep) -> tuple[bool, str | None]`: `subprocess.run(dep.check_cmd, capture_output=True, timeout=5)` returncode==0 이면 OK. exception/nonzero 면 `(False, stderr.decode()[:200])`.
  - 함수 `check_python_pkg(name: str) -> bool`: `importlib.metadata.version(name)` → exception 없으면 True.
  - 함수 `try_auto_install(dep: Dep) -> bool`: `install_hint_<platform>` 쉘 명령을 subprocess 로 실행. shell=True 사용은 install_hint 가 단순 1라인이며 사용자 prompt 동의를 받은 후라는 전제. 실행 후 다시 `check_dep` 호출하여 성공 여부 반환.
  - 검증: `pytest tests/unit/test_init_deps.py` PASS.

- [ ] **4A-2** `src/agentbox/init_cmd.py` 작성 — 메인 흐름 함수 `init(dir: str, project_id: str | None = None, skip_deps: bool = False, auto_yes: bool = False) -> int`.
  1. **Step 1 — 경로 검증**:
     - `src = Path(dir).expanduser().resolve()`.
     - `if not src.is_dir(): print error; return 2`.
     - `pid = project_id or src.name` (= basename).
     - `print(f"[agentbox] PROJECT_ID={pid}")`.
  2. **Step 2 — 설정 파일 확인**:
     - `.sops.yaml` 존재 + placeholder(`{region}` 문자열 검색 → 미포함) 검증.
     - `<project_root>/.env.endpoint` 존재 + `EC2_GRPC_HOST` 키 존재(=Task-3 deploy.sh 결과물).
     - terraform output(`saas_url`)을 가져오는 보조 함수 호출 시도(아래 4A-3).
     - 실패시 `return 3` + 설정 가이드 출력.
  3. **Step 3 — 의존성 점검**:
     - `if skip_deps: pass`. 아니면 각 `DEP` 에 대해 `check_dep` 수행. 실패한 것만 모아 사용자에게:
       ```
       [agentbox] 누락된 의존성: sops, aws
       자동 설치를 시도할까요? [y/N]:
       ```
     - `auto_yes` 면 묻지 않음. `y` 면 `try_auto_install` 순서대로 호출. 모두 성공해야 다음 단계, 하나라도 실패하면 install_hint 출력 후 `return 4`.
     - Python 패키지는 import 가 이미 끝났으므로 본 init 이 import 가능했다 = OK. 다만 future-proof 로 `check_python_pkg` 도 출력만 진행.
  4. **Step 4 — 암호화 + 업로드**:
     - 환경변수 `PROJECT_S3_BUCKET=<project_name>-encrypted-code`, `PROJECT_ID=<pid>` 설정.
     - `subprocess.run(["bash", str(_PROJ_ROOT / "scripts/encrypt_and_upload.sh"), str(src)], env=..., check=False)`.
     - returncode != 0 이면 마지막 stderr 마지막 30줄 출력 후 `return 5`.
     - Windows 환경 검출 시: `wsl bash scripts/encrypt_and_upload.sh` 자동 prefix(WSL 설치 가정). WSL 없으면 안내 후 `return 5`.
  5. **Step 5 — EC2 connectivity**:
     - `app_public_ip = .env.endpoint 의 EC2_GRPC_HOST 값` (또는 `terraform output -raw app_public_ip`).
     - `saas_url = "http://" + app_public_ip + ":8000"` (또는 terraform output `saas_url`).
     - HTTP check: `requests.get(saas_url + "/healthz", timeout=5)` → 200 OK 가 아니면 에러 메시지 + 가능한 원인 5개(SG ingress / SaaS systemctl status / EIP 변경 / endpoint subnet egress / DNS) 출력 후 `return 6`.
     - TCP check: `with socket.create_connection((app_public_ip, 50051), timeout=5):` → 실패 시 에러 + 원인(SG 50051 ingress, gRPC systemd, mTLS 사전 ssl handshake 는 시도 안 함) 출력 후 `return 7`.
  6. **Step 6 — 성공 출력**:
     - `print(f"[agentbox] init OK. 대시보드: {saas_url}")`.
     - `return 0`.
  - 모든 print 는 logger 도 같이 호출(`logger.info` / `logger.error`). 로그 파일은 `logs/agentbox-init-<timestamp>.log`. (Task CLAUDE.md §5: 감사용 로그.)
  - 검증: `pytest tests/unit/test_init_cmd.py` PASS.

- [ ] **4A-3** `src/agentbox/init_cmd.py` 헬퍼 `get_terraform_output(name: str) -> str | None`
  - `subprocess.run(["terraform","-chdir=infra","output","-raw",name], capture_output=True, timeout=10)`.
  - returncode==0 이면 stdout strip 후 반환. 아니면 None.
  - `init()` 의 Step 2 에서 saas_url 가져올 때 fallback 으로 사용.

- [ ] **4A-4** `src/agentbox/__main__.py` 의 `main()` 에 `init` subparser 추가
  ```python
  p_init = sub.add_parser("init", help="Encrypt+upload a project, verify EC2, print dashboard URL")
  p_init.add_argument("dir")
  p_init.add_argument("--project-id", default=None)
  p_init.add_argument("--skip-deps", action="store_true")
  p_init.add_argument("-y", "--yes", action="store_true", help="자동 설치 prompt 건너뛰고 동의")
  ```
  - `args.cmd == "init"` 분기에서 `from agentbox.init_cmd import init; sys.exit(init(args.dir, args.project_id, args.skip_deps, args.yes))`.
  - 검증: `python -m agentbox init --help` 출력에 4개 옵션 보임.

- [ ] **4A-5** `scripts/encrypt_and_upload.sh` 수정
  - 본문 시작부에 `echo "[agentbox] PROJECT_ID=$PROJECT_ID"` 추가.
  - `find "$SRC_DIR" -type f` 직후 `find -size +50M` 경고(있으면 stderr).
  - 검증: `bash -n scripts/encrypt_and_upload.sh` 통과 + `PROJECT_S3_BUCKET=fake PROJECT_ID=test bash scripts/encrypt_and_upload.sh <임시디렉토리>` 가 (실 AWS 호출 직전 줄에서 실패해도) PROJECT_ID 출력은 됨.

**Phase 4A Gate**: 
- 단위 테스트 `tests/unit/test_init_deps.py`, `tests/unit/test_init_cmd.py` PASS (의존성 mock + subprocess mock).
- 수동: 가짜 디렉토리(`mkdir /tmp/sample && echo hi > /tmp/sample/a.txt`)로 `python -m agentbox init /tmp/sample --skip-deps -y` 실행 시 Step 4 까지 진행되어 실 AWS 업로드 시도(권한 OK 인 환경) 또는 의도된 에러.

---

### Phase 4B — MCP Server tool 2종 신설/변경

> Task-3 의 `ec2/mcp_server/server.py` 를 다음과 같이 전면 개편. kb_staging 코드 경로는 **삭제**.

- [ ] **4B-1** `_KB_STAGING_BUCKET` 상수 + 관련 코드 전부 제거
  - `_KB_STAGING_BUCKET = f"{_PROJECT}-kb-staging"` 라인 삭제.
  - `decrypt_and_stage` 내부에서 kb_staging 에 put 하는 블록 삭제.
  - `/mcp/cleanup/{session_id}` 엔드포인트 핸들러 함수 삭제.
  - 검증: `grep -i kb_staging ec2/mcp_server/server.py` → 0 hit.

- [ ] **4B-2** `_is_binary_bytes(data: bytes) -> bool` 헬퍼 추가
  - 알고리즘: 처음 8192 바이트(또는 전체) 안에 NUL 바이트(`b"\x00"`) 가 1개라도 있으면 True. 또는 ASCII 범위(0x09, 0x0A, 0x0D, 0x20~0x7E) 비율이 70% 미만이면 True. 그 외 False.
  - 단위 테스트로 직접 검증.

- [ ] **4B-3** `GET /mcp/list_files/{project_id}` 엔드포인트 신설
  - 입력: path param `project_id`. `Authorization: Bearer <admin_token>` 검증(`_verify_token`).
  - 동작:
    1. `_s3.list_objects_v2(Bucket=_ENCRYPTED_CODE_BUCKET, Prefix=f"encrypted_code/{project_id}/")` 페이지네이션 처리(`Paginator`).
    2. 각 객체의 Key 에서 `encrypted_code/<pid>/` prefix 제거 + `.enc` 접미사 제거 → 원본 상대경로 복원.
    3. **is_binary 판정**: list 결과의 Key 확장자가 다음 집합이면 binary 로 표시: `{.png,.jpg,.jpeg,.gif,.webp,.pdf,.zip,.tar,.gz,.exe,.dll,.so,.dylib,.bin,.mp3,.mp4,.mov,.wav}`. (Phase 4B-2 의 `_is_binary_bytes` 는 decrypt 시점 실제 검사용. list 시점은 확장자 휴리스틱.)
    4. 응답 본문(Markdown 텍스트):
       ```
       # Project files: <project_id>
       Total: <count> files, <total_size_bytes> bytes encrypted

       | Path | Size (encrypted bytes) | Is Binary | Last Modified (UTC) |
       |---|---|---|---|
       | src/main.py | 1234 | false | 2026-05-11T03:22:01Z |
       | ...
       ```
     - Content-Type: `text/markdown; charset=utf-8`.
  - 반환 시 응답 본문 길이를 logger.info 로 기록.
  - 검증: `tests/unit/test_mcp_list_files.py` 5개 케이스(0 files / 1 file / 3 files / paged 1500 files / project_id 존재 안함).

- [ ] **4B-4** `POST /mcp/decrypt_and_stage` 전면 개편
  - 입력 모델:
    ```python
    class DecryptRequest(BaseModel):
        project_id: str
        files: list[str]                 # 상대경로. 빈 리스트 금지(422).
        start_byte: int = 0              # 0 이상.
        max_bytes: int = 20480           # 기본 20KB. 응답 전체가 25KB 한도이므로 보수적.
    class FileChunk(BaseModel):
        path: str
        is_binary: bool
        size: int                        # 평문 전체 크기(바이트)
        returned_bytes: int              # 이번 응답에 담긴 본문 크기
        next_offset: int | None          # 더 가져올 게 있으면 다음 호출 start_byte. 없으면 null.
        truncated: bool                  # max_bytes 로 잘렸으면 true
        content: str | None              # 텍스트면 utf-8 디코드 문자열, 이진이면 null
        error: str | None                # 파일 없음/decrypt 실패 등
    class DecryptResponse(BaseModel):
        project_id: str
        files: list[FileChunk]
    ```
  - 동작 (files 리스트 각 항목 순회):
    1. S3 key = `f"encrypted_code/{project_id}/{rel_path}.enc"`. download to temp file.
    2. `subprocess.run(["sops","--decrypt","--input-type","binary","--output-type","binary",enc_path], capture_output=True, timeout=30)`.
    3. returncode != 0 → `FileChunk(path=rel,error="decrypt_failed: <stderr 80자>",size=0,returned_bytes=0,next_offset=null,truncated=false,is_binary=false,content=null)`.
    4. 성공 → plaintext bytes (`buf`). `is_binary = _is_binary_bytes(buf)`.
       - 이진: `content=None`, `returned_bytes=0`, `next_offset=None`, `truncated=False`, `size=len(buf)`.
       - 텍스트: 
         - `chunk = buf[start_byte : start_byte + max_bytes]`.
         - `try: content = chunk.decode("utf-8")` 실패 시 `errors="replace"` 적용 + logger.warning.
         - `returned_bytes = len(chunk)`.
         - `truncated = (start_byte + len(chunk)) < len(buf)`.
         - `next_offset = start_byte + len(chunk) if truncated else None`.
    5. `buf[:] = b"\x00" * len(buf)` (zero-fill) 후 temp 파일 unlink.
  - 응답 전체 직렬화 후 byte 길이가 24KB 초과면 logger.warning(LLM 응답 잘림 가능). 단, 호출자(Lambda)가 25.6KB 한도 위반 책임을 지지 않음.
  - 검증: `tests/unit/test_mcp_decrypt_chunked.py` 6개 케이스(텍스트 단일, 텍스트 chunked 2회, 이진 단일, 다중 파일 혼합, 파일 없음, decrypt 실패).

- [ ] **4B-5** `MCP_PORT` 기본값 8080 유지. `/healthz` 그대로 유지.
  - 검증: `grep -n '8080' ec2/mcp_server/server.py` 와 기존 동일 라인.

**Phase 4B Gate**: `pytest tests/unit/test_mcp_list_files.py tests/unit/test_mcp_decrypt_chunked.py -v` 100% PASS. `python -c "import ec2.mcp_server.server"` 시 syntax/import 에러 없음.

---

### Phase 4C — Lambda mcp_bridge + grpc_server cleanup 제거

- [ ] **4C-1** `lambda/mcp_bridge.py` 재작성
  - 분기:
    ```python
    fn_name = event.get("function", "")
    params = {p["name"]: p["value"] for p in event.get("parameters", [])}
    project_id = params.get("project_id", "default")
    mcp = os.environ["MCP_SERVER_URL"]
    headers = {"Authorization": f"Bearer {os.environ.get('MCP_ADMIN_TOKEN','')}"}

    if fn_name == "list_project_files":
        url = f"{mcp}/mcp/list_files/{project_id}"
        req = urllib.request.Request(url, method="GET", headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8")
        body = text
    elif fn_name == "decrypt_and_stage":
        files_csv = params.get("files", "")
        files = [f.strip() for f in files_csv.split(",") if f.strip()]
        start_byte = int(params.get("start_byte", "0"))
        max_bytes = int(params.get("max_bytes", "20480"))
        payload = json.dumps({"project_id": project_id, "files": files,
                              "start_byte": start_byte, "max_bytes": max_bytes}).encode()
        req = urllib.request.Request(f"{mcp}/mcp/decrypt_and_stage",
                                     data=payload, method="POST",
                                     headers={**headers, "Content-Type":"application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")  # JSON 문자열
    else:
        body = json.dumps({"error": f"unknown function: {fn_name}"})
    ```
  - **중요**: Bedrock action_group parameter 는 모두 string 타입만 지원. 따라서 `files` 는 콤마 구분 문자열로 받음. 시스템 prompt 에 명시.
  - 반환:
    ```python
    return {"response": {"actionGroup": event["actionGroup"],
                         "function": fn_name,
                         "functionResponse": {"responseBody": {"TEXT": {"body": body}}}}}
    ```
  - 검증: `tests/unit/test_lambda_mcp_bridge_v2.py`.

- [ ] **4C-2** `ec2/grpc_server/server.py` 의 `_invoke_bedrock_agent` 직후 `requests.delete(... /mcp/cleanup ...)` 호출 라인 **삭제**
  - Task-3 Phase 3C-2 에서 추가했던 try/except 블록 통째로 제거.
  - 토큰 카운터 `_increment_token_count(tokens_used)` 호출은 **유지**.
  - 검증: `grep -n "mcp/cleanup" ec2/grpc_server/server.py` → 0 hit.
  - 검증: `tests/unit/test_grpc_no_cleanup.py` PASS.

**Phase 4C Gate**: 모든 변경된 파일이 mypy/ruff(있다면) 통과. import 가능. 단위 테스트 PASS.

---

### Phase 4D — `infra/bedrock.tf` action_group 2개로 분리 + Prompt 증분

> **용어**: Bedrock Agent Action Group 의 `function_schema.functions[*].parameters` 는 OpenAPI-like 스키마. 모든 parameter type 은 string/number/boolean/integer 중 하나. **array 직접 지원 없음** → `files` 는 string 으로 받고 Lambda 가 CSV split. 시스템 prompt 에서 LLM 에게 명시.

- [ ] **4D-1** `infra/bedrock_tools_addendum.txt` 신규 작성. 정확한 본문(따옴표/줄바꿈 포함):
  ```
  
  ## Tools
  
  You have two action group tools available.
  
  ### list_project_files(project_id: string) -> markdown text
  Returns a markdown table of all encrypted files in the project, with columns: Path, Size (encrypted bytes), Is Binary, Last Modified (UTC). Call this FIRST when you need to understand a project's structure. The path is the original relative path inside the source directory.
  
  ### decrypt_and_stage(project_id: string, files: string, start_byte: integer, max_bytes: integer) -> JSON
  - files: comma-separated relative paths, e.g. "src/main.py,config.yaml". Must be paths that appeared in list_project_files output.
  - start_byte: starting byte offset within the plaintext file. Use 0 for the first call.
  - max_bytes: maximum bytes of plaintext to include in the response per file. Default 20480 (20KB). Keep ≤ 20480 to fit Bedrock action-group response limit.
  Returns JSON: {project_id, files:[{path,is_binary,size,returned_bytes,next_offset,truncated,content,error}]}.
  - If a file's `truncated` is true and `next_offset` is non-null, call decrypt_and_stage again with the SAME file in files and start_byte=next_offset to retrieve more bytes.
  - Binary files (.png/.zip/.exe/etc.) return is_binary=true and content=null. Do not request binary files for content analysis.
  - You may include multiple files in one call to reduce round-trips, but the combined response stays within 25KB; for very large files, call once per file and follow next_offset.
  ```
  - 검증: 파일 인코딩 UTF-8 (BOM 없음), 줄바꿈 LF.

- [ ] **4D-2** `infra/bedrock.tf` 의 `aws_bedrockagent_agent.inspector` 의 `instruction` 필드 변경
  - 기존: `instruction = file("${path.module}/bedrock_system_prompt.txt")`.
  - 변경: 
    ```hcl
    instruction = join("\n", [
      file("${path.module}/bedrock_system_prompt.txt"),
      file("${path.module}/bedrock_tools_addendum.txt"),
    ])
    ```
  - 검증: `terraform validate` PASS.

- [ ] **4D-3** `infra/bedrock.tf` 의 기존 `aws_bedrockagent_agent_action_group.decrypt_and_stage` 리소스 시그니처 변경
  ```hcl
  resource "aws_bedrockagent_agent_action_group" "decrypt_and_stage" {
    agent_id          = aws_bedrockagent_agent.inspector.id
    agent_version     = "DRAFT"
    action_group_name = "decrypt_and_stage"
    action_group_executor {
      lambda = aws_lambda_function.mcp_bridge.arn
    }
    function_schema {
      member_functions {
        functions {
          name        = "decrypt_and_stage"
          description = "Decrypt specified files and return plaintext content. See system instruction for usage."
          parameters {
            map_block_key = "project_id"
            type          = "string"
            required      = true
          }
          parameters {
            map_block_key = "files"
            type          = "string"
            required      = true
            description   = "comma-separated relative paths"
          }
          parameters {
            map_block_key = "start_byte"
            type          = "integer"
            required      = false
          }
          parameters {
            map_block_key = "max_bytes"
            type          = "integer"
            required      = false
          }
        }
      }
    }
  }
  ```
  > **주의**: AWS provider 5.x 에서 `function_schema` 블록은 `member_functions { functions {...} }` 중첩 구조. parameter 표현은 `parameters { map_block_key=... type=... required=... description=... }` 의 **dynamic block 또는 반복 블록**. 정확한 syntax 는 `aws_bedrockagent_agent_action_group` 공식 문서로 4D-2 직전 확인. 만약 array 타입을 지원하는 새 버전이라면 `files` 를 array<string> 으로 바꾸고 Lambda CSV split 로직 제거 가능 — Task-4 시작 시 provider 버전 명시 확인할 것.

- [ ] **4D-4** 신규 리소스 `aws_bedrockagent_agent_action_group.list_project_files` 추가
  ```hcl
  resource "aws_bedrockagent_agent_action_group" "list_project_files" {
    agent_id          = aws_bedrockagent_agent.inspector.id
    agent_version     = "DRAFT"
    action_group_name = "list_project_files"
    action_group_executor {
      lambda = aws_lambda_function.mcp_bridge.arn
    }
    function_schema {
      member_functions {
        functions {
          name        = "list_project_files"
          description = "List all files (with size, is_binary, modified) of an encrypted project. Returns Markdown."
          parameters {
            map_block_key = "project_id"
            type          = "string"
            required      = true
          }
        }
      }
    }
  }
  ```
  - alias 는 `aws_bedrockagent_agent_alias.live` 가 두 action_group 변경 후 자동 prepare → 새 version 생성. terraform apply 가 다 처리.

- [ ] **4D-5** Lambda permission 확장 검증
  - `aws_lambda_permission.bedrock_invoke` 가 양쪽 action_group 의 ARN 을 source 로 허용하는지 확인. 만약 단일 source 면 `source_arn` 을 prefix 화 또는 두 permission 으로 분리.
  - 검증: terraform plan 출력에 `aws_lambda_permission` 변경 라인 명시되는지 확인.

- [ ] **4D-6** kb_staging 관련 리소스 제거 (§3 의 `infra/s3.tf`, `infra/ec2.tf` 수정)
  - `infra/s3.tf`:
    - `aws_s3_bucket.kb_staging` 리소스 + 관련 `aws_s3_bucket_*` 부속 리소스 모두 삭제.
    - `aws_s3_bucket_policy.kb_staging` 삭제.
  - `infra/ec2.tf`:
    - `aws_iam_role_policy.mcp` 의 inline JSON 에서 `agentbox-kb-staging` 관련 statement 삭제. 결과적으로 mcp-role 권한 = KMS Decrypt + GenerateDataKey + encrypted_code GetObject + SSM + CloudWatch agent 만 남음.
  - 검증: `terraform plan` 에 `aws_s3_bucket.kb_staging` 가 **destroy** 로 표시. plan 출력에서 kb-staging 관련 객체가 삭제되는지 확인. (사전에 kb-staging 안에 임시 객체 있을 수 있으므로 force_destroy=true 가 이미 설정되어 있는지 확인. 아니면 plan 단계에서 부착.)

- [ ] **4D-7** `tests/integration/test_terraform_plan_v2.py` 신규
  - Task-3 의 `tf_plan_json` fixture 재사용(이미 session-scope).
  - assertion:
    - **kb_staging 부재**: `assert not any("kb_staging" in c["address"] for c in plan["resource_changes"])`.
    - **action_group 2개**: `count = sum(1 for c in plan["resource_changes"] if c["address"].startswith("aws_bedrockagent_agent_action_group."))` ≥ 2.
    - **list_project_files action_group 존재**: address `aws_bedrockagent_agent_action_group.list_project_files` 찾기 성공.
    - **lambda env 그대로**: `MCP_SERVER_URL` 그대로.

**Phase 4D Gate**: `terraform validate` + `terraform plan -refresh=false -var-file=../tests/terraform/test.tfvars` PASS. `pytest tests/integration/test_terraform_plan_v2.py -m terraform -v` PASS.

---

### Phase 4E — 단위 테스트 작성

> 모두 moto + responses + pytest. AWS 실호출 없음. 비용 $0.

- [ ] **4E-1** `tests/unit/test_init_deps.py`
  - `test_check_dep_present`: `subprocess.run` mock(returncode=0) → `check_dep` True.
  - `test_check_dep_missing`: mock(FileNotFoundError) → False + error 메시지.
  - `test_try_auto_install_success`: install_hint mock 실행 후 재check 성공.
  - `test_try_auto_install_fail`: 설치 후에도 dep 미발견 → False.
  - `test_check_python_pkg_present` / `_missing`.

- [ ] **4E-2** `tests/unit/test_init_cmd.py`
  - fixture `fake_project(tmp_path)`: src dir 안에 텍스트 2개 + 이진 1개 생성.
  - `test_init_invalid_dir`: 존재하지 않는 dir → returncode=2.
  - `test_init_missing_sops_yaml`: `.sops.yaml` 없는 cwd → returncode=3.
  - `test_init_deps_missing_decline`: monkeypatch `check_dep` 실패 + input 'n' → returncode=4.
  - `test_init_deps_missing_accept`: input 'y' + `try_auto_install` 성공 mock → 통과.
  - `test_init_encrypt_failure`: `subprocess.run` for encrypt 가 returncode=1 → returncode=5.
  - `test_init_healthz_fail`: requests.get monkeypatch → ConnectionError → returncode=6 + 원인 안내 5개 포함.
  - `test_init_tcp_fail`: socket.create_connection mock → OSError → returncode=7.
  - `test_init_success`: 모두 성공 → returncode=0 + stdout 에 saas_url 포함.

- [ ] **4E-3** `tests/unit/test_mcp_list_files.py`
  - moto S3 + FastAPI TestClient.
  - `test_list_empty`: 빈 prefix → Markdown 본문에 `Total: 0 files` 포함.
  - `test_list_three_text_files`: `*.py, *.md, *.json` 업로드 → 표 3행 + is_binary 전부 false.
  - `test_list_with_binary_extensions`: `image.png.enc`, `archive.zip.enc` 업로드 → is_binary true.
  - `test_list_paginated`: 1500개 객체(moto 가 paginate 처리) → 1500 row.
  - `test_list_unknown_project`: project_id 다른 경로 → `Total: 0 files`.

- [ ] **4E-4** `tests/unit/test_mcp_decrypt_chunked.py`
  - sops 실제 실행 대신 `subprocess.run` 을 monkeypatch 로 mock 하여 임의 평문 반환.
  - `test_text_single_full`: 1KB 텍스트 → `truncated=false, next_offset=None, content` 길이 1024.
  - `test_text_chunked_first`: 30000 byte 텍스트 → `start_byte=0, max_bytes=20480` → `returned_bytes=20480, truncated=true, next_offset=20480`.
  - `test_text_chunked_second`: 위와 동일 파일 → `start_byte=20480, max_bytes=20480` → `returned_bytes=9520, truncated=false, next_offset=None`.
  - `test_binary_file`: 평문이 `\x00\x01...` 패턴 → `is_binary=true, content=null, size=N`.
  - `test_decrypt_failure`: sops mock returncode=1 → `error="decrypt_failed: ..."`.
  - `test_file_not_found`: S3 download 가 NoSuchKey → 해당 FileChunk 의 `error="not_found"`. 다른 파일들은 정상 처리.

- [ ] **4E-5** `tests/unit/test_lambda_mcp_bridge_v2.py`
  - responses 라이브러리로 MCP HTTP 가짜 응답 등록.
  - `test_route_list_project_files`: event `function="list_project_files"`, params `[{name:project_id,value:demo}]` → MCP `GET /mcp/list_files/demo` 1회 호출, response body 는 Markdown 그대로 passthrough.
  - `test_route_decrypt_and_stage`: event `function="decrypt_and_stage"`, params 4종 → MCP `POST /mcp/decrypt_and_stage` body 검증(files 가 list, start_byte/max_bytes 가 int) → response JSON passthrough.
  - `test_unknown_function`: event `function="bogus"` → response body 에 `error` 키 포함.
  - `test_authorization_header_present`: 양쪽 분기 모두 Bearer 토큰 헤더 포함.

- [ ] **4E-6** `tests/unit/test_grpc_no_cleanup.py`
  - InspectorServicer 인스턴스. `_invoke_bedrock_agent` mock(verdict ALLOW). `_record_event`, `_increment_token_count` mock.
  - `responses.add(DELETE, ...)` 미등록. InspectRequest 처리 후 `responses.calls` 길이 == 0.
  - 토큰 카운터 mock 호출 횟수 == 1.

**Phase 4E Gate**: `pytest tests/unit -v --cov=ec2 --cov=lambda --cov=src/agentbox --cov-report=term-missing` 신규 코드 라인 커버리지 ≥ 90%.

---

### Phase 4F — 통합 테스트 작성

> moto + 실제 sops 바이너리(없으면 skip) + 실제 FastAPI in-process. AWS 실호출 없음.

- [ ] **4F-1** `tests/integration/test_init_e2e.py`
  - moto S3+KMS+STS. KMS CMK 생성 후 ARN 으로 `.sops.yaml` 임시 생성.
  - 임시 cwd 에 `.env.endpoint` (`EC2_GRPC_HOST=127.0.0.1` 등) 와 `infra/` 빈 디렉토리 생성.
  - `agentbox.init_cmd.init(tmp_path, ...)` 호출.
  - `requests.get`, `socket.create_connection` monkeypatch 로 성공 응답 주입.
  - 종료 후 `_s3.list_objects_v2(Bucket="agentbox-encrypted-code", Prefix=f"encrypted_code/<basename>/")` Contents 길이 == 입력 파일 수.
  - stdout 캡처에 `대시보드: http://127.0.0.1:8000` 포함.

- [ ] **4F-2** `tests/integration/test_mcp_full_flow_v2.py`
  - `shutil.which("sops")` 없으면 `pytest.skip`.
  - moto S3+KMS. SOPS 가 mock 환경에 KMS 호출하므로, `AWS_ENDPOINT_URL` 등 환경 변수 세팅(moto 5 의 standalone mode).
  - encrypted_code 에 평문 3개(텍스트 2개 + 이진 1개) 를 sops 로 진짜 암호화 후 업로드.
  - FastAPI TestClient → `GET /mcp/list_files/<pid>` → Markdown 파싱 → 3 rows 확인.
  - `POST /mcp/decrypt_and_stage {files=["a.txt","b.md","img.bin"], start_byte=0, max_bytes=4096}` → 응답 JSON 검증:
    - a.txt FileChunk.content 정확. is_binary false.
    - b.md 동일.
    - img.bin is_binary true, content null.
  - 큰 텍스트(50KB)도 1개 추가 → `start_byte=0,max_bytes=20480` 1차 호출, `start_byte=next_offset` 2차 호출 후 content 합치면 원본과 동일.

- [ ] **4F-3** `tests/integration/test_grpc_full_flow_v2.py`
  - Task-3 의 `test_grpc_full_flow.py` 와 동일하나 cleanup HTTP mock 없음 + 토큰 카운터 검증만 유지.

**Phase 4F Gate**: `pytest tests/integration -m "not aws and not terraform" -v` 100% PASS.

---

### Phase 4F-pre — Script DRY_RUN 회귀 (Task-3 Phase 3F-post 유지)

- [ ] **4Fpre-1** `bash -n scripts/deploy.sh scripts/destroy.sh scripts/encrypt_and_upload.sh` 모두 0 exit.
- [ ] **4Fpre-2** `DRY_RUN=1 ./scripts/deploy.sh` 가 0 exit (Task-3 의 DRY_RUN 분기 그대로 동작).
- [ ] **4Fpre-3** `pytest tests/scripts -v` PASS (Task-3 의 `test_dry_run_*.py`).

**Phase 4F-pre Gate**: 회귀 없음.

---

### Phase 4G — 배포 + 실 AWS 검증 (사용자 직접 실행 단계)

> Claude 는 §4F 까지 완료 후 멈춘다. 이하 단계는 사용자가 본인 손으로 실행하며 결과를 보고한다.
> 비용: terraform apply 가 kb_staging 삭제 + action_group 1개 추가 + agent prepare 1회. 추가 월 비용 $0 (오히려 S3 비용 -소액).

- [ ] **4G-1** `git status` 깨끗(이전 작업 잔여물 없음). 필요 시 `git stash`.
- [ ] **4G-2** `./scripts/deploy.sh -auto-approve` 실행.
  - terraform apply 가 kb_staging 버킷 삭제 시 `force_destroy=true` 필요. 미설정이면 plan 실패. 사전 확인.
  - alias prepare 자동 진행 후 종료. 정상 종료 확인.
- [ ] **4G-3** **AgentBox init 직접 검증**:
  - 새 폴더 만들고 (`mkdir /tmp/demo_proj && echo "hello" > /tmp/demo_proj/a.txt && echo '{"k":1}' > /tmp/demo_proj/b.json`).
  - `python -m agentbox init /tmp/demo_proj -y` 실행.
  - 출력에 `[agentbox] PROJECT_ID=demo_proj`, `[agentbox] init OK. 대시보드: http://<app_public_ip>:8000` 포함 확인.
  - AWS S3 콘솔에서 `agentbox-encrypted-code/encrypted_code/demo_proj/a.txt.enc`, `b.json.enc` 두 객체 존재 확인.
- [ ] **4G-4** **list_project_files 라운드트립**:
  - SaaS 대시보드 또는 직접 `aws bedrock-agent-runtime invoke-agent` 로 prompt "List all files in project demo_proj" 보냄.
  - Agent 가 `list_project_files(project_id=demo_proj)` 호출 → Markdown 테이블 응답 → LLM 이 사용자에게 a.txt/b.json 안내.
  - CloudWatch Logs 에서 Lambda mcp_bridge 로그에 `function=list_project_files` 라인 확인.
- [ ] **4G-5** **decrypt_and_stage 라운드트립 (소형)**:
  - prompt "Show me the contents of a.txt and b.json in project demo_proj".
  - Agent 가 `decrypt_and_stage(project_id=demo_proj, files="a.txt,b.json", start_byte=0, max_bytes=20480)` 호출 → 응답 JSON 에 content 포함 → LLM 이 "hello", `{"k":1}` 인용.
- [ ] **4G-6** **decrypt_and_stage 라운드트립 (chunked)**:
  - 30KB 텍스트 파일 `c.txt` 추가 후 재 init.
  - prompt "Read the full contents of c.txt in project demo_proj".
  - Agent 가 첫 호출 `start_byte=0,max_bytes=20480` → `truncated=true,next_offset=20480` 받음 → 자동으로 두 번째 호출 `start_byte=20480` 보냄 → 완전한 내용 재구성.
  - 두 번째 호출이 발생하지 않으면 system prompt(`bedrock_tools_addendum.txt`) 수정 후 `terraform apply -target=aws_bedrockagent_agent.inspector` 로 재 prepare.
- [ ] **4G-7** **이진 파일 거동**:
  - `dd if=/dev/urandom of=/tmp/demo_proj/blob.bin bs=1024 count=10`. 재 init.
  - prompt "What is blob.bin?". Agent 가 list 호출 후 `is_binary=true` 보고 decrypt 요청 안 함을 확인(또는 요청해도 content=null 받음).
- [ ] **4G-8** **kb_staging 부재 확인**:
  - `aws s3 ls | grep kb-staging` → 0 hit. (terraform destroy 완료된 상태.)
  - `aws iam get-role-policy --role-name <mcp-role>` 출력에 kb-staging 문자열 없음.
- [ ] **4G-9** **트래픽 검사 회귀**:
  - Task-3 `scripts/test_lifecycle_45.sh` 실행 → ALL PASSED (gRPC + Bedrock + DynamoDB 기록 + 토큰 카운터). cleanup 호출 제거가 다른 라이프사이클에 영향 없음 확인.

**Phase 4G Gate**:
- 4G-3 ~ 4G-7 모두 의도대로 동작.
- 4G-8 kb_staging 없음.
- 4G-9 회귀 없음.

---

## 5. 비기능 요구사항

| 영역 | 목표 | 변경 |
|---|---|---|
| 지연 | 평문 본문 포함으로 Bedrock 응답 1KB → ~20KB 로 증가. Bedrock TTFT 영향 미미(payload < 25KB). chunked 호출은 LLM 1턴 추가 = +1~2s. p95 ≤ 7s 목표. | 신규 |
| 보안 | 평문이 디스크 영구화되지 않음. kb_staging 제거로 IAM 권한면 ↓. | 강화 |
| 가용성 | Task-3 동일. 단일 EC2 PoC. | 변경 없음 |
| 비용 | kb_staging S3 PUT/Storage 비용 제거 (~$0/월 미미). | 미세 ↓ |
| 사용성 | `agentbox init <dir>` 1줄 진입. 의존성 자동설치 프롬프트 제공. | 신규 |

---

## 6. 리스크 및 결정 보류

| ID | 항목 | 결정 |
|---|---|---|
| R1 | Bedrock function_schema parameter type 가 string-only 제약 → files 가 CSV string | 합의. Lambda 가 split. LLM 은 system prompt 안내로 CSV 생성. |
| R2 | LLM 이 next_offset 무시하고 첫 chunk 만 보고 답할 가능성 | system prompt 에 명시 + 4G-6 에서 실증. 실패 시 prompt 보강 후 `apply -target=agent`. |
| R3 | Bedrock action_group response 25.6KB 한도 위반 시 LLM 잘림 | `max_bytes=20480` 기본 + 응답 byte 길이 logger.warning. 사용자가 max_bytes 더 키우려면 → 단일 파일 호출 권장. |
| R4 | kb_staging force_destroy 미설정 시 destroy 실패 | Phase 4D-6 사전 확인. 객체 잔존 시 `aws s3 rm s3://...kb-staging --recursive` 후 재시도. |
| R5 | Windows 환경에서 encrypt_and_upload.sh 직접 실행 불가 | init_cmd.py 가 WSL 검출 후 `wsl bash ...` prefix. WSL 미설치 시 명확한 안내. |
| R6 | Bedrock Agent alias prepare 가 1~2분 → terraform apply 종료 후 검증 호출이 너무 빠르면 NotPrepared | 4G-3 전 30초 대기 또는 `aws bedrock-agent get-agent --agent-id ... --query agentStatus` 로 PREPARED 폴링. |
| R7 | sops binary GitHub release 다운로드 실패(네트워크/CI 차단) | init_deps 의 try_auto_install 실패 시 install_hint 출력. |
| R8 | files 리스트 안에 `..` / 절대경로 / 심볼릭링크 포함되면 디렉토리 탈출 위험 | MCP `decrypt_and_stage` 가 rel_path 검증: 정규화 후 `..` 포함되면 422. `Path("encrypted_code")` 기준 `is_relative_to`. |

---

## 7. 테스트 전략

| 레벨 | 도구 | 대상 | 위치 |
|---|---|---|---|
| Terraform plan JSON | pytest + terraform show -json | infra/ 변경: kb_staging 부재 + action_group 2개 | `tests/integration/test_terraform_plan_v2.py` |
| Unit | pytest, moto, responses, monkeypatch | init_cmd, init_deps, mcp_server(list_files/decrypt), lambda mcp_bridge v2, grpc no-cleanup | `tests/unit/test_*.py` (신규 6개) |
| Integration (mock) | pytest, moto, FastAPI TestClient, 실 sops binary | init E2E, MCP full flow with chunking, grpc flow v2 | `tests/integration/test_*_v2.py` |
| Script | bash -n, DRY_RUN=1 | deploy.sh / destroy.sh / encrypt_and_upload.sh | `tests/scripts/` (Task-3 유지) |
| Real AWS | pytest -m aws | 사용자 손에서 4G 시나리오 | (자동화 안 함, §4G 매뉴얼) |

CI 명령(권장 순서):
```bash
# 0. 정적
terraform -chdir=infra validate
bash -n scripts/deploy.sh scripts/destroy.sh scripts/encrypt_and_upload.sh

# 1. Terraform plan (4D-7)
pytest tests/integration/test_terraform_plan_v2.py -m terraform -v

# 2. Unit (4E)
pytest tests/unit -m "not aws and not terraform" -v --cov=ec2 --cov=lambda --cov=src/agentbox

# 3. Integration mock (4F)
pytest tests/integration -m "not aws and not terraform" -v

# 4. DRY_RUN 스크립트 회귀
pytest tests/scripts -v
```

---

## 8. TODO 마스터 체크리스트 (재실행용)

> Plan 이 중간에 중단되어도 가장 최근 미체크(`- [ ]`) 항목부터 재시작 가능.

### Phase 4A — `agentbox init` CLI
- [x] 4A-1 `src/agentbox/init_deps.py` 작성 (DEPS, check_dep, try_auto_install, check_python_pkg)
- [x] 4A-2 `src/agentbox/init_cmd.py` 작성 (`init(...)` 6단계 함수)
- [x] 4A-3 `get_terraform_output` 헬퍼 추가
- [x] 4A-4 `src/agentbox/__main__.py` 에 `init` subparser 추가
- [x] 4A-5 `scripts/encrypt_and_upload.sh` PROJECT_ID 출력 + 50MB 경고

### Phase 4B — MCP Server tool 2종
- [x] 4B-1 `_KB_STAGING_BUCKET` 및 cleanup 엔드포인트 전부 삭제
- [x] 4B-2 `_is_binary_bytes` 헬퍼 추가
- [x] 4B-3 `GET /mcp/list_files/{project_id}` Markdown 응답 신설
- [x] 4B-4 `POST /mcp/decrypt_and_stage` 시그니처 전면 변경 (files / start_byte / max_bytes / chunked 응답)
- [x] 4B-5 `MCP_PORT=8080` 및 `/healthz` 유지 확인

### Phase 4C — Lambda + grpc cleanup 제거
- [x] 4C-1 `lambda/mcp_bridge.py` function 분기 (list_project_files / decrypt_and_stage)
- [x] 4C-2 `ec2/grpc_server/server.py` 의 `requests.delete(... /mcp/cleanup ...)` 삭제

### Phase 4D — Bedrock + kb_staging 인프라
- [ ] 4D-1 `infra/bedrock_tools_addendum.txt` 신규 (UTF-8, LF)
- [ ] 4D-2 `aws_bedrockagent_agent.instruction` 을 두 파일 join 으로 변경
- [ ] 4D-3 `decrypt_and_stage` action_group 시그니처 변경 (project_id, files, start_byte, max_bytes)
- [ ] 4D-4 `list_project_files` action_group 신규 (project_id)
- [ ] 4D-5 `aws_lambda_permission` 가 양쪽 action_group 허용하는지 검증/수정
- [ ] 4D-6 kb_staging 관련 모든 인프라 리소스 + IAM statement 삭제 (force_destroy=true 사전 부착)
- [ ] 4D-7 `tests/integration/test_terraform_plan_v2.py` 4개 assert

### Phase 4E — 단위 테스트
- [ ] 4E-1 test_init_deps.py (5 케이스)
- [ ] 4E-2 test_init_cmd.py (9 케이스)
- [ ] 4E-3 test_mcp_list_files.py (5 케이스)
- [ ] 4E-4 test_mcp_decrypt_chunked.py (6 케이스)
- [ ] 4E-5 test_lambda_mcp_bridge_v2.py (4 케이스)
- [ ] 4E-6 test_grpc_no_cleanup.py (cleanup 미호출 + 토큰카운터 1회)

### Phase 4F — 통합 테스트
- [ ] 4F-1 test_init_e2e.py (moto + monkeypatch)
- [ ] 4F-2 test_mcp_full_flow_v2.py (실 sops 바이너리, 없으면 skip)
- [ ] 4F-3 test_grpc_full_flow_v2.py (cleanup 없음 회귀)

### Phase 4F-pre — Script 회귀
- [ ] 4Fpre-1 `bash -n` 3개 스크립트 통과
- [ ] 4Fpre-2 `DRY_RUN=1 ./scripts/deploy.sh` PASS
- [ ] 4Fpre-3 `pytest tests/scripts` PASS

### Phase 4G — 실 AWS 라운드트립 (사용자 손에서)
- [ ] 4G-1 git status 깨끗
- [ ] 4G-2 deploy.sh 정상 종료 (kb_staging 삭제 + alias prepare)
- [ ] 4G-3 `python -m agentbox init /tmp/demo_proj -y` 성공 + S3 에 .enc 객체 생성
- [ ] 4G-4 list_project_files 라운드트립 (LLM 이 a.txt/b.json 안내)
- [ ] 4G-5 decrypt_and_stage 라운드트립 소형
- [ ] 4G-6 decrypt_and_stage chunked (30KB 텍스트, next_offset 사용)
- [ ] 4G-7 이진 파일 거동 (is_binary=true)
- [ ] 4G-8 `aws s3 ls | grep kb-staging` 0 hit + IAM 에 kb-staging 미참조
- [ ] 4G-9 `test_lifecycle_45.sh` ALL PASSED (회귀 없음)

---

## 9. 재개 프로토콜

1. §8 의 가장 최근 미체크(`- [ ]`) 항목으로 이동.
2. **Phase 4A~4F 의 모든 변경은 git commit 으로 분리** 권장:
   - `feat(task-4,4A-1): add init_deps module`
   - `feat(task-4,4B-3): mcp list_files endpoint`
   - 등.
3. Phase 4E/4F 는 idempotent — `pytest` 만 다시 돌리면 된다.
4. Phase 4D 까지 코드만 변경 + Phase 4G 직전에만 `terraform apply` 수행.
5. Phase 4G 가 중간에 실패 시:
   - 4G-2 실패(kb_staging 객체 잔존) → `aws s3 rm s3://*-kb-staging --recursive` 후 재시도.
   - 4G-4/5 실패(LLM 이 tool 호출 안 함) → Bedrock Agent CloudWatch Logs 에서 LLM trace 확인 → `bedrock_tools_addendum.txt` 수정 → `terraform apply -target=aws_bedrockagent_agent.inspector` → 30초 대기 → 재시도.
   - 4G-6 실패(chunked 두 번째 호출 안 함) → tools addendum 의 "If a file's truncated is true..." 문장 강화.
6. 코드 수정 후엔 항상 단위 테스트 먼저 → 통합 → 실 AWS.

---

## 10. 코드 수정 금지 — 시작 조건

- 본 문서 사용자 검토 + **"Task-4 시작"** 명시적 지시 전까지 어떤 파일도 수정 금지.
- 사용자가 검토 중 수정 요청한 항목은 본 문서를 직접 갱신 후 다시 검토 받음.
- 첫 실행 단계는 §8 의 **4A-1**.

---

## 부록 A — 합의된 결정 요약 (§0.1 와 동일하지만 빠른 참조용)

| 결정 | 값 |
|---|---|
| PROJECT_ID | dir basename |
| 대시보드 URL | SaaS `http://<app_public_ip>:8000` |
| MCP Tool #2 파일 선택 | files: list[str] |
| Dependency 처리 | 확인 + 자동설치(프롬프트) |
| Connectivity | SaaS /healthz + gRPC TCP 도달 |
| Bedrock 응답 전달 | tool 응답 본문 + chunking |
| MCP Tool #1 포맷 | Markdown flat list |
| Agent prompt 변경 | 증분 addendum |
| Agent 갱신 | terraform apply |
| Chunking 인터페이스 | files+start_byte+max_bytes 단일 tool, next_offset 응답 |
| kb_staging | 완전 제거 |
| 이진 파일 | 메타데이터만, content=null |
| 테스트 도구 | 기존 pytest+moto+responses |

---

## 부록 B — 용어 정의

- **`agentbox init <dir>`**: 본 Task-4 에서 신설하는 endpoint CLI 명령. 단일 폴더를 검사 대상 프로젝트로 등록.
- **PROJECT_ID**: S3 `encrypted_code/<PROJECT_ID>/` prefix 식별자. 본 Task 에서는 dir basename.
- **action_group**: Bedrock Agent 가 Lambda 를 호출하기 위한 함수 집합. function_schema 로 LLM 에게 시그니처 노출.
- **function_schema**: Bedrock action_group 의 OpenAPI-like 스키마. parameter type 은 string/integer/number/boolean 만 지원(array 직접 미지원).
- **start_byte / max_bytes / next_offset / truncated**: 본 Task 의 chunked decrypt 인터페이스 4종 필드. 의미는 §4.4 (Phase 4B-4) 참조.
- **is_binary**: list 시점에는 확장자 휴리스틱, decrypt 시점에는 NUL/ASCII 비율 휴리스틱.
- **kb_staging**: Task-2/3 의 평문 임시 보관용 S3 버킷. Task-4 에서 완전 제거.
- **`responses` 라이브러리**: `requests` 호출을 mock 하는 라이브러리.
- **moto**: AWS SDK 호출을 in-memory 로 mock 하는 라이브러리.
- **alias prepare**: Bedrock Agent 가 action_group/instruction 변경을 반영해 새 version 빌드 후 alias 가 그 version 을 가리키도록 하는 1~2분 짜리 비동기 작업. `terraform apply` 가 자동 트리거.

---

## 부록 C — 코드 분석 근거 (작성 시 직접 확인한 함수 내부)

> 사용자 작성 주의사항: "함수 이름만 보지 말고 함수 내부 직접 확인".
> 아래는 본 plan 작성 시 직접 읽은 파일과 함수 본문 요지.

| 파일 | 라인 | 확인 사항 |
|---|---|---|
| `src/agentbox/__main__.py` | 102–119 | `main()` 의 `argparse` 가 `run/ca/setup` 만 존재 → `init` 신설 필요 확인. |
| `ec2/mcp_server/server.py` | 43–101 | `decrypt_and_stage` 가 project_id prefix 전체를 loop 돌며 `subprocess.run(["sops","--decrypt",...,enc_path])` 후 `_s3.put_object(Bucket=_KB_STAGING_BUCKET,...)` 함. 즉 파일 선택 불가 + 평문 S3 보관 확인. |
| `ec2/mcp_server/server.py` | 104–118 | `/mcp/cleanup/{session_id}` 핸들러가 kb_staging prefix 의 모든 객체 delete. Task-4 에서 제거 대상. |
| `lambda/mcp_bridge.py` | 9–37 | event["parameters"] 에서 project_id 만 추출 → MCP POST `/mcp/decrypt_and_stage` 한 가지 path. function 분기 없음. Task-4 에서 분기 추가. |
| `scripts/encrypt_and_upload.sh` | 27–36 | `find` 로 모든 파일을 `sops --encrypt <f> > <f>.enc` 한 후 `aws s3 sync` 로 `s3://$S3_BUCKET/encrypted_code/$PROJECT_ID/` 에 업로드. → 사용자 요구(파일명 유지 + `.enc` 부착) 와 일치. 재사용. |
| `Task-3.md` | 3A-5, 4D | Lambda 가 private subnet 에 in-VPC, `MCP_SERVER_URL=http://<mcp_private_ip>:8080`. Task-4 변경 없음. |

