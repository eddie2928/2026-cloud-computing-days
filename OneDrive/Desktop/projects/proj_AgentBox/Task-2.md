# Task-2: AgentBox Full Phase 1 + Phase 2 Build

> 본 문서는 Task-1(로컬 HITL 샌드박스 MVP)을 기반으로 **Phase 1 전체(eBPF/iptables Transparent Proxy + EC2 Data Plane + SOPS Zero-Knowledge)** 와 **Phase 2(Lambda MCP 브릿지 + Bedrock Agent 자동 판정 + SaaS 대시보드)** 를 구현하는 작업 계획이다.
> 피드백 반영: 2026-05-07. 이전 버전 대비 Zero-Knowledge 재설계, 로컬 웹서버 제거, Bedrock MCP 아키텍처 신규 도입.
> 인코딩: UTF-8 (BOM 없음)

---

## 0. 메타 정보

| 항목 | 값 |
|---|---|
| Task ID | Task-2 |
| 선행 조건 | Task-1 체크리스트 전체 `[x]` 완료 |
| 핵심 변경 | ① 로컬 HITL 웹서버 제거 → Bedrock 자동 판정, ② SOPS+KMS 코드 암호화, ③ Lambda MCP 브릿지 신설, ④ SaaS 대시보드를 EC2로 이동 |
| 대상 OS | Endpoint: WSL2 Ubuntu 22.04 / Server: AWS EC2 Ubuntu 22.04 |
| 언어 | Python 3.11+ (Endpoint addon, EC2 gRPC/MCP/SaaS), TypeScript+React (대시보드) |
| 인프라 | **Terraform** (모든 AWS 리소스 IaC). `terraform apply`는 사용자가 직접 실행 |
| 코드 수정 금지 | 사용자가 명시적으로 "Task-2 시작" 지시 전까지 본 문서 외 수정 금지 |

---

## 1. 목표

1. **투명한 트래픽 통제** — eBPF/iptables로 AI 도구(Claude Code) 443 트래픽만 mitmproxy로 강제 라우팅. `HTTPS_PROXY` 환경변수 의존 제거.
2. **Zero-Knowledge 코드 유출 방지** — 기업 코드는 SOPS+KMS로 암호화된 채 S3에 보관. 검사 시점에만 EC2 MCP Server가 임시 복호화 → Bedrock-only 접근 가능 KB 버킷에 저장 → 검사 완료 후 즉시 삭제.
3. **Bedrock 자동 판정** — 기존 HITL(사람이 허용/차단) 완전 대체. Bedrock Agent가 코드 유출·기밀값 유출 등 복수 사유로 자동 BLOCK/ALLOW 결정.
4. **중앙화된 가시성 (EC2 SaaS)** — EC2에서 SaaS 대시보드 제공: 파이프라인 현황, Bedrock 시스템 프롬프트 편집, KB 보존 기간 설정, 감사 로그 조회.

---

## 2. 아키텍처

