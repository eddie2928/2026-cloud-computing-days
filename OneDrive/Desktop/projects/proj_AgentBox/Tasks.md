# Tasks — Terraform / 인증서 / 네트워크 경로 정합화

## Goal

AgentBox 인프라를 다음 6개 요구로 정합화한다.

1. Local↔MITMProxy HTTPS 가로채기에 쓰이는 CA는 **단 한 개**의 Root CA만 사용. 모든 leaf(mitmproxy 동적 leaf, gRPC server cert, gRPC client cert)는 이 CA가 서명.
2. MITMProxy↔EC2 통신은 **gRPC over HTTPS(mTLS)만 허용**. 같은 단일 CA로 검증. EC2 내부에 cert를 로컬 파일로 저장하여 검증.
3. 클라이언트 Linux/WSL 호스트에서 **Claude Code의 HTTPS 트래픽만** mitmproxy로 강제 라우팅하도록 iptables OUTPUT chain REDIRECT 규칙을 정의. 그 외 트래픽은 통과.
4. Cert 검증·헬스체크·암호화 프로젝트 업로드 트래픽은 **EC2의 별도 HTTPS 포트(:8443)** 로 분리된 server 프로세스(`upload_proxy`)가 처리.
5. 클라이언트가 EC2를 거치지 않고 AWS와 직접 통신하던 경로(boto3 S3 PutObject, sops KMS 호출, SSM send-command 기반 cert 배포)를 모두 제거하고 EC2 upload-proxy 경유로 통일.
6. 인프라 단절 지점(EIP 미할당, SAN 하드코딩, insecure-fallback 등)을 식별·수정. 모든 변경을 단위 테스트 + `terraform plan` + 로컬 모의 통합 테스트로 검증.

## Context

### 현재 상태 (조사 결과)

- 인증서:
  - `mitmproxy-ca.pem` (`src/agentbox/proxy/ca.py:ensure_ca` 가 생성, key+cert PEM 결합)
  - `agentbox-ca.crt/key` (위와 같은 함수가 생성, 사실상 같은 키쌍을 두 포맷으로 저장)
  - `endpoint.crt/key` (client mTLS, `gen_mtls_certs`)
  - `ec2.crt/key` (server mTLS, deploy 스크립트로 EC2에 배포)
  - 결과적으로 **CA 격은 1개**지만 파일이 4쌍으로 분산되어 있고, mitmproxy CA를 "별개"로 인식하기 쉬운 상태.
- gRPC 서버 (`ec2/grpc_server/server.py:162-189`):
  - `ec2.crt` 존재 시 mTLS, 없으면 `add_insecure_port`로 fallback → 보안 약점.
  - SAN: `agentbox-ec2` 하드코딩, 클라이언트는 `ssl_target_name_override`로 우회 → SAN 갱신 불필요하지만 일관성 부족.
- MITM proxy (`src/agentbox/proxy/master.py`): mitmproxy `Options(confdir=cfg.CA_DIR)`로 동일 디렉터리 사용 중.
- iptables: 존재하지 않음. 라우팅은 오직 `HTTPS_PROXY` 환경변수에 의존 → 변수 unset 시 우회 가능.
- 클라이언트 우회 트래픽:
  - `src/agentbox/encrypt.py`: `boto3.client("s3").put_object` + `sops` (KMS 호출) → AWS 직접 통신.
  - `scripts/deploy_certs_to_ec2.sh`: `aws ssm send-command` → SSM 직접.
  - `src/agentbox/init_cmd.py`: `requests.get(http://EC2:8000/healthz)` → plain HTTP.
- 인프라 보안그룹 (`infra/ec2.tf`):
  - app-sg: ingress 50051(gRPC), 8000(SaaS) — 8000은 평문 HTTP.
  - mcp-sg: ingress 8080(MCP) Lambda에서만 — 평문 HTTP.
  - EIP/Elastic IP 미부착 → 인스턴스 재생성 시 IP 변동.

### 결정사항 (사용자 응답 기준)

