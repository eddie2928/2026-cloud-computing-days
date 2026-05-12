# Task-7: `.agentbox` 통합 + CLI 표면 단순화 + 정합성 검사 + 테스트 자동화

> 본 문서는 코드 수정 전 사용자 승인용 플랜이다. 사용자가 "go"를 명시하기 전에는
> 본 플랜 내 코드 변경 항목을 실행하지 않는다. UTF-8 인코딩.

## 0. 한 줄 요약

산개된 설정(`.env`, `.env.endpoint`, `.sops.yaml`, `certs/grpc/`)을
**`~/.agentbox/`(global config)** 와 **`<repo>/.agentbox/`(local state)** 로 이원화하고,
`scripts/`의 18개 파일 중 `deploy.sh`/`destroy.sh`/`redeploy_idempotency.sh` 3개만 남기고
나머지는 `agentbox set/init/on/off/run/destroy/reset/status/doctor` CLI에 흡수한다.
`set`은 7a(LISTEN) → 7b(gRPC TCP) → **7c(mTLS handshake)** 까지 자동 검증하며,
수동 테스트 직전 단일 read-only 점검을 위한 신규 **`agentbox doctor`**(D1~D9)를
추가한다. hardcoded IP/Cert/Token 정합성은 **Terraform output을 SoT**로 하는 별도
`scripts/verify_consistency.py`로 검사·수정한다. `agentbox --help` 흐름은 새 표면을
반영하여 전면 갱신한다. 모든 변경은 `pytest` 기반 단위/통합 테스트로 자동 검증한다.

---

## 1. 배경 / 현 상태 (코드 직접 확인)

다음은 본 플랜 작성 시점에 실제 파일 내용을 직접 열어 확인한 사실이며,
함수 이름만 보고 가정한 부분은 없다.

### 1.1 위치가 분산된 설정·상태

| 파일 / 폴더 | 현재 위치 | 의미 |
|---|---|---|
| `.env` | `<repo>/` | `GRPC_HOST=3.86.3.245`, `GRPC_PORT=50051`, `GRPC_CA_CERT=/mnt/c/.../certs/grpc/agentbox-ca.crt`, `GRPC_CLIENT_CERT`, `GRPC_CLIENT_KEY` |
| `.env.endpoint` | `<repo>/` | `EC2_GRPC_HOST=3.86.3.245`, `EC2_GRPC_PORT=50051` (deploy.sh가 생성) |
| `.env.example` | `<repo>/` | `PROXY_PORT=8080`, `API_PORT=8000`, `DB_PATH`, `CA_DIR`, `HITL_TIMEOUT`, `DEBUG` |
| `.sops.yaml` | `<repo>/` | KMS ARN. `init_cmd.py`가 `_PROJ_ROOT / ".sops.yaml"`로 직접 참조 |
| `certs/grpc/` | `<repo>/` | mTLS 인증서. `.env`에서 절대경로로 참조 |
| `.agentbox.pid` | `<repo>/` | `_run`/`_reset`/`set_cmd._start_proxy_background`가 쓰는 PID |
| `logs/` | `<repo>/` | `agentbox-run.log`, `agentbox-set-*.log`, `agentbox-init-*.log` |
| `~/.agentbox/last_init.json` | `$HOME/.agentbox/` | `last_init.py`가 user-home에 기록 (프로젝트별이 아닌 user-wide) |

문제: state(`pid`, `logs`, `last_init`)는 프로젝트별이어야 하는데 일부가 user-home에 있고,
config(env, certs)는 사용자별이어야 하는데 프로젝트 안에 있어 의미와 위치가 뒤바뀌어 있다.

### 1.2 `scripts/` 파일 18개 (실제 확인)

```
activate.sh             check_ec2.sh         deactivate.sh
deploy.sh               deploy_static.sh     destroy.sh
encrypt_and_upload.sh   gen_mtls_certs.sh    gen_proto.sh
install_ca.sh           install_ebpf.sh      iptables_redirect.sh
redeploy_idempotency.sh run.sh               setup_vm.sh
test_lifecycle_45.sh    test_transparent.sh  update_my_ip.sh
```

이 중 `init_cmd.py`가 직접 호출하는 것은 `encrypt_and_upload.sh` 하나.
`activate.sh`/`deactivate.sh`는 `set_cmd._install_shell_integration`이 만든
`~/.bashrc` 함수에서 `source`로 호출. 나머지는 사용자가 수동 또는 `deploy.sh`가 호출.

### 1.3 `agentbox` CLI 서브커맨드 (현재)

`set`, `init`, `run`, `reset`, `destroy`, `ca`, `setup`, `status`

### 1.4 테스트 인프라 (현재)

- `pytest` (`pyproject.toml` 설정), `asyncio_mode = "auto"`
- `tests/unit/` 25개, `tests/integration/` 18개, `tests/scripts/` 3개
- 표식: `terraform`(터미널 필요), `aws`(실 AWS 자격 필요)
- 본 Task는 위 인프라를 **확장**한다 (대체 X).

---

## 2. 목표 / 비목표

### 2.1 목표 (G)

- **G1**: `~/.agentbox/`(global config) ↔ `<repo>/.agentbox/`(local state) 하이브리드 레이아웃 도입
- **G2**: 산개된 `.env`/`.env.endpoint`/`.sops.yaml`/`certs/grpc/`를 `~/.agentbox/`로 1회 마이그레이션
- **G3**: `agentbox set`이 deps + env + CA/mTLS + proto + shell + background run + health-check + gRPC TCP + **mTLS handshake** 까지 **단일 명령**으로 처리 (7a/7b/7c)
- **G4**: `agentbox on`/`off`를 Python으로 옮기고 `activate.sh`/`deactivate.sh` 제거
- **G5**: `scripts/` 18개 중 `deploy.sh`, `destroy.sh`, `redeploy_idempotency.sh`만 남기고 나머지 제거 또는 Python 내장
- **G6**: Terraform output을 SoT로 하는 정합성 검사·수정 스크립트 `scripts/verify_consistency.py` 신규
- **G7**: **`agentbox doctor`** 신규 — 수동 테스트 직전 단일 read-only 점검 (D1~D9)
- **G8**: **`agentbox --help`** 전면 갱신 — 새 흐름(set→doctor→on/off, ca/setup 제거) 반영
- **G9**: 위 모든 변경에 대해 pytest 단위/통합 테스트 작성 후 일괄 통과
- **G10**: 수동 E2E 체크리스트(다른 Claude Code 인스턴스 → EC2 도달) 문서화