```
+-------------------------------------+      +-----------------------------------------------+
| Endpoint (WSL2 / Linux VM)          |      | AWS Cloud                                     |
|                                     |      |                                               |
|  [SOPS 초기 설정 - 1회성]            |      |  S3: s3://{project}-encrypted-code/           |
|  $ sops --encrypt ./project/ ─────────────►|  (SOPS+KMS 암호화 파일 원본 보관)              |
|                                     |      |                                               |
|  Claude Code (Node.js)              |      |  +-----------------------------------------+  |
|     | HTTPS_PROXY=:8080             |      |  | EC2 (t3.micro 이상)                      |  |
|     v (eBPF/iptables 443->8080)     |      |  |                                         |  |
|  mitmproxy :8080                    |      |  |  [agentbox-grpc :50051]                 |  |
|  AgentBoxAddon (HITL 제거됨)        |      |  |   (1) prompt + user_id 수신              |  |
|  - TLS 오프로딩                      | gRPC |  |   (2) regex 1차 필터 (즉시 BLOCK 가능)  |  |
|  - prompt 추출                       |────► |  |   (3) Bedrock Agent InvokeAgent 호출    |  |
|  - verdict 수신 -> auto block/allow | <─── |  |   (4) verdict + reasons 반환            |  |
|                                     |      |  |                                         |  |
|  (로컬 FastAPI 웹서버 없음)           |      |  |  [agentbox-mcp :8443]                   |  |
|                                     |      |  |   Lambda 호출 수신                       |  |
+-------------------------------------+      |  |   KMS decrypt -> KB 버킷 저장           |  |
                                             |  |   검사 완료 후 KB 버킷 객체 삭제         |  |
                                             |  |                                         |  |
                                             |  |  [agentbox-saas :8000 (FastAPI+React)]  |  |
                                             |  |   파이프라인 현황 WebSocket 스트림       |  |
                                             |  |   Bedrock 시스템 프롬프트 편집           |  |
                                             |  |   KB 보존 기간 설정                      |  |
                                             |  |   감사 로그 조회/CSV export              |  |
                                             |  +-----------------------------------------+  |
                                             |                                               |
                                             |  Lambda: MCP 브릿지 (Bedrock Action Group)    |
                                             |   Bedrock -> Lambda 호출 (Action Group)        |
                                             |   Lambda -> EC2 MCP Server HTTP POST 호출      |
                                             |                                               |
                                             |  Bedrock Agent                                |
                                             |   system prompt: 코드 유출 탐지기             |
                                             |   Action Group: Lambda MCP 브릿지             |
                                             |   verdict + reasons JSON 반환                 |
                                             |   (내부 코드 유출 | 내부 기밀값 유출 | ...)   |
                                             |                                               |
                                             |  KMS CMK: SOPS 암호화/복호화 전용            |
                                             |  S3 KB 버킷: Bedrock Agent IAM Role만 접근   |
                                             |  DynamoDB: 이벤트 감사 로그                  |
                                             +-----------------------------------------------+
                                                      | (verdict == ALLOW)
                                                      v
                                             +---------------------------+
                                             | Anthropic API             |
                                             +---------------------------+
```

### 검사 1회 라이프사이클

| 단계 | 주체 | 동작 |
|---|---|---|
| (1) | mitmproxy addon | Claude Code 요청 인터셉트, prompt 추출 |
| (2) | gRPC 클라이언트 | EC2 `InspectRequest{prompt, user_id}` 전송 (timeout 5s) |
| (3) | EC2 gRPC 서버 | regex 1차 필터 -> Bedrock `InvokeAgent(prompt)` 호출 |
| (4) | Bedrock Agent | Action Group Lambda 호출: "회사 코드를 제공하라" |
| (5) | Lambda MCP 브릿지 | EC2 MCP Server `POST /mcp/decrypt_and_stage` 호출 |
| (6) | EC2 MCP Server | S3 encrypted-code -> KMS decrypt -> KB 버킷 업로드 |
| (7) | Bedrock Agent | KB 버킷 내용과 prompt 비교 -> verdict + reasons JSON 반환 |
| (8) | EC2 MCP Server | KB 버킷 객체 삭제 (즉시 또는 TTL 5분) |
| (9) | EC2 gRPC 서버 | `InspectResponse{verdict, reasons, event_id}` 반환 |
| (10) | mitmproxy addon | BLOCK -> 403 반환 / ALLOW -> upstream forward |

---

## 3. AWS 비용 분석 - Capex vs Opex

> **Capex성(고정비)** - 사용량과 무관하게 매월 일정하게 발생.
> **Opex(변동비)** - 실제 사용량에 따라 과금.

| 서비스 | 유형 | 추정 월 비용 (PoC) | 비고 |
|---|---|---|---|
| EC2 t3.micro on-demand (24/7) | **Capex성** | ~$8.35 | 항상 실행 시 고정비에 가까움 |
| KMS CMK | **Capex성** | $1/키 | 키당 고정 월정액 |
| NAT Gateway (EC2->외부) | **Capex성** | ~$32 | EC2 VPC 내에서 Bedrock/S3 호출 시 필요. Bedrock VPC Endpoint($7.2/AZ) 대안 고려 가능 |
| Lambda | Opex | ~$0 (PoC 수준) | 100만 req/월 무료 티어 |
| S3 (encrypted-code 버킷) | Opex | 저장 GB당 $0.023 + 요청비 | |
| S3 (KB 버킷) | Opex | 미미함 | 객체 즉시 삭제 정책 |
| Bedrock (Claude Haiku) | Opex | 토큰당 과금 | 월 예산 cap 필수 |
| DynamoDB | Opex | on-demand 요청당 과금 | |