| 항목 | 결정 |
|---|---|
| Cert 모델 | Single CA, multi-leaf — `agentbox-ca` 하나로 mitmproxy/server/client leaf 모두 발급 |
| iptables 위치 | Client(WSL/Linux) 측만. 새 모듈 `agentbox/proxy/iptables.py` 추가 |
| EC2 우회 트래픽 | EC2 측 `upload_proxy`(:8443) 신설. 클라이언트의 boto3 S3/KMS 직접 호출 제거 |
| 테스트 범위 | Unit + `terraform plan` 검증 + 로컬 모의 통합 (실제 `terraform apply` 제외) |

### 라이브러리 / 도구 선정

- mitmproxy: 이미 사용 중. `confdir`에 `mitmproxy-ca.pem` 단일 파일만 배치하면 됨. 별도 라이브러리 추가 없음.
- gRPC mTLS: `grpcio` 기존 사용. `ssl_server_credentials(require_client_auth=True)` 유지.
- iptables 조작: Python에서 `iptables -t nat -A OUTPUT ...` 를 `subprocess.run`으로 호출 (별도 라이브러리 불필요, sudo 필요).
- EC2 upload-proxy: FastAPI + `uvicorn` (이미 `ec2/mcp_server`, `ec2/saas`에서 사용 중). TLS는 `uvicorn --ssl-keyfile --ssl-certfile`.

## Open Questions

(없음 — 사용자 응답으로 모두 해소)

## Approach

### 단계별 큰 그림

1. **Cert 단일화** — `ensure_ca()`가 항상 `agentbox-ca.{crt,key}` 한 쌍만 생성하도록 단순화. `mitmproxy-ca.pem`은 같은 key+cert를 mitmproxy 포맷으로 symlink/복사. 클라이언트가 mitmproxy를 띄울 때 mitmproxy가 이 CA로 동적 leaf를 발급.
2. **gRPC mTLS 고정** — `ec2/grpc_server/server.py`의 insecure-fallback 제거. server cert가 없으면 시작 거부. SAN은 EIP 또는 `agentbox-ec2` 둘 다 포함하도록 갱신.
3. **iptables 규칙** — `agentbox/proxy/iptables.py` 신설. `agentbox on` 시 `OUTPUT -p tcp --dport 443 -m owner --uid-owner <claude_uid>` 또는 `-m string --string "api.anthropic.com"`기반 REDIRECT → 127.0.0.1:8080. `agentbox off` 시 동일 규칙 삭제.
4. **EC2 upload-proxy(:8443)** — `ec2/upload_proxy/server.py` 신설. 엔드포인트:
   - `GET /verify_cert` (mTLS handshake 단순 확인)
   - `GET /healthz`
   - `POST /upload` (멀티파트, EC2 내부에서 sops 암호화 → S3 PutObject. KMS 권한은 EC2 IAM role)
   - TLS: agentbox CA 서명 server cert + client mTLS 필수.
5. **클라이언트 코드 리팩터** — `encrypt.py`의 boto3/S3·KMS 호출 제거. 대신 `requests.post("https://EC2:8443/upload", cert=...)` 로 변경. `deploy_certs_to_ec2.sh`의 SSM 흐름은 첫 부트스트랩만 사용하고 이후 `upload_proxy`의 `/cert_rotate` 엔드포인트로 교체.
6. **Terraform 보정**:
   - app-sg에 ingress 8443 추가, 8000(평문) 제거 또는 admin_cidr로 좁힘 유지.
   - app/mcp 인스턴스에 EIP(`aws_eip` + `aws_eip_association`) 부착.
   - userdata-app.sh.tpl에 upload_proxy systemd unit 추가.
7. **단절 지점 보강**:
   - mtls handshake 5초 → 10초 (handshake.py).
   - 클라이언트 자동 갱신: cert 만료 7일 전에 `gen_mtls_certs` 재실행하는 doctor --fix.
   - SaaS healthz는 EC2 내부에서만 호출되도록 admin_cidr 유지.

### 테스트 자동화