### 2.2 비목표 (NG)

- **NG1**: transparent 모드(iptables/eBPF) 재활성화 (현재 `TRANSPARENT_MODE=false` 고정, 관련 코드 제거)
- **NG2**: 실제 Claude Code 자식 프로세스를 통한 E2E 자동화 (수동 체크리스트로 대체)
- **NG3**: 인프라(Terraform) 변경. `deploy.sh`/`destroy.sh`는 코드 손대지 않음
- **NG4**: `~/.bashrc` 외 shell(zsh/fish) 통합 (현 코드와 동일하게 bash 한정)
- **NG5**: Windows native PowerShell 지원 (현 코드와 동일하게 WSL 안에서 실행 가정)

---

## 3. 설계 상세

### 3.1 디렉토리 레이아웃 (확정)

```
~/.agentbox/                       # global config (deploy 시점 산물)
├── env                            #   GRPC_HOST/PORT/CA_CERT/CLIENT_CERT/CLIENT_KEY 통합
├── endpoint                       #   EC2_GRPC_HOST/PORT (Terraform output 산물)
├── sops.yaml                      #   KMS ARN
└── certs/grpc/
    ├── agentbox-ca.crt
    ├── agentbox-ca.key
    ├── endpoint.crt
    └── endpoint.key

<repo>/.agentbox/                  # local state (실행 중 산물)
├── pid                            #   현 .agentbox.pid 이동
├── logs/
│   ├── agentbox-run.log
│   ├── agentbox-set-<ts>.log
│   └── agentbox-init-<ts>.log
└── last_init.json                 #   현 ~/.agentbox/last_init.json → 프로젝트별로 분리
```

**경로 결정 우선순위 (확정)**:

1. 환경변수 `AGENTBOX_HOME` (테스트용 override) → 둘 다 이 경로 아래에 둠
2. 기본: global = `Path.home() / ".agentbox"`, local = `<project_root> / ".agentbox"`

`<project_root>`는 `_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent` (기존 규칙 유지).

### 3.2 `config.py` 변경

- `BaseSettings.model_config.env_file`를 다중 경로 튜플로:
  `("~/.agentbox/env", "~/.agentbox/endpoint")` (둘 다 expanduser).
- 두 파일이 다 없으면 기본값 사용 (현 `Settings` 기본값 유지).
- `_resolve_paths()`가 처리하던 상대→절대 변환은 그대로 두되,
  `CA_DIR`/`DB_PATH` 기본값은 변경하지 않는다 (state는 `<repo>/.agentbox/`로 이동하지만
  config 호환을 위해 환경변수 override가 가능해야 함).

### 3.3 마이그레이션 로직 (`agentbox.dotagentbox` 신규 모듈)

`ensure_layout(project_root: Path) -> LayoutPaths`:

1. `~/.agentbox/` 없으면 생성.
2. `<project_root>/.agentbox/{logs}` 없으면 생성.
3. **1회 마이그레이션** (idempotent, source 파일 존재 시에만 동작):
   - `<proj>/.env` → `~/.agentbox/env` (덮어쓰지 않음, 다르면 `.env.backup-<ts>`로 백업)
   - `<proj>/.env.endpoint` → `~/.agentbox/endpoint`
   - `<proj>/.sops.yaml` → `~/.agentbox/sops.yaml`
   - `<proj>/certs/grpc/*` → `~/.agentbox/certs/grpc/`
   - `<proj>/.agentbox.pid` → `<proj>/.agentbox/pid`
   - `<proj>/logs/*` → `<proj>/.agentbox/logs/`
   - `~/.agentbox/last_init.json` → `<proj>/.agentbox/last_init.json` (있을 때만)
4. 마이그레이션 후 원본 파일은 `.migrated` 빈 마커 남기고 **삭제** (재실행 시 다시 옮기지 않도록).
5. `LayoutPaths` 데이터클래스 반환: `global_env, global_endpoint, global_sops, global_certs_dir, local_pid, local_logs_dir, local_last_init`.

### 3.4 `agentbox set` 새 동작 (7단계)

| # | 단계 | 실패 처리 |
|---|---|---|
| 1 | `ensure_layout()` (3.3) | 권한 오류만 fail-fast |
| 2 | deps 점검·자동 설치 (현 `_check_deps_step` 유지) | 누락 + `-y` 없으면 exit 4 |
| 3 | env vars 점검 (현 `_check_env_step` 유지) | warning만 |
| 4 | CA + mTLS 인증서 보장 (`ensure_ca` + 내장 mTLS 생성기) | exit 5 |
| 5 | proto stub 점검 (`agentbox.grpc.inspect_pb2` import 가능?), 없으면 `python -m grpc_tools.protoc` 호출 | exit 6 |
| 6 | shell 통합 (현 `_install_shell_integration` 유지, 내용만 `command agentbox _on/_off` 호출로 단순화) | warning |
| 7a | background `agentbox run` 시작 + **health-check** (최대 10초 polling: `127.0.0.1:8080`+`:8000` LISTEN) | 실패 시 `<repo>/.agentbox/logs/agentbox-run.log` 끝 50줄 stdout, exit 7 |
| 7b | **gRPC TCP connect** (`GRPC_HOST:GRPC_PORT` 5초) | exit 7 + 보안 그룹/서비스 가이드 |
| 7c | **mTLS handshake 검증**: `grpc.secure_channel(host:port, ssl_credentials(ca, client_cert, client_key))`로 채널 생성 후 `grpc.channel_ready_future(channel).result(timeout=5)` 호출. 채널 ready 도달 시 OK. | exit 7 + "CA/client cert 불일치 또는 EC2 mTLS 설정 점검" 가이드 |

각 단계 시작·종료 로그를 `<repo>/.agentbox/logs/agentbox-set-<ts>.log`에 기록.
7c는 실제 RPC 호출이 아니라 채널 ready 도달만 확인 — 가벼우면서 cert 신뢰 체인까지 검증.