> 주의: **PoC 월 고정비 합산**: EC2 $8.35 + KMS $1 + NAT Gateway $32 = 약 **$41/월**
> NAT Gateway 대신 Bedrock/S3 VPC Endpoint 사용 시 $32 절감 가능 (설정 복잡도 증가). 사용자 결정 필요 (R5 참조).

---

## 4. 하위 작업 (Phase별 세부 계획)

### Phase 1A: Endpoint - eBPF/iptables Transparent Interception

**선행:** Task-1 mitmproxy addon, custom CA 인프라.
**핵심 변경:** 로컬 FastAPI 웹서버 제거. Addon이 HITL Future 없이 바로 EC2 gRPC로 위임.

- [ ] **1A-1.** Ubuntu 22.04 VM 부트스트랩 (Multipass 또는 Vagrant)
  - 완료 조건: `uname -r` >= 5.15, `bpftool feature` 정상 출력
- [ ] **1A-2.** eBPF 도구 설치: `linux-headers-$(uname -r)`, `bpfcc-tools`, `clang >=14`, `libbpf-dev`, `python3-bpfcc`
  - 완료 조건: `python3 -c "from bcc import BPF"` 무에러
- [ ] **1A-3.** **(기본) iptables OUTPUT REDIRECT:** uid 기반 443->8080 REDIRECT + mitmproxy `mode: transparent`
  ```sh
  iptables -t nat -A OUTPUT -p tcp --dport 443 -m owner --uid-owner $(id -u) -j REDIRECT --to-port 8080
  ```
- [ ] **1A-4.** **(선택 강화) BCC cgroup_skb:** AI 도구 프로세스 cgroup v2 격리 + dst_port=443 패킷 mark
  - 결정: **1A-3 iptables를 먼저 구현, 1A-4는 선택적 추가.**
- [ ] **1A-5.** SNI 분기: mitmproxy `--allow-hosts "api\.anthropic\.com"` - 비대상 트래픽 pass-through
- [ ] **1A-6.** 통합 테스트: `curl https://api.anthropic.com/healthcheck` (HTTPS_PROXY 미설정) -> mitmproxy access log 노출 확인
- [ ] **1A-7.** 일반 트래픽 비간섭: `curl https://www.google.com` -> mitmproxy log 미노출
- [ ] **1A-8.** eBPF stats 로깅: 마킹/드롭 카운터 5초 주기로 `logs/ebpf-stats.log` export

**Phase 1A Gate:** HTTPS_PROXY 미설정 + Claude Code 실행 -> mitmproxy에 정상 노출. 일반 트래픽 영향 없음.

---

### Phase 1B: Endpoint - gRPC 클라이언트 (EC2 연결)

**핵심 변경:** addon 내부에서 `HITLQueue.wait()` 제거 -> `gRPC_client.Inspect()` 자동 호출.

- [ ] **1B-1.** `proto/inspect.proto` 정의:
  ```protobuf
  syntax = "proto3";
  service Inspector {
    rpc Inspect(InspectRequest) returns (InspectResponse);
  }
  message InspectRequest {
    string user_id = 1;
    string prompt  = 2;
    string model   = 3;
  }
  message InspectResponse {
    string verdict          = 1;  // "ALLOW" | "BLOCK"
    repeated string reasons = 2;  // ["내부 코드 유출 탐지", "내부 기밀값 유출 탐지", ...]
    string event_id         = 3;
  }
  ```
- [ ] **1B-2.** Endpoint gRPC 클라이언트: `grpcio` + stub, connection pool (최대 5 connections)
- [ ] **1B-3.** mTLS: self-signed 사내 CA (PoC). `cryptography` 라이브러리로 `agentbox-ca.crt`, `endpoint.crt`, `ec2.crt` 생성. Addon이 EC2 cert pin 검증.
- [ ] **1B-4.** Addon 수정 (`src/agentbox/proxy/addon.py`):
  - `HITLQueue.wait()` 코드 제거 (로컬 HITL 완전 제거)
  - `grpc_stub.Inspect(InspectRequest(prompt=..., user_id=...), timeout=5)` 호출
  - `grpc.RpcError` 또는 timeout -> 안전 차단 (`BLOCK`, status="failed")
- [ ] **1B-5.** 단위 테스트: `grpc.testing` stub + mock 서버로 Inspect RPC round-trip
- [ ] **1B-6.** 통합 테스트: Endpoint addon -> 로컬 mock EC2 gRPC 서버 -> verdict round-trip