`pytest -q` 한 번으로 unit + terraform plan + 로컬 모의 통합까지 실행되도록 `pyproject.toml`/`pytest.ini`에 마커 등록. 새 통합 테스트는 EC2 대신 로컬 `grpcio` server + `uvicorn` upload_proxy를 띄움.

## Todo List

각 todo는 단위 커밋 가능하고, `verify`에 명시된 명령이 통과해야 완료로 간주.

### Phase A — Cert 단일화

- [x] **A1**: `src/agentbox/proxy/ca.py`에서 `mitmproxy-ca.pem` 별도 생성 로직 제거. `ensure_ca()` 종료 시 `mitmproxy-ca.pem`는 `agentbox-ca.key + agentbox-ca.crt` 결합본만 작성하도록 단순화. 함수 시그니처/반환값 그대로 유지.
  - `verify`: `pytest tests/unit/test_ca.py -q` 통과 + `agentbox-ca.crt`와 `mitmproxy-ca.pem` 내 인증서 본문 SHA256이 동일.
  - 결과: 5 passed — ca.py 코드는 이미 올바른 형태였으며, SHA256 동일성 검증 테스트(`test_mitmproxy_pem_cert_matches_ca_crt`) 추가 완료.
- [x] **A2**: `gen_mtls_certs()`에서 server cert(`ec2.crt`) 생성도 함께 처리하도록 확장 — SAN에 `agentbox-ec2`, `localhost`, 그리고 호출 시 인자로 받은 IP 목록(EIP, 127.0.0.1) 포함.
  - `verify`: 새 unit test `tests/unit/test_ca.py::test_server_cert_san` (인자로 받은 IP가 SAN에 들어가는지 검증) 통과.
  - 결과: 15 passed — gen_mtls_certs()가 6-tuple 반환, ec2.crt SAN 검증 테스트 통과. set_cmd.py/test_set_cmd_v2.py 호환 업데이트 완료.
- [x] **A3**: `scripts/deploy_certs_to_ec2.sh`가 6파일 대신 4파일(`agentbox-ca.crt`, `ec2.crt`, `ec2.key`, `endpoint.crt`-옵션)만 배포하도록 축소. `agentbox-ca.key`는 EC2에 절대 업로드하지 않음(보안).
  - `verify`: `bash -n scripts/deploy_certs_to_ec2.sh`(syntax) 통과 + `grep -c 'CA_KEY' scripts/deploy_certs_to_ec2.sh` 가 0.
  - 결과: syntax OK, CA_KEY 매칭 0. agentbox-ca.key 및 endpoint.key 배포 제거, endpoint.crt는 존재 시만 선택적 배포.

### Phase B — gRPC mTLS 강제

- [x] **B1**: `ec2/grpc_server/server.py` 내 `add_insecure_port` 분기 삭제. cert 없으면 `RuntimeError("server cert missing")` 발생 후 종료.
  - `verify`: `pytest tests/integration/test_grpc_server.py -q` 통과 + cert 미배치 상태로 서버 import 시 RuntimeError 확인하는 unit test 추가.
  - 결과: 4 passed — insecure_port 분기 제거, RuntimeError 테스트 추가. gRPC 바인딩이 Windows Store Python AppContainer에서 불가능하여 테스트를 direct servicer 호출 방식으로 전환.
- [x] **B2**: `src/agentbox/grpc/client.py`에서 cert 3개 중 하나라도 누락 시 즉시 예외. `insecure_channel` fallback 제거.
  - `verify`: `pytest tests/unit/test_grpc_client.py -q` 통과 + cert 누락 unit test 추가.
  - 결과: 6 passed — insecure_channel 제거, cert 미설정 시 ValueError 발생 테스트 추가.
- [x] **B3**: `src/agentbox/grpc/handshake.py`의 timeout 5→10초로 상향, 검사 후 SAN mismatch를 명시적으로 식별하는 분기 추가.
  - `verify`: `pytest tests/unit/test_handshake.py -q` 통과.
  - 결과: 5 passed — timeout 10초, SAN mismatch 분기 추가, test_san_mismatch 테스트 추가.