### 3.5 `agentbox on`/`off` (`agentbox._activate` 신규 모듈)

shell이 부모 환경변수를 못 바꾸므로 **eval 패턴** 사용. `~/.bashrc` 함수는:

```bash
agentbox() {
    case "$1" in
        on)  eval "$(command agentbox _on)"  ;;
        off) eval "$(command agentbox _off)" ;;
        *)   command agentbox "$@" ;;
    esac
}
```

- `agentbox _on`은 stdout에 다음을 출력:
  ```
  export HTTPS_PROXY=http://127.0.0.1:8080
  export NO_PROXY=169.254.169.254,amazonaws.com,...
  export NODE_EXTRA_CA_CERTS=/home/.../.agentbox/certs/grpc/agentbox-ca.crt
  ```
  추가로 `:8080`이 LISTEN 아니면 백그라운드 `agentbox run` 시작 (set과 동일 로직 재사용).
- `agentbox _off`는 `unset HTTPS_PROXY ...` 출력 + `pid` 파일로 백그라운드 종료.
- 두 서브커맨드는 `--quiet`이 아니면 user-facing 메시지를 **stderr**로 (stdout은 eval 대상이므로 깨끗하게 유지).

### 3.6 `scripts/` 정리 (확정)

**남길 (3개)**:
- `deploy.sh` (인프라 apply)
- `destroy.sh` (인프라 destroy)
- `redeploy_idempotency.sh` (검증 도구, 기존 테스트가 의존)

**Python으로 옮기고 삭제 (8개)**:
| 삭제 | 대체 |
|---|---|
| `activate.sh` | `agentbox._activate.on_command()` |
| `deactivate.sh` | `agentbox._activate.off_command()` |
| `install_ca.sh` | `agentbox.ca_install.install_to_trust_store()` (sudo 필요 시 hint 출력) |
| `gen_mtls_certs.sh` | `agentbox.proxy.ca.gen_mtls_certs()` 확장 |
| `gen_proto.sh` | `agentbox.set_cmd._ensure_proto_stub()` |
| `encrypt_and_upload.sh` | `agentbox.encrypt.encrypt_and_upload()` (boto3 + `sops` CLI) |
| `run.sh` | 이미 `agentbox run`이 존재 |
| `deploy_static.sh` | dashboard 정적 산출물 → 빌드 산출물은 `deploy.sh`가 처리하므로 단순 삭제 |

**완전 삭제 (7개)**: `check_ec2.sh`, `update_my_ip.sh`, `test_lifecycle_45.sh`, `test_transparent.sh`, `iptables_redirect.sh`, `install_ebpf.sh`, `setup_vm.sh`.

### 3.7 정합성 검사 스크립트 `scripts/verify_consistency.py`

**SoT**: `terraform -chdir=infra output -json`의 다음 키:
- `app_public_ip` → `~/.agentbox/endpoint:EC2_GRPC_HOST`, `~/.agentbox/env:GRPC_HOST`
- `kms_key_arn` → `~/.agentbox/sops.yaml:creation_rules[0].kms`
- (있다면) `code_bucket` → 환경변수 `PROJECT_S3_BUCKET` 힌트 또는 `~/.agentbox/env:PROJECT_S3_BUCKET`

**검사 항목**:
- IP 일치 (위 두 키)
- KMS ARN 일치 (sops.yaml)
- `~/.agentbox/certs/grpc/agentbox-ca.crt` 존재 + `openssl x509 -checkend $((7*24*3600))` 통과
- `~/.agentbox/certs/grpc/endpoint.crt` 동일 검사

**CLI**:
- `python scripts/verify_consistency.py --check` → diff JSON, exit 0 일치 / exit 1 불일치
- `python scripts/verify_consistency.py --fix` → 확인 프롬프트 후 수정
- `python scripts/verify_consistency.py --fix -y` → 자동 수정

**비통합 원칙**: `set`/`init`은 이 스크립트를 호출하지 않는다. 개발자가 인프라 재배포 후 수동 실행.

### 3.8 `agentbox doctor` (신규 서브커맨드)

수동 테스트 직전에 **단일 read-only 명령**으로 모든 연결성·정합성을 점검.
`set`을 다시 돌리지 않고도 현재 상태가 시연 가능한 상태인지 확인.

**동작 (순서대로, 한 항목 실패해도 다음 항목 계속 검사하고 마지막에 종합 종료코드 결정)**:

| 항목 | 검사 내용 | 출처 |
|---|---|---|
| D1 | `.agentbox/` 레이아웃 8개 산출물 존재 | `dotagentbox.ensure_layout` (read-only mode) |
| D2 | deps 5개 (sops, aws, boto3, pyyaml, grpcio) | `init_deps.check_dep`, `check_python_pkg` |
| D3 | `~/.agentbox/certs/grpc/*` 4개 파일 존재 + 만료 ≥ 7일 | `openssl x509 -checkend` |
| D4 | proto stub import 가능 (`from agentbox.grpc import inspect_pb2`) | importlib |
| D5 | 프록시 `:8080` LISTEN + dashboard `:8000` LISTEN | socket |
| D6 | gRPC TCP connect (`GRPC_HOST:GRPC_PORT` 5초) | socket |
| D7 | **mTLS handshake** (3.4 7c와 동일 로직, 5초) | grpc.channel_ready_future |
| D8 | SaaS `/healthz` HTTP 200 (saas_url) | requests, 3초 |
| D9 | `scripts/verify_consistency.py --check` 결과 | subprocess (또는 함수 직접 호출) |

**CLI**:
- `agentbox doctor` → 표 형태 출력 (각 항목 OK/FAIL/SKIP + 사유), 종료코드 0(모두 OK) 또는 1(하나라도 FAIL)
- `agentbox doctor --json` → JSON 출력 (CI/스크립트용)
- `agentbox doctor --fix` → FAIL 항목 중 자동 복구 가능한 것만 수정. 복구 대상:
  - D3 만료/누락 → `gen_mtls_certs` 재실행
  - D4 stub 누락 → protoc 재실행
  - D5 프록시 미실행 → 백그라운드 `agentbox run` 시작
  - D9 불일치 → `verify_consistency.py --fix -y` 위임
  - 그 외(D1, D2, D6, D7, D8)는 자동 수정 안 함, FAIL로 보고