**Phase 1B Gate:** Addon이 동기적으로 verdict 수신 후 forward/block. mTLS 핸드쉐이크 검증.

---

### Phase 1C: EC2 Data Plane - gRPC 서버 + MCP 서버 + SaaS 기본

> **실 AWS EC2 t3.micro 배포.** `infra/` 디렉터리 Terraform으로 관리. `terraform apply`는 사용자 직접 실행.

- [ ] **1C-1.** Terraform `infra/ec2.tf`:
  - EC2 인스턴스 (AMI: Ubuntu 22.04 LTS, t3.micro), Elastic IP
  - 보안 그룹 inbound: TCP 50051 (gRPC/mTLS, Endpoint IP 한정), TCP 8443 (MCP, Lambda IP 한정), TCP 8000 (SaaS, 관리자 IP 한정)
  - IAM 역할: `kms:Decrypt`, `s3:GetObject` (encrypted-code), `s3:PutObject`+`s3:DeleteObject` (kb-staging), `bedrock:InvokeAgent`, `dynamodb:PutItem`+`dynamodb:Query`
- [ ] **1C-2.** systemd 서비스 3종: `/etc/systemd/system/agentbox-grpc.service`, `agentbox-mcp.service`, `agentbox-saas.service`
- [ ] **1C-3.** gRPC 서버 (`agentbox-grpc`, Python `grpc.aio`):
  - `Inspect(InspectRequest)` 핸들러:
    1. Pydantic 룰셋(`rules.yaml`) regex 1차 필터 - 패턴 매칭 시 즉시 `BLOCK` (Bedrock 호출 생략, 저지연)
    2. `boto3.client('bedrock-agent-runtime').invoke_agent(...)` 호출
    3. 스트리밍 청크 수집 -> 전체 텍스트에서 `json.loads()` -> `verdict`, `reasons` 추출
    4. DynamoDB `events` 테이블 기록 후 `InspectResponse` 반환
- [ ] **1C-4.** MCP 서버 (`agentbox-mcp`, FastAPI HTTPS :8443):
  - `POST /mcp/decrypt_and_stage`:
    - Body: `{"project_id": str, "session_id": str}`
    - 동작: S3 encrypted-code 다운로드 -> `sops --decrypt` (subprocess, bytearray 버퍼) -> KB 버킷 `/staging/{session_id}/` 업로드
    - 응답: `{"kb_bucket": str, "prefix": str}`
  - `DELETE /mcp/cleanup/{session_id}`: KB 버킷 prefix 하위 객체 전체 삭제
  - 업로드 완료 후 bytearray zero-fill: `buf[:] = b'\x00' * len(buf)`
- [ ] **1C-5.** SaaS 대시보드 기본 API (`agentbox-saas`, FastAPI :8000):
  - `GET /` -> Jinja2 index.html (React 번들 서빙)
  - `WebSocket /pipeline/stream` -> DynamoDB Streams 실시간 relay
  - `GET /audit?from=&to=&verdict=` -> DynamoDB 조회
  - `PUT /settings/prompt` -> Bedrock Agent System Prompt 업데이트 (DynamoDB `settings` 테이블 저장)
  - `PUT /settings/kb-ttl` -> KB 버킷 객체 TTL(분) 업데이트
- [ ] **1C-6.** DynamoDB `events` 테이블:
  - PK: `event_id` (uuid4), SK: `ts` (ISO8601 UTC)
  - 속성: `user_id`, `prompt_hash` (SHA256), `verdict`, `reasons_json`, `matched_rules`, `latency_ms`
  - GSI: `user_id-ts-index` (사용자별 이벤트 조회)
- [ ] **1C-7.** 단위 테스트: regex 룰 엔진, MCP decrypt 로직 (mock KMS/S3), gRPC 핸들러 (botocore.stub)
- [ ] **1C-8.** 통합 테스트: gRPC `InspectRequest` (차단 패턴 포함) -> `verdict==BLOCK`, DynamoDB 기록 확인

**Phase 1C Gate:** EC2 gRPC endpoint mTLS 호출 -> 룰 매칭 응답 확인. DynamoDB 기록 확인.

---

### Phase 1D: SOPS 로컬 암호화 & S3 업로드 (Zero-Knowledge 기반 구축)