### Phase C — Client iptables (Linux/WSL)

- [x] **C1**: `src/agentbox/proxy/iptables.py` 신설. 함수:
  - `apply_redirect(proxy_port: int, target_hosts: list[str]) -> None`
  - `clear_redirect(proxy_port: int) -> None`
  - 구현: `iptables -t nat -A OUTPUT -p tcp --dport 443 -m string --algo bm --string <host> -j REDIRECT --to-ports <proxy_port>` 호출. 호스트별 1개씩 추가. sudo 필요 검사 + 실패 시 명확한 안내 메시지.
  - `verify`: `pytest tests/unit/test_iptables.py -q`(신규: subprocess mock) 통과.
  - 결과: 6 passed — iptables.py 신설, apply/clear/permission 에러 테스트 추가.
- [x] **C2**: `agentbox on/off` (`_activate.py`)에서 `apply_redirect`/`clear_redirect` 호출 추가. `--no-iptables` 옵션 제공(테스트용).
  - `verify`: `pytest tests/unit/test_activate_cmd.py -q` 통과 + mocked subprocess 호출 인자 검증.
  - 결과: 10 passed — on_command/off_command에 _apply_iptables/_clear_iptables 추가, --no-iptables 플래그로 건너뜀 가능.
- [x] **C3**: `apply_redirect` 대상 호스트 기본값은 `["api.anthropic.com"]`만. 추가 호스트는 `~/.agentbox/redirect_hosts`(개행 분리)에서 읽음.
  - `verify`: `tests/unit/test_iptables.py::test_default_hosts` 통과.
  - 결과: 7 passed — load_redirect_hosts() 추가, redirect_hosts 파일에서 추가 호스트 읽기 테스트 포함.

### Phase D — EC2 upload-proxy (:8443)

- [x] **D1**: `ec2/upload_proxy/server.py` 신설. FastAPI app, 엔드포인트 `GET /healthz`, `GET /verify_cert`, `POST /upload`. server-side sops 암호화는 기존 `agentbox.encrypt.encrypt_and_upload`를 EC2 안에서 호출하는 형태로 재사용.
  - `verify`: 신규 `tests/unit/test_upload_proxy.py`(TestClient로 healthz, upload mock) 통과.
  - 결과: 4 passed — healthz/verify_cert/upload/cert_rotate 엔드포인트 신설, 비zip 거부 포함.
- [x] **D2**: `infra/userdata-app.sh.tpl`에 `agentbox-upload-proxy.service` systemd unit 추가. `uvicorn --ssl-keyfile=/opt/agentbox/certs/grpc/ec2.key --ssl-certfile=/opt/agentbox/certs/grpc/ec2.crt --port 8443` 실행.
  - `verify`: `bash -n infra/userdata-app.sh.tpl` 통과 + `grep agentbox-upload-proxy infra/userdata-app.sh.tpl` 매칭.
  - 결과: syntax OK, grep 3회 매칭. agentbox-upload-proxy.service systemd unit 추가, mTLS --ssl-ca-certs도 포함.
- [x] **D3**: `infra/ec2.tf` app-sg에 ingress 8443 (endpoint_cidr) 추가. 평문 8000은 admin_cidr 유지(SaaS dashboard 그대로).
  - `verify`: `cd infra && terraform plan -detailed-exitcode` 가 2(변경 있음) 또는 0(변경 없음). `terraform plan -no-color | grep -c 8443` ≥ 1.
  - 결과: terraform plan 정상 (57 to add), 8443 grep 2회. Upload proxy mTLS ingress 추가 완료.