**원칙**: doctor는 `set`을 재실행하지 않는다 (반대로 set은 doctor의 모든 항목을 첫 실행 시 만족하도록 보장한다). 따라서 deps 자동 설치 같은 부작용 없음.

### 3.9 `agentbox help` 전면 갱신

현 `__main__.py`의 argparse epilog/description은 5개 서브커맨드(set, init, on, off, reset, destroy, ca, setup, status) 기준. 본 Task로 새로 생기는 `_on`/`_off`/`doctor` 및 제거되는 `ca`/`setup` 흐름을 반영해 다음을 갱신:

**최상위 parser**:
- description은 유지 (한 줄 요약)
- epilog의 "일반적인 사용 흐름" 표를 다음 순서로 재작성:
  ```
  # 1. 인프라 배포 (한 번)         ./scripts/deploy.sh
  # 2. 로컬 셋업 (한 번)            agentbox set [-y]
  # 3. 프로젝트 등록 (프로젝트마다) agentbox init ./myrepo [-y]
  # 4. 셸 활성화 (새 터미널마다)    agentbox on  /  agentbox off
  # 5. 상태 점검                    agentbox status   (요약)
                                  agentbox doctor   (전체 점검)
  # 6. 프록시 관리                  agentbox reset / agentbox destroy
  # 7. 인프라 정리                  ./scripts/destroy.sh
  ```

**서브커맨드별 help 갱신**:
- `set`: description에 "7a/b/c (health-check, gRPC TCP, mTLS handshake)" 명시
- `init`: 변경 없음 (기존 description 유지)
- `on`/`off`: 신규 표면 노출(현재는 hidden). description = "[shell] HTTPS_PROXY 설정/해제 (eval 패턴, ~/.bashrc 함수에서 호출)"
- `_on`/`_off`: hidden subparser (argparse `help=argparse.SUPPRESS`). description에 "eval `$(command agentbox _on)`로 호출됨" 명시
- `doctor`: 신규. description = "[진단] 수동 테스트 직전 단일 read-only 점검 (D1~D9, 종료코드 0/1)". epilog에 `--json`, `--fix` 옵션 예시
- `status`: description 마지막에 "전체 점검은 `agentbox doctor` 참고" 추가
- `ca` 서브커맨드 제거 (set에 흡수됨)
- `setup` 서브커맨드 제거 (set의 Step 6에 흡수됨)

**`agentbox --help` 출력 검증**: 단위 테스트 `test_help_text.py`로 위 흐름의 키워드 포함 여부 확인 (정규식 매칭).

### 3.11 테스트 패키지 추가

`requirements-dev.txt`에 다음 줄 추가 (PyPI 검증된 OSS):

```
pytest-mock>=3.10
moto[s3,kms]>=5.0
responses>=0.25
```

`pytest`, `pytest-asyncio`는 이미 있음(가정). 본 Task에서 새로 추가하는 의존성은 위 3개로 제한.

---

## 4. 영향받는 파일 (전체 목록)

### 4.1 신규 생성

| 경로 | 역할 |
|---|---|
| `src/agentbox/dotagentbox.py` | LayoutPaths, ensure_layout, 마이그레이션 |
| `src/agentbox/_activate.py` | `_on`/`_off` 서브커맨드 핸들러 (eval pattern) |
| `src/agentbox/encrypt.py` | `encrypt_and_upload.sh`의 Python 포팅 |
| `src/agentbox/ca_install.py` | `install_ca.sh`의 Python 포팅 |
| `src/agentbox/doctor_cmd.py` | `agentbox doctor` D1~D9 점검 (3.8) |
| `src/agentbox/grpc/handshake.py` | mTLS handshake 검증 헬퍼 (`verify_mtls_handshake(host, port, ca, cert, key, timeout)`) — set 7c와 doctor D7이 공유 |
| `scripts/verify_consistency.py` | 정합성 검사·수정 (별도 dev 도구) |
| `tests/unit/test_dotagentbox_layout.py` | ensure_layout, 마이그레이션 단위 |
| `tests/unit/test_config_loader_v2.py` | 다중 env_file 로드 |
| `tests/unit/test_set_cmd_v2.py` | 7단계 set 동작 (mock 위주) |
| `tests/unit/test_activate_cmd.py` | `_on`/`_off` stdout 검증 |
| `tests/unit/test_encrypt_module.py` | moto S3/KMS, sops fake CLI |
| `tests/unit/test_ca_install.py` | trust store hint, 권한 부족 graceful |
| `tests/unit/test_verify_consistency.py` | Terraform output mock, diff/fix |
| `tests/unit/test_handshake.py` | mTLS handshake 헬퍼 (정상/만료/CA 불일치/타임아웃 4 케이스) |
| `tests/unit/test_doctor_cmd.py` | D1~D9 각 항목 mock, 종합 종료코드, `--json`/`--fix` |
| `tests/unit/test_help_text.py` | `agentbox --help` 출력 키워드/흐름 정규식 매칭 |
| `tests/integration/test_set_e2e_v2.py` | 임시 `$HOME` + 임시 repo에서 set 전체 흐름 |
| `tests/integration/test_init_e2e_v2.py` | moto 환경에서 init 전체 흐름 |
| `tests/integration/test_run_lifecycle.py` | set → :8080 응답 → destroy → 해제 |

### 4.2 수정