> 기업 소스코드를 **로컬에서 SOPS+KMS로 암호화**하여 S3에 업로드. EC2는 평문 코드를 장기 보관하지 않음.

- [ ] **1D-1.** Terraform `infra/kms.tf` + `infra/s3.tf`:
  - KMS CMK (별칭 `agentbox-sops-key`, 키 정책: 로컬 IAM User + EC2 IAM Role만 `kms:Decrypt`)
  - S3 버킷 `{project}-encrypted-code`: 버전 관리 활성화, SSE-KMS (CMK)
  - S3 버킷 `{project}-kb-staging`: SSE-KMS (CMK), 버킷 정책 - Bedrock Agent IAM Role만 `s3:GetObject` 허용
- [ ] **1D-2.** SOPS 설치 및 `.sops.yaml` 작성:
  ```yaml
  # .sops.yaml - 프로젝트 루트에 위치
  creation_rules:
    - path_regex: .*
      kms: "arn:aws:kms:{region}:{account_id}:key/{key_id}"
  ```
- [ ] **1D-3.** 암호화 및 업로드 스크립트 `scripts/encrypt_and_upload.sh`:
  ```sh
  #!/usr/bin/env bash
  set -e
  SRC_DIR="${1:?Usage: $0 <source_dir>}"
  ENC_DIR="./encrypted"
  S3_BUCKET="${PROJECT_S3_BUCKET:?set PROJECT_S3_BUCKET}"
  rm -rf "$ENC_DIR" && mkdir -p "$ENC_DIR"
  find "$SRC_DIR" -type f | while read -r f; do
    rel="${f#$SRC_DIR/}"
    mkdir -p "$ENC_DIR/$(dirname "$rel")"
    sops --encrypt "$f" > "$ENC_DIR/$rel.enc"
  done
  aws s3 sync "$ENC_DIR/" "s3://$S3_BUCKET/encrypted_code/" --delete
  echo "Upload complete."
  ```
  - 완료 조건: S3에 `.enc` 파일 존재. `cat .enc` -> 암호문 출력 (평문 불가)
- [ ] **1D-4.** IAM 확인: EC2 Role -> `kms:Decrypt` (CMK), `s3:GetObject` (encrypted-code), `s3:PutObject`+`s3:DeleteObject` (kb-staging) 만 부여
- [ ] **1D-5.** 보안 검증: EC2에서 `aws s3 cp s3://.../file.enc - | cat` -> 암호문 출력 (평문 불가 확인)
- [ ] **1D-6.** MCP Server decrypt 플로우 E2E 검증:
  1. S3 encrypted-code 파일 다운로드
  2. `sops --decrypt --output-type binary` (subprocess) -> `bytearray` 버퍼
  3. `bytearray` KB 버킷 `/staging/{session_id}/plaintext` 업로드
  4. 업로드 완료 후 `buf[:] = b'\x00' * len(buf)` (zero-fill)
  5. KB 버킷 객체 존재 확인 -> `DELETE /mcp/cleanup/{session_id}` -> 객체 삭제 확인

**Phase 1D Gate:** S3 SOPS 암호화 파일 존재. EC2 MCP 정상 복호화 후 KB 버킷 적재, 완료 후 삭제 확인.

---

### Phase 2A: Lambda MCP 브릿지 & Bedrock Agent 연동

- [ ] **2A-1.** Bedrock 모델 액세스 승인 (AWS Console -> Bedrock -> Model Access -> Anthropic Claude Haiku, us-east-1)
- [ ] **2A-2.** Terraform `infra/lambda.tf`: Lambda 함수 `agentbox-mcp-bridge`
  - 런타임: Python 3.11
  - 환경변수: `MCP_SERVER_URL`, `KB_STAGING_BUCKET`
  - IAM: Bedrock Agent가 `lambda:InvokeFunction` 권한 보유, Lambda에 `s3:GetObject` (kb-staging)
  - 핸들러 (Bedrock Action Group 이벤트 포맷):
    ```python
    import os, json
    import urllib.request

    def handler(event, ctx):
        params = {p['name']: p['value'] for p in event.get('parameters', [])}
        project_id = params.get('project_id', 'default')
        session_id = event.get('sessionId', 'unknown')
        mcp_url = os.environ['MCP_SERVER_URL']
        body = json.dumps({"project_id": project_id, "session_id": session_id}).encode()
        req = urllib.request.Request(f"{mcp_url}/mcp/decrypt_and_stage",
                                     data=body, method='POST',
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return {
            "response": {
                "actionGroup": event['actionGroup'],
                "function": event['function'],
                "functionResponse": {
                    "responseBody": {"TEXT": {"body": json.dumps(data)}}
                }
            }
        }
    ```