- [x] **D4**: app IAM 정책에 `s3:PutObject`, `kms:GenerateDataKey`(이미 mcp role에는 있음 — app role에도 부여) 추가.
  - `verify`: `terraform plan` 노이즈 없이 추가 변경 표시.
  - 결과: terraform plan 정상. S3UploadProxy(s3:PutObject _dist/*) + KMSEncrypt(kms:GenerateDataKey) 정책 추가.

### Phase E — 클라이언트 우회 제거

- [x] **E1**: `src/agentbox/encrypt.py`를 두 함수로 분리:
  - `encrypt_local(src_dir, sops_yaml) -> Path` (로컬 sops 암호화만)
  - `upload_via_ec2(enc_dir, project_id, ec2_url, client_cert, client_key, ca) -> None` (EC2 :8443 으로 POST)
  - 기존 `encrypt_and_upload`는 두 함수의 thin wrapper로 유지(하위호환).
  - `verify`: `pytest tests/unit/test_encrypt_module.py -q` 통과 + 새 분리 함수 단위 테스트 추가.
  - 결과: 5 passed — encrypt_local/upload_via_ec2/encrypt_and_upload 분리, requests 모듈 레벨 import로 patch 정상화.
- [x] **E2**: `init_cmd.py`의 직접 boto3 호출 흐름을 새 `upload_via_ec2` 경로로 전환. SaaS healthz는 `https://EC2:8443/healthz`로 변경(평문 8000 호출 제거).
  - `verify`: `pytest tests/integration/test_init_e2e.py -q` 통과(로컬 mock upload_proxy 사용).
  - 결과: 3 passed — encrypt_local+upload_via_ec2로 교체, healthz https://IP:8443/healthz mTLS로 변경, 테스트 fixtures에 dummy cert 추가.
- [x] **E3**: `scripts/deploy_certs_to_ec2.sh`의 SSM 흐름은 "최초 부트스트랩"으로 한정. 부트스트랩 이후 cert rotate는 `upload_proxy`의 `/cert_rotate` 엔드포인트(D1에 추가)를 사용하도록 README 갱신.
  - `verify`: README diff 확인 + script가 한 번만 호출되는지 unit 검증 불가 → 수동 확인 체크박스로 대체.
  - 결과: 스크립트 헤더에 BOOTSTRAP ONLY 명시 + /cert_rotate curl 예시 추가. syntax OK.

### Phase F — 인프라 단절 지점

- [ ] **F1**: `infra/ec2.tf`에 `aws_eip` 2개 + `aws_eip_association` 2개 추가(app/mcp). `output "app_public_ip"`가 EIP를 반환하도록 변경.
  - `verify`: `terraform plan` 통과 + plan 출력에 `aws_eip` 자원 2개 등장.
- [ ] **F2**: `infra/ec2.tf` app-sg ingress 50051을 endpoint_cidr 외에 EC2 자체 SG (self) 도 허용(향후 sidecar 가능성). 또한 50051의 description을 "gRPC mTLS only — no insecure fallback"로 갱신.
  - `verify`: `terraform plan -detailed-exitcode` 통과.
- [ ] **F3**: `agentbox doctor`에 D10 추가: client cert 만료까지 ≤ 7일이면 자동 갱신 권고(`agentbox set -y --regen-certs` 안내).
  - `verify`: `pytest tests/unit/test_doctor_cmd.py -q` 통과 + D10 케이스 unit test 추가.

### Phase G — 테스트 자동화

- [ ] **G1**: `tests/integration/test_full_path_localmock.py` 신설. 로컬 grpcio mTLS server + uvicorn upload_proxy를 fixture로 띄우고, 클라이언트 mitmproxy addon이 `api.anthropic.com` 요청 → gRPC inspect → ALLOW/BLOCK 응답 → upload 흐름까지 검증.
  - `verify`: `pytest tests/integration/test_full_path_localmock.py -q` 통과.
- [ ] **G2**: `tests/terraform/test_plan.py` 신설(이미 `tests/terraform/` 존재). `subprocess.run(["terraform", "-chdir=infra", "plan", "-detailed-exitcode"])` 호출 + 새 자원(`aws_eip`, ingress 8443) 존재 검증.
  - `verify`: `pytest tests/terraform/test_plan.py -q` 통과.
- [ ] **G3**: `pytest.ini` 또는 `pyproject.toml`에 `markers = ["tf_plan: requires terraform CLI"]` 추가 + `pytest -m "not tf_plan"`이 기본값이 되도록 설정.
  - `verify`: `pytest -q` (기본) 와 `pytest -q -m tf_plan` (terraform 포함) 둘 다 통과.

## Test Plan

### Unit 입출력 표

| 함수 | 입력 | 기대 출력 |
|---|---|---|
| `ensure_ca(empty_dir)` | 빈 디렉터리 | `agentbox-ca.crt/key` 생성, `mitmproxy-ca.pem`은 key+crt 결합본, 셋의 cert 본문 SHA256 동일 |
| `gen_mtls_certs(dir, ips=["1.2.3.4"])` | CA 존재 | `endpoint.crt`+`ec2.crt` 생성, `ec2.crt` SAN에 `1.2.3.4` 포함 |
| `apply_redirect(8080, ["api.anthropic.com"])` | mock subprocess | `iptables -t nat -A OUTPUT ... --string api.anthropic.com --to-ports 8080` 호출 확인 |
| `clear_redirect(8080)` | 위 규칙 존재 | `-D` 명령 호출 확인 |
| `upload_proxy POST /upload` | 멀티파트 zip | 200 + `{project_id, files: N}` 응답 |
| `grpc client._make_channel()` (cert 누락) | env var 비움 | `ValueError("gRPC cert missing")` raise |
| `grpc server.serve()` (cert 누락) | `/opt/agentbox/certs/grpc` 비움 | `RuntimeError("server cert missing")` raise |
| `doctor D10` | endpoint.crt 만료까지 3일 | status=FAIL, 안내 메시지에 `agentbox set --regen-certs` 포함 |

### Integration 시나리오

| 시나리오 | 종단 동작 |
|---|---|
| 로컬 모의 풀 패스 (G1) | mitmproxy ↑ → 로컬 grpcio server ↑ → uvicorn upload_proxy ↑ → 클라이언트가 fake `api.anthropic.com`(테스트 fixture로 stub) 요청 → addon이 gRPC inspect → ALLOW → 응답 그대로 통과. BLOCK 시 403 응답. upload_proxy `/upload`로 더미 zip 업로드 200 |
| Terraform plan (G2) | `terraform -chdir=infra plan -detailed-exitcode` exitcode in {0,2}; plan 텍스트에 `aws_eip` 2개 + ingress 8443 등장 |
| iptables 우회 차단 | `HTTPS_PROXY` 미설정 상태에서 `agentbox on` 후 `curl -k https://api.anthropic.com` 시 127.0.0.1:8080으로 라우팅 확인(WSL 수동 검증) |

### 실행 명령

```bash
# 기본 단위 + 로컬 통합 (CI 기본값)
pytest -q

# Terraform plan 포함 (terraform CLI 필요)
pytest -q -m tf_plan

# 전체
pytest -q -m "tf_plan or not tf_plan"
```

## Resume Protocol

세션이 끊겨도 다음 절차로 재개 가능:

1. `Tasks.md`를 열어 **마지막으로 `[x]`로 체크된 todo**를 찾는다.
2. `git log --oneline -20`으로 최근 커밋이 어느 todo에 대응하는지 확인 (커밋 메시지는 `feat(taskA1): ...` 형식 권장).
3. `pytest -q` 실행. 실패하는 테스트가 있다면 가장 최근 todo부터 다시 검토.
4. `cd infra && terraform plan -detailed-exitcode` 실행. exitcode가 1(에러)이면 Phase D/F 변경 중 무결성 깨짐 → 해당 todo로 복귀.
5. 진행 중이던 다음 todo의 `verify` 명령을 수동 실행해 현 상태를 확인한 뒤 작업 재개.
6. 새 todo 시작 시 todo 라인 앞에 `🚧` 표시(WIP), 완료 시 `[x]`로 변경.

### 코드 미수정 약속

이 문서는 계획이며, 사용자가 명시적으로 "시작" 또는 "go"라고 말하기 전까지 어떤 소스 파일도 수정하지 않습니다.