| 경로 | 변경 |
|---|---|
| `src/agentbox/config.py` | env_file을 다중 경로 튜플로 |
| `src/agentbox/__main__.py` | `_on`/`_off`/`on`/`off`/`doctor` 서브커맨드 추가, `ca`/`setup` 제거, **전체 help epilog 갱신 (3.9)**, 경로 참조를 `dotagentbox` 통해 |
| `src/agentbox/set_cmd.py` | 7단계(7a/b/c) 흐름 + health-check polling + 로그 출력 + mTLS handshake (헬퍼 공유) |
| `src/agentbox/init_cmd.py` | `_PROJ_ROOT / ".sops.yaml"` → `~/.agentbox/sops.yaml`, 산출물 경로 갱신 |
| `src/agentbox/last_init.py` | `_DEFAULT_PATH`를 `<proj>/.agentbox/last_init.json`로 |
| `src/agentbox/proxy/ca.py` | mTLS 인증서 생성 함수 추가 (현 ensure_ca 확장) |
| `requirements-dev.txt` | pytest-mock, moto, responses 추가 |
| `.gitignore` | `.agentbox/` 추가, 기존 `.env`/`certs/`/`logs/` 라인은 유지(역호환) |
| `README.md` | scripts 정리 + .agentbox/ 레이아웃 섹션 갱신 |

### 4.3 삭제

| 경로 | 비고 |
|---|---|
| `scripts/activate.sh` | Python으로 포팅 |
| `scripts/deactivate.sh` | Python으로 포팅 |
| `scripts/install_ca.sh` | Python으로 포팅 |
| `scripts/gen_mtls_certs.sh` | Python으로 포팅 |
| `scripts/gen_proto.sh` | Python으로 포팅 |
| `scripts/encrypt_and_upload.sh` | Python으로 포팅 |
| `scripts/run.sh` | `agentbox run`이 대체 |
| `scripts/deploy_static.sh` | deploy.sh가 처리 |
| `scripts/check_ec2.sh` | 사용처 없음 |
| `scripts/update_my_ip.sh` | 사용처 없음 |
| `scripts/test_lifecycle_45.sh` | pytest로 대체 |
| `scripts/test_transparent.sh` | NG1 |
| `scripts/iptables_redirect.sh` | NG1 |
| `scripts/install_ebpf.sh` | NG1 |
| `scripts/setup_vm.sh` | 사용처 없음 |
| `.env`, `.env.endpoint`, `.sops.yaml` | 마이그레이션 후 자동 삭제 |
| `certs/grpc/` 원본 | 마이그레이션 후 자동 삭제 |

### 4.4 코드 영향 확인 후 별도 처리 필요

- `src/agentbox/__main__.py`의 `_run()`이 사용하는 `cfg.EBPF_STATS_LOG`/`TRANSPARENT_MODE` 분기: NG1 따라 분기 자체 제거.
- `src/agentbox/proxy/ebpf_stats.py`: NG1, 모듈 통째 삭제.
- 위 두 변경으로 깨지는 import는 `_run` 안 분기와 함께 정리.

---

## 5. 단위/통합 테스트 명세

### 5.1 검증 OSS 사용 방식

| OSS | 용도 |
|---|---|
| `pytest` | 러너, fixture |
| `pytest-asyncio` | 기존 `_run` 비동기 코드 테스트 |
| `pytest-mock` | `subprocess.run`, `Popen`, `socket` mock |
| `moto[s3,kms]` | `encrypt.py`의 S3 PutObject/KMS Encrypt 모킹 |
| `responses` | `init_cmd.py`의 `requests.get(/healthz)` 모킹 |
| `tmp_path`(pytest 내장) | `AGENTBOX_HOME` override로 격리 |

### 5.2 단위 테스트 케이스 (`tests/unit/`)

#### `test_dotagentbox_layout.py`
- T1: 빈 `$HOME` + 빈 repo에서 `ensure_layout()` → 8개 디렉토리/파일 생성 확인
- T2: `<repo>/.env` 존재 시 `~/.agentbox/env`로 이동, 원본 삭제 확인
- T3: `~/.agentbox/env` 이미 존재 + 내용 다름 → `.backup-<ts>` 생성 확인
- T4: 두 번 호출해도 결과 동일 (idempotent)
- T5: `<repo>/certs/grpc/*` 4개 파일 → `~/.agentbox/certs/grpc/`로 이동
- T6: `~/.agentbox/last_init.json` → `<repo>/.agentbox/last_init.json` 이동
- T7: `AGENTBOX_HOME` 환경변수 시 두 경로 모두 그 아래로

#### `test_config_loader_v2.py`
- T1: `~/.agentbox/env`에 `GRPC_HOST=foo`, `~/.agentbox/endpoint`에 `EC2_GRPC_HOST=bar` → `cfg.GRPC_HOST=="foo"` 확인
- T2: 두 파일 다 없음 → 기본값 fallback
- T3: `endpoint`가 `env`의 같은 키를 override (의도된 우선순위 검증)

#### `test_set_cmd_v2.py`
- T1: 모든 deps OK + 산출물 존재 → 7단계(7a/b/c) 전부 통과, exit 0
- T2: sops 없음 + `-y` → 자동 설치 mock 호출됨
- T3: sops 없음 + `-y` 없음 → exit 4
- T4: CA 없음 → 생성 + Phase 4 OK
- T5: proto stub 없음 → `grpc_tools.protoc` mock 호출
- T6: background run 후 `:8080` LISTEN 안 됨 → log 끝 50줄 stdout, exit 7
- T7: gRPC `GRPC_HOST` TCP fail (7b) → exit 7 + 가이드 메시지
- T8: TCP OK 이나 mTLS handshake 실패 (7c, `channel_ready_future` raise) → exit 7 + "CA/client cert 점검" 가이드

#### `test_handshake.py`
- T1: ssl_credentials + ready future timeout 5초 내 OK → True
- T2: 만료된 endpoint.crt mock → grpc.FutureTimeoutError → False + 사유 "expired"
- T3: CA 불일치 (다른 CA로 서명된 fake server) → False + 사유 "CA mismatch"
- T4: host:port unreachable → False + 사유 "unreachable"

#### `test_doctor_cmd.py`
- T1: 9개 항목 전부 OK mock → 표 출력, exit 0
- T2: D5(:8080) fail → 그 행만 FAIL, exit 1, 나머지는 계속 평가됨 (early-exit 아님 확인)
- T3: D7 mTLS fail → exit 1 + 가이드
- T4: D9 verify_consistency diff → exit 1, diff 요약 표 안에 표시
- T5: `--json` → 스키마 `{items: [{id, status, detail}], exit_code}` 일치
- T6: `--fix` 시 D3/D4/D5/D9는 복구 호출, D1/D2/D6/D7/D8은 호출 안 됨