- [ ] **2A-3.** Terraform `infra/bedrock.tf`: Bedrock Agent `agentbox-inspector`
  - 기반 모델: `anthropic.claude-haiku-20240307-v1:0`
  - 시스템 프롬프트 (초안, 대시보드에서 수정 가능):
    ```
    You are a security inspector for a software company.
    Given a developer's prompt, determine if it contains:
    1. Proprietary source code (functions, classes, algorithms) from the company
    2. Internal secret values (API keys, credentials, tokens, passwords)
    3. Other confidential internal information
    Use the company code retrieved via the decrypt_and_stage tool as reference.
    Return ONLY this JSON (no other text):
    {"verdict": "BLOCK" or "ALLOW", "reasons": ["reason1", "reason2"]}
    Do NOT echo or repeat the company code. If no violation: {"verdict": "ALLOW", "reasons": []}
    ```
  - Action Group: `agentbox-mcp-bridge` Lambda 연결
    - Function 스펙: `decrypt_and_stage(project_id: string) -> {kb_bucket: string, prefix: string}`
  - Knowledge Base: kb-staging 버킷 연결 (동적 접근, 검사당 갱신)
- [ ] **2A-4.** EC2 gRPC 서버 `InvokeAgent` 통합:
  - `boto3.client('bedrock-agent-runtime').invoke_agent(agentId=..., sessionId=event_id, inputText=prompt)` 호출
  - 스트리밍 청크 수집 -> 전체 텍스트 `json.loads()` -> `verdict`, `reasons` 추출
  - JSON 파싱 실패 시 -> regex 룰셋 fallback (1C-3 룰셋 재사용)
  - 검사 완료 후 `DELETE /mcp/cleanup/{event_id}` 호출 (KB 버킷 정리)
- [ ] **2A-5.** Bedrock 장애 시 의미론적 fallback:
  - EC2에 `sentence-transformers/all-MiniLM-L6-v2` 로컬 실행
  - 복호화 코드 임베딩 vs prompt 임베딩, cosine similarity >= 0.85 시 BLOCK
- [ ] **2A-6.** 비용 가드 (env-driven):
  - `BEDROCK_MAX_TOKENS_PER_DAY=100000` - DynamoDB daily counter로 추적, 초과 시 regex-only 모드
  - `PROMPT_MAX_CHARS=8000` - 초과 시 BLOCK (reason: "프롬프트 길이 제한 초과")
- [ ] **2A-7.** KB sync 지연 측정 및 방식 결정:
  - Bedrock KB가 새 S3 객체 반영에 수초 이상 소요 시 -> 직접 컨텍스트 주입 전환:
    Lambda 응답에 복호화 코드 텍스트를 직접 포함 -> Bedrock 프롬프트 컨텍스트로 삽입
  - p95 >= 500ms이면 직접 주입 방식으로 전환, Task-2.md §6 R4 업데이트
- [ ] **2A-8.** 단위 테스트: `botocore.stub`으로 Bedrock `invoke_agent`, KMS `decrypt`, S3 응답 mock
- [ ] **2A-9.** 통합 테스트 (실 Bedrock Haiku):
  - 알려진 leak 시나리오 (샘플 함수를 그대로 prompt에 포함) -> `verdict == BLOCK`
  - 무관 prompt ("파이썬 정렬 알고리즘 설명해줘") -> `verdict == ALLOW`
  - p50/p95 지연 측정 기록

**Phase 2A Gate:** 알려진 코드 leak -> BLOCK. 무관 prompt -> ALLOW. p95 < 500ms.

---

### Phase 2B: SaaS 대시보드 고도화

> Phase 1C에서 기본 FastAPI API를 구축한 뒤, 본 Phase에서 React UI + 완성된 API를 추가한다.