#### `test_help_text.py`
- T1: `agentbox --help` 출력에 다음 키워드 전부 포함: "deploy.sh", "agentbox set", "agentbox init", "agentbox on", "agentbox off", "agentbox doctor", "agentbox status", "agentbox reset", "agentbox destroy", "destroy.sh"
- T2: 제거된 키워드 부재: "agentbox ca", "agentbox setup" (서브커맨드 자체 제거 확인)
- T3: `agentbox doctor --help` 출력에 "D1", "--json", "--fix", "read-only" 포함
- T4: `agentbox set --help` 출력에 "7a", "7b", "7c", "mTLS handshake" 포함
- T5: hidden 서브커맨드 `_on`/`_off`는 `agentbox --help` 출력에 노출 안 됨 (argparse SUPPRESS 확인)

#### `test_activate_cmd.py`
- T1: `_on` stdout이 `export HTTPS_PROXY=...` 3줄 정확히 출력
- T2: `:8080`이 LISTEN 안 됨 → background `agentbox run` Popen mock 호출
- T3: `_off` stdout이 `unset` 3줄
- T4: stderr는 user-facing 메시지, stdout은 export만 (eval 안전성)

#### `test_encrypt_module.py`
- T1 (moto): 임시 dir 4개 파일 → SOPS fake CLI(mocker fixture) → S3 upload mock → 모든 파일이 `s3://{bucket}/encrypted_code/{pid}/`에 PutObject 됐는지 확인
- T2: SOPS CLI 비-zero → exit 5
- T3: KMS 미존재 → moto가 raise, 적절한 에러 메시지

#### `test_ca_install.py`
- T1: trust store에 이미 있음(openssl verify mock=0) → noop
- T2: 없음 + sudo 가능 → install 명령 호출
- T3: sudo 불가 → hint stdout만, exit 0 (warning)

#### `test_verify_consistency.py`
- T1: tf output JSON mock + `~/.agentbox/*` 일치 → `--check` exit 0
- T2: IP 다름 → `--check` exit 1 + JSON diff 출력
- T3: `--fix -y` → 파일 덮어써짐
- T4: KMS ARN diff → `sops.yaml` 갱신
- T5: cert 만료 5일 → diff에 cert 항목, `--fix`에서 mTLS 재생성

### 5.3 통합 테스트 케이스 (`tests/integration/`)

#### `test_set_e2e_v2.py`
- T1: `monkeypatch.setenv("AGENTBOX_HOME", str(tmp_path / "global"))`, 임시 repo, deps mock OK → `run_set(args)` exit 0, 산출물 8개 검증
- T2: 같은 repo 두 번 실행 → idempotent, 마이그레이션 한 번만
- T3: 마이그레이션 후 원본 `.env`/`.sops.yaml` 부재 확인

#### `test_init_e2e_v2.py` (moto)
- T1: `aws_credentials` mock + `mock_aws`(S3+KMS) + sops fake CLI + responses로 `/healthz` 200 + socket.create_connection mock → `init(...)` exit 0, `<repo>/.agentbox/last_init.json` 생성 확인
- T2: `/healthz` 502 → exit 6
- T3: gRPC TCP fail → exit 7

#### `test_run_lifecycle.py`
- T1: 백그라운드 `agentbox run` 실제 fork → `:8080` health-check 통과 → `<repo>/.agentbox/pid` 존재 → `agentbox destroy` → port 해제
- T2: `set` 두 번 연속 호출 → 두 번째는 "프록시 이미 실행 중" 분기

### 5.4 회귀 보호

기존 `tests/unit/test_*.py` 25개와 `tests/integration/test_*.py` 18개 모두 통과 유지.
경로 변경으로 깨질 가능성이 큰 것:
- `test_set_e2e.py`, `test_status_e2e.py`, `test_init_e2e.py`, `test_last_init.py`,
  `test_set_cmd.py`, `test_status_cmd.py`, `test_init_cmd.py`

위 7개는 본 Task가 끝날 때 `AGENTBOX_HOME` fixture를 활용하도록 **최소 수정**.

---

## 6. 수동 E2E 체크리스트 (Task-7 종료 검증)

코드 자동화 없음. `docs/manual-e2e.md` 신규 파일에 기록.

1. `./scripts/deploy.sh -auto-approve` 통과, `terraform output -raw app_public_ip` 비어있지 않음
2. `agentbox set -y` 통과, 출력에 `Step 7a: proxy LISTEN OK`, `Step 7b: gRPC TCP OK`, `Step 7c: mTLS handshake OK` 3줄 모두 포함
3. **`agentbox doctor` 실행 → D1~D9 9개 항목 모두 OK, exit 0** (수동 테스트 직전 단일 점검)
4. 새 터미널: `agentbox on`, `echo $HTTPS_PROXY`가 `http://127.0.0.1:8080`
5. 또 다른 터미널 (별도 Claude Code): `claude` 실행
6. Claude Code에 "ping" 등 임의 prompt 전송
7. dashboard `http://localhost:8000/audit` 새 행 표시 (request_id, prompt 미리보기)
8. EC2: `aws ssm send-command ... 'journalctl -u agentbox-grpc -n 50'` 출력에 `Inspect` RPC 로그
9. `agentbox off`, `agentbox destroy`로 정리

각 단계 OK/FAIL 체크박스를 `docs/manual-e2e.md`에 표 형태로 둠.

---

## 7. Todo Phases (재개 가능 체크리스트)

각 phase는 독립 커밋 가능. 중단 후 재개 시 마지막 unchecked 항목부터 진행.
각 phase는 `verify:` 줄에 적힌 명령으로 합격 검증.

### Phase A — 기반 (디렉토리 + config)

- [x] **A1**: `src/agentbox/dotagentbox.py` 신규 (LayoutPaths, ensure_layout, 마이그레이션)
  - verify: `pytest tests/unit/test_dotagentbox_layout.py -x`
- [ ] **A2**: `src/agentbox/config.py` env_file 다중 경로화
  - verify: `pytest tests/unit/test_config_loader_v2.py -x`
- [ ] **A3**: `src/agentbox/last_init.py`의 `_DEFAULT_PATH`를 LayoutPaths 통해 `<proj>/.agentbox/last_init.json`로
  - verify: `pytest tests/unit/test_last_init.py -x` (기존 테스트는 `AGENTBOX_HOME` fixture 적용)
- [ ] **A4**: `requirements-dev.txt`에 pytest-mock, moto[s3,kms], responses 추가
  - verify: `pip install -r requirements-dev.txt` 무오류

### Phase B — set 흐름 재구성

- [ ] **B1**: `src/agentbox/proxy/ca.py`에 mTLS 인증서 생성 함수 추가
  - verify: `pytest tests/unit/test_ca.py -x`
- [ ] **B2**: `src/agentbox/set_cmd.py` 7단계화 (ensure_layout → deps → env → CA/mTLS → proto → shell → run+health+gRPC)
  - verify: `pytest tests/unit/test_set_cmd_v2.py -x`
- [ ] **B3**: health-check polling + 실패 시 로그 출력
  - verify: `pytest tests/unit/test_set_cmd_v2.py::test_run_log_dump -x`
- [ ] **B4**: gRPC TCP connect 검증(7b) + 가이드 메시지
  - verify: `pytest tests/unit/test_set_cmd_v2.py::test_grpc_connect_fail -x`
- [ ] **B5**: `src/agentbox/grpc/handshake.py` 신규 (`verify_mtls_handshake`)
  - verify: `pytest tests/unit/test_handshake.py -x`
- [ ] **B6**: set Step 7c에서 `verify_mtls_handshake` 호출 + exit 7 분기
  - verify: `pytest tests/unit/test_set_cmd_v2.py::test_mtls_handshake_fail -x`

### Phase C — on/off Python 포팅

- [ ] **C1**: `src/agentbox/_activate.py` 신규 (`on_command`, `off_command`)
- [ ] **C2**: `src/agentbox/__main__.py`에 `_on`/`_off` 서브커맨드 등록 (hidden help)
- [ ] **C3**: `_install_shell_integration` 내용을 `eval "$(command agentbox _on)"` 패턴으로 갱신
  - verify: `pytest tests/unit/test_activate_cmd.py -x`
- [ ] **C4**: `scripts/activate.sh`, `scripts/deactivate.sh` 삭제

### Phase D — init/encrypt Python 포팅

- [ ] **D1**: `src/agentbox/encrypt.py` 신규 (boto3 + sops CLI 래퍼)
  - verify: `pytest tests/unit/test_encrypt_module.py -x`
- [ ] **D2**: `src/agentbox/init_cmd.py`에서 `encrypt_and_upload.sh` 호출 제거, `encrypt.encrypt_and_upload()` 호출로 교체
  - verify: `pytest tests/unit/test_init_cmd.py tests/integration/test_init_e2e_v2.py -x`
- [ ] **D3**: `init_cmd.py`의 `.sops.yaml` 경로를 `~/.agentbox/sops.yaml`로
- [ ] **D4**: `scripts/encrypt_and_upload.sh` 삭제

### Phase E — CA install Python 포팅

- [ ] **E1**: `src/agentbox/ca_install.py` 신규
  - verify: `pytest tests/unit/test_ca_install.py -x`
- [ ] **E2**: `scripts/install_ca.sh` 삭제, `activate.sh`에서의 호출 흔적도 제거 (이미 C4에서 삭제됐는지 확인)

### Phase F — proto stub 내장

- [ ] **F1**: `src/agentbox/set_cmd._ensure_proto_stub()` 추가
- [ ] **F2**: `scripts/gen_proto.sh` 삭제, `Makefile` 등에서 호출 흔적 grep
- [ ] **F3**: `scripts/gen_mtls_certs.sh` 삭제 (B1에서 Python으로 옮김)

### Phase G — transparent 모드 제거 (NG1)

- [ ] **G1**: `src/agentbox/config.py`에서 `TRANSPARENT_MODE`, `EBPF_STATS_LOG` 필드 삭제
- [ ] **G2**: `src/agentbox/__main__.py::_run`의 transparent 분기 삭제
- [ ] **G3**: `src/agentbox/proxy/ebpf_stats.py` 파일 삭제
- [ ] **G4**: `scripts/iptables_redirect.sh`, `scripts/install_ebpf.sh`, `scripts/test_transparent.sh` 삭제
  - verify: `pytest tests/unit -x -k "not transparent"`

### Phase H — 잔여 scripts 정리

- [ ] **H1**: `scripts/check_ec2.sh`, `scripts/update_my_ip.sh`, `scripts/test_lifecycle_45.sh`,
  `scripts/setup_vm.sh`, `scripts/deploy_static.sh`, `scripts/run.sh` 삭제
- [ ] **H2**: `scripts/` 잔존 파일이 `deploy.sh`, `destroy.sh`, `redeploy_idempotency.sh`, `verify_consistency.py` 4개인지 확인
  - verify: `ls scripts/ | wc -l` → 4

### Phase I — 정합성 검사 스크립트

- [ ] **I1**: `scripts/verify_consistency.py` 신규
  - verify: `pytest tests/unit/test_verify_consistency.py -x`
- [ ] **I2**: `--check`/`--fix`/`--fix -y` 세 동작 모두 테스트 통과

### Phase N — `agentbox doctor` + help 갱신

- [ ] **N1**: `src/agentbox/doctor_cmd.py` 신규 (D1~D9 함수형 분리)
  - verify: `pytest tests/unit/test_doctor_cmd.py -x`
- [ ] **N2**: `src/agentbox/__main__.py`에 `doctor` 서브커맨드 등록 (`--json`, `--fix` 옵션)
  - verify: `agentbox doctor --help` 출력 확인
- [ ] **N3**: `__main__.py`의 최상위 epilog "일반적인 사용 흐름"을 3.9 표대로 갱신
- [ ] **N4**: `on`/`off` 서브커맨드를 정식 노출(현재 hidden), `_on`/`_off`는 SUPPRESS
- [ ] **N5**: `ca`/`setup` 서브커맨드 제거 (set에 흡수됨을 description으로 안내)
- [ ] **N6**: `set` 서브커맨드 description에 "7a/b/c (LISTEN, gRPC TCP, mTLS handshake)" 명시
- [ ] **N7**: `status` description 끝에 "전체 점검은 agentbox doctor 참고" 추가
  - verify (N3~N7 통합): `pytest tests/unit/test_help_text.py -x`