- [ ] **2B-1.** Vite + React 18 + TypeScript 스캐폴드 - `dashboard/` 디렉터리
- [ ] **2B-2.** 인증: 단일 admin 토큰 (`X-Admin-Token` 헤더, env-driven)
- [ ] **2B-3.** 화면 4개:
  - **Pipeline Stream**: WebSocket `/pipeline/stream` 실시간 이벤트 (verdict, reasons, user_id, ts, latency_ms)
  - **Prompt Editor**: Bedrock 시스템 프롬프트 편집 + `PUT /settings/prompt` 저장
  - **KB Settings**: KB 버킷 객체 TTL(분) 조회/수정 + `PUT /settings/kb-ttl` 저장
  - **Audit**: `GET /audit` DynamoDB 조회, 날짜 범위/verdict 필터, CSV export
- [ ] **2B-4.** Playwright E2E (`tests/e2e/`): 화면별 주요 시나리오 1개씩 (총 4케이스)
- [ ] **2B-5.** Lighthouse (EC2 SaaS URL 기준): Performance >= 80, Accessibility >= 90

**Phase 2B Gate:** dev VM -> Claude Code -> eBPF -> mitmproxy -> EC2 Bedrock 검사 -> 대시보드 실시간 표시.

---

### Phase 2C: 로깅 & 모니터링

- [ ] **2C-1.** CloudWatch Logs: EC2 systemd 3종 로그 -> Log Group `/agentbox/ec2`
- [ ] **2C-2.** CloudWatch Metrics: DynamoDB Streams -> Lambda -> Custom Metric (`BlockRate`, `EventCount`)
- [ ] **2C-3.** SNS 알람: `BlockRate > 10%` (10분 평균) 또는 `ErrorRate > 5%` -> 이메일 알림
- [ ] **2C-4.** 보존 정책: CloudWatch Logs 90일, DynamoDB `events` TTL 365일

---

## 5. 비기능 요구사항

| 영역 | 목표 |
|---|---|
| 지연 (Endpoint->Verdict) | p50 < 200ms, p95 < 500ms (Bedrock + MCP 포함) |
| 가용성 | EC2 단일 인스턴스 PoC; timeout/오류 -> mitmproxy BLOCK (안전 차단) |
| 보안 | KMS CMK, SOPS 로컬 암호화, mTLS gRPC, IAM 최소 권한, KB 버킷 Bedrock-only, 즉시 삭제 |
| 관측성 | DynamoDB 이벤트 로그, CloudWatch 메트릭, SaaS 실시간 WebSocket 스트림 |
| 비용 | Bedrock 일일 토큰 cap, Capex성 합계 <= $50/월 (PoC 기준) |

---

## 6. 리스크 및 결정 보류 항목

| ID | 항목 | 필요 결정 |
|---|---|---|
| R1 | AWS 계정/예산 | IAM credential 제공 + 월 예산 cap 합의 (Capex ~$41 + Opex 상한) |
| R2 | mTLS 인증서 | Self-signed PoC vs 사내 CA 발급 |
| R3 | Bedrock 모델 액세스 | us-east-1 Claude Haiku 가용성 확인 |
| R4 | KB sync 지연 | Bedrock KB sync가 p95 > 500ms이면 직접 컨텍스트 주입 방식으로 전환 (2A-7) |
| R5 | NAT Gateway 비용 | $32/월 vs Bedrock/S3 VPC Endpoint $7.2/AZ - 설정 복잡도와 비용 절감 트레이드오프 |
| R6 | SOPS 초기 설정 | 개발자 로컬에 KMS 접근 IAM 권한 배포 방식 (AWS SSO vs static credentials) |
| R7 | Lambda cold start | MCP 브릿지 첫 호출 수초 지연. Provisioned Concurrency 필요 여부 (추가 비용) |
| R8 | eBPF 권한 | dev VM에서 `CAP_BPF` 또는 `CAP_SYS_ADMIN` 필요 범위 협의 |

---

## 7. 테스트 전략

| 레벨 | 도구 | 대상 |
|---|---|---|
| Unit | pytest | gRPC 핸들러, MCP decrypt 로직, regex 룰 엔진, Bedrock 클라이언트 어댑터 |
| Integration | pytest + LocalStack (KMS/S3/DynamoDB) + botocore.stub (Bedrock) | Validation 파이프라인 전체 |
| Contract | grpcio test + protobuf round-trip | gRPC schema 호환성 |
| E2E | Playwright | SaaS 대시보드 4개 화면 |
| Security | auditd, bandit, pip-audit | KB 버킷 즉시 삭제 검증, 알려진 취약점 |
| Load | locust | gRPC 100 req/min (PoC) |

---

## 8. TODO 마스터 체크리스트