### Phase J — 통합 테스트

- [ ] **J1**: `tests/integration/test_set_e2e_v2.py` 통과
- [ ] **J2**: `tests/integration/test_init_e2e_v2.py` 통과
- [ ] **J3**: `tests/integration/test_run_lifecycle.py` 통과

### Phase K — 회귀 (기존 테스트 호환)

- [ ] **K1**: `tests/conftest.py`에 `agentbox_home` autouse fixture 추가 (`AGENTBOX_HOME=tmp_path/global`)
- [ ] **K2**: 기존 7개 테스트(`test_set_e2e.py`, `test_status_e2e.py`, `test_init_e2e.py`,
  `test_last_init.py`, `test_set_cmd.py`, `test_status_cmd.py`, `test_init_cmd.py`)의 경로 단언만 갱신
  - verify: `pytest tests/ -x`

### Phase L — 문서

- [ ] **L1**: `README.md` `.agentbox/` 레이아웃 + scripts 목록 갱신
- [ ] **L2**: `docs/manual-e2e.md` 신규 (섹션 6)

### Phase M — 최종 일괄 검증

- [ ] **M1**: `pytest tests/ -x --cov=agentbox` 전부 통과, 커버리지 ≥ 기존 수준
- [ ] **M2**: `python scripts/verify_consistency.py --check` 통과 (인프라가 살아있다면)
- [ ] **M3**: `agentbox doctor` 실행 → D1~D9 모두 OK, exit 0
- [ ] **M4**: 수동 E2E 체크리스트 (섹션 6) 9단계 모두 OK

---

## 8. 위험 / 완화

| 위험 | 영향 | 완화 |
|---|---|---|
| 마이그레이션 중 OneDrive 동기화 충돌(메모리 알려진 이슈) | 파일 락 → 부분 마이그레이션 | 마이그레이션 시작 시 `<repo>/.env*` 잠금 확인, `OneDrive 종료 후 재실행` 안내; 임시 디렉토리에 먼저 쓰고 atomic rename |
| 기존 7개 테스트가 OS 절대경로 가정 | 회귀 실패 | Phase K1의 autouse fixture로 격리 |
| `eval "$(command agentbox _on)"`이 잘못된 stdout 시 shell 손상 | 다음 명령들이 깨짐 | `_on` 종료 시 항상 `return 0` 보장 + 단위 테스트 T4 |
| moto 5.x API 변경 | 단위 테스트만 영향 | `requirements-dev.txt`에 `>=5.0` 핀, 실패 시 5.0.x로 다운핀 |
| Terraform output JSON 키가 환경마다 다름 | `verify_consistency` 오인식 | 부재 키는 warning만, 절대 에러로 처리하지 않음 |
| `_PROJ_ROOT` 가정이 editable install이 아닐 때 깨짐 | 경로 오류 | 본 Task는 editable install 가정(기존과 동일), 비-editable는 NG로 명시 |

---

## 9. 인코딩 / 스타일

- 모든 신규/수정 Python 파일은 UTF-8 (no BOM), LF.
- 한글 문자열은 그대로 사용 (현 코드와 동일).
- 신규 파일 첫 줄에 인코딩 선언 불필요 (Python3 기본 UTF-8).
- 본 Task-7.md 자체도 UTF-8 (no BOM).

---

## 10. 완료 조건 (Definition of Done)

다음이 모두 참일 때 Task-7 완료:

1. `ls scripts/` 결과가 정확히 `deploy.sh destroy.sh redeploy_idempotency.sh verify_consistency.py`
2. `<repo>/.env`, `<repo>/.env.endpoint`, `<repo>/.sops.yaml`, `<repo>/certs/grpc/`,
   `<repo>/logs/`, `<repo>/.agentbox.pid` 모두 부재 (또는 빈 `.migrated` 마커만 남음)
3. `~/.agentbox/env`, `~/.agentbox/endpoint`, `~/.agentbox/sops.yaml`,
   `~/.agentbox/certs/grpc/{agentbox-ca.crt,endpoint.crt,endpoint.key}` 모두 존재
4. `pytest tests/ -x` 100% 통과 (신규 단위 + 통합 + 기존 회귀)
5. `agentbox set -y` 1회 + 출력에 `Step 7a/7b/7c` OK 3줄 모두 포함
6. `agentbox doctor` 실행 → D1~D9 9개 모두 OK, exit 0
7. `agentbox on` 후 `echo $HTTPS_PROXY`가 `http://127.0.0.1:8080`
8. `python scripts/verify_consistency.py --check` exit 0 (인프라 살아있는 환경에서)
9. `agentbox --help` 출력에 3.9 표의 7개 흐름 키워드 모두 포함, `ca`/`setup` 부재
10. `docs/manual-e2e.md` 9단계 모두 OK 체크
11. `README.md`의 scripts 섹션과 `.agentbox/` 레이아웃이 실제와 일치

---

## 11. 실행 지침 (Claude Code에게)

- 본 Task-7.md 변경 없이 그대로 두고, 사용자가 "Task-7 진행" 또는 "Phase X 시작" 등으로 명시할 때만 코드 변경.
- 각 Phase는 별도 커밋. 커밋 메시지 prefix: `feat(task-7):`, `refactor(task-7):`, `test(task-7):`, `chore(task-7):`.
- Phase 중간 실패 시 `Phase X 실패 — 사유: ...` 를 stdout으로 보고하고 다음 Phase 진행 금지.
- 매 Phase 종료 시 `verify:` 줄의 명령을 실행하고 결과를 보고.
- OneDrive 동기화로 인한 파일 락은 사용자에게 OneDrive 일시 중지를 요청 (기존 메모리 가이드).
- 단위/통합 테스트 코드도 본 플랜의 Phase에 포함되어 있음. Phase A/B/C/D/E/F/G/I/J 각각에서 해당 테스트 파일 함께 작성.

---

Made by JeonMyeongHwan (Task-7 plan, 2026-05-12)