### Phase 1A - eBPF/iptables
- [x] 1A-1 VM 부트스트랩
- [x] 1A-2 eBPF 도구 설치
- [ ] 1A-3 BCC cgroup_skb (선택)
- [x] 1A-4 iptables REDIRECT (기본)
- [x] 1A-5 SNI 분기
- [x] 1A-6 transparent 통합 테스트
- [x] 1A-7 일반 트래픽 비간섭
- [x] 1A-8 eBPF stats 로깅

### Phase 1B - gRPC 클라이언트
- [x] 1B-1 proto 정의
- [x] 1B-2 gRPC 클라이언트
- [x] 1B-3 mTLS 인증서
- [x] 1B-4 Addon 수정 (HITL 제거)
- [x] 1B-5 단위 테스트
- [x] 1B-6 통합 테스트

### Phase 1C - EC2 서버 3종
- [x] 1C-1 Terraform EC2+보안그룹+IAM
- [x] 1C-2 systemd 서비스 3개
- [x] 1C-3 gRPC 서버 (regex+Bedrock)
- [x] 1C-4 MCP 서버 (decrypt_and_stage + cleanup)
- [x] 1C-5 SaaS 기본 API
- [x] 1C-6 DynamoDB 테이블+GSI
- [x] 1C-7 단위 테스트
- [x] 1C-8 통합 테스트

### Phase 1D - SOPS 암호화
- [x] 1D-1 Terraform KMS + S3 (2버킷)
- [x] 1D-2 SOPS 설치 + .sops.yaml
- [x] 1D-3 encrypt_and_upload.sh
- [x] 1D-4 IAM 최소 권한 확인
- [ ] 1D-5 보안 검증 (평문 불가) - EC2 배포 후 검증 필요
- [ ] 1D-6 MCP decrypt 플로우 E2E 검증 - EC2 배포 후 검증 필요

### Phase 2A - Lambda MCP + Bedrock
- [ ] 2A-1 Bedrock 모델 액세스 - AWS Console 수동 승인 필요
- [x] 2A-2 Terraform Lambda MCP 브릿지
- [x] 2A-3 Terraform Bedrock Agent IAM (Agent 리소스는 모델 액세스 후 활성화)
- [x] 2A-4 InvokeAgent 통합 + KB 정리 (ec2/grpc_server/server.py)
- [x] 2A-5 의미론적 fallback (semantic_fallback.py)
- [x] 2A-6 비용 가드 (토큰 cap, 프롬프트 길이 제한)
- [ ] 2A-7 KB sync 지연 측정 - 실 Bedrock 배포 후 측정 필요
- [x] 2A-8 단위 테스트 (test_bedrock_client.py)
- [ ] 2A-9 통합 테스트 (실 Bedrock) - EC2 배포 후 실행 필요

### Phase 2B - SaaS 대시보드
- [x] 2B-1 Vite/React 스캐폴드
- [x] 2B-2 인증 (admin 토큰)
- [x] 2B-3 화면 4개 구현
- [x] 2B-4 Playwright E2E
- [ ] 2B-5 Lighthouse - EC2 배포 후 측정 필요

### Phase 2C - 로깅/모니터링
- [x] 2C-1 CloudWatch Logs (log groups + SSM agent config)
- [x] 2C-2 Custom Metrics (DynamoDB Streams -> Lambda -> BlockRate/EventCount)
- [x] 2C-3 SNS 알람 (BlockRate>10%, ErrorRate>5%)
- [x] 2C-4 보존 정책 (CloudWatch 90일, DynamoDB events TTL 365일)

---

## 9. 재개 프로토콜

1. §8의 가장 최근 미체크(`- [ ]`) 항목으로 이동.
2. 직전 Phase Gate 검증 재실행.
3. `git status`로 의도치 않은 변경 점검.
4. 각 Phase는 별도 PR/브랜치 권장.

---

## 10. 코드 수정 금지 - 시작 조건

- Task-2 모든 작업은 **Task-1 완료 + 본 문서 사용자 검토 + "Task-2 시작" 명시적 지시** 후에만 착수.
- `terraform apply`는 사용자가 직접 실행. Claude는 Terraform 코드 작성 후 apply 단계에서 멈춤.
- 각 Phase 시작 전 §6 R1~R8 중 해당 Phase 관련 리스크를 먼저 사용자와 협의한다.
