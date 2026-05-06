# Task-2: AgentBox Full Phase 1 + Phase 2 Build

> 본 문서는 `rough-plan.md`의 **Phase 1 전체(eBPF 후킹 + Transparent Proxy + TLS Offloading + EC2 Data Plane + Zero-Knowledge PoC)** 와 **Phase 2(Bedrock Agent 의미론적 비교 + SaaS 대시보드)** 를 모두 포함하는 후속 작업 계획이다.
> Task-1(`Task-1.md`)에서 검증한 로컬 샌드박스(HTTPS_PROXY 기반 + HITL UI)를 기반으로 확장한다.
> 인코딩: 본 문서 및 모든 산출물은 **UTF-8 (BOM 없음)** 으로 통일한다.

---

## 0. 메타 정보

| 항목 | 값 |
|---|---|
| Task ID | Task-2 |
| 선행 조건 | Task-1 모든 Phase Gate 통과 |
| 범위 | rough-plan.md Phase 1 전체 + Phase 2 전체 |
| 대상 OS | Endpoint: WSL2 → 별도 Ubuntu 22.04 VM (eBPF 검증) / Server: AWS EC2 (Ubuntu 22.04 또는 Amazon Linux 2023) |
| 언어 | Python 3.11+ (Endpoint, Server, 테스트), TypeScript+React (대시보드) |
| 인프라 | **실제 AWS 계정** (사용자가 자격증명 제공 필요): EC2, KMS, Bedrock, S3, DynamoDB 또는 OpenSearch |
| 코드 수정 금지 | Task-1 완료 후 사용자가 명시적으로 "Task-2 시작"이라고 지시하기 전까지 본 문서 외 수정 금지 |

---

## 1. 목표 (Objectives)

`rough-plan.md` §1과 일치:
1. **실시간 투명한 통제** — eBPF/iptables 기반 트래픽 후킹 + TLS Offloading
2. **Zero-Knowledge 코드 유출 방지** — KMS + In-memory 복호화 + 즉시 wipe
3. **중앙화된 가시성** — 프롬프트 로깅, Bedrock Agent 룰셋(RAG), SaaS 대시보드

---

## 2. 아키텍처 (rough-plan §3 구체화)

```
+-----------------------------+        +---------------------------------------+
| Endpoint (Linux dev VM)     |        | AWS Cloud (Company SaaS)              |
|                             |        |                                       |
|  Cursor / Claude Code       |        |  +--------------------------------+   |
|       |                     |        |  | EC2 (Data Plane + Control)     |   |
|       v eBPF/iptables       |        |  |                                |   |
|  Local Transparent Proxy    |        |  |  Validation Worker             |   |
|  - mitmproxy + custom addon |        |  |  - KMS decrypt (in-memory)     |   |
|  - dynamic leaf cert        |        |  |  - Bedrock Agent invoke        |   |
|       |                     |        |  |  - Secure wipe                 |   |
|       | gRPC/HTTP2 (mTLS)   | -----> |  |                                |   |
|       v                     |        |  |  Control Plane (FastAPI)       |   |
|                             |        |  |  - Rule Mgmt / RAG upload      |   |
|                             |        |  |  - Log query                   |   |
|                             |        |  |                                |   |
|                             |        |  |  Storage:                      |   |
|                             |        |  |   S3 (encrypted code, RAG)     |   |
|                             |        |  |   DynamoDB or OpenSearch (logs)|   |
|                             |        |  +--------------------------------+   |
|                             |        |                                       |
|                             |        |  Dashboard (React/Vite)               |
|                             |        |  - WebSocket logs / verdict UI        |
+-----------------------------+        +---------------------------------------+
                                                   |
                                                   v (if ALLOW)
                                       +---------------------------+
                                       | Anthropic / OpenAI APIs   |
                                       +---------------------------+
```

---

## 3. 하위 작업(Sub-task) 분할 — 각 Phase별 별도 PR/검증

### Phase 1A: Endpoint — eBPF/iptables Transparent Interception
**선행:** Task-1의 mitmproxy addon, custom CA, HITL 큐.
**목표:** HTTPS_PROXY 환경변수 의존 제거 → OS 레벨 강제 라우팅.

- [ ] **1A-1.** Ubuntu 22.04 VM(VirtualBox+Vagrant 또는 cloud-init Multipass) 부트스트랩 — 호스트 Windows에서 `vagrant up` 한 줄 기동
  - 검증: `uname -r`, `bpftool feature` 출력
- [ ] **1A-2.** eBPF 환경: `linux-headers`, `bpfcc-tools`, `clang/llvm`, `libbpf-dev`, `python3-bpfcc` 설치
  - 검증: `python3 -c "from bcc import BPF"` 무에러
- [ ] **1A-3.** **선택지 A (BCC + cgroup_skb):** AI 도구 프로세스(Cursor / Claude Code)를 cgroup에 격리, cgroup_skb 프로그램으로 dst_port=443 + dst_ip ∈ {Anthropic IP set} 패킷을 mark
- [ ] **1A-4.** **선택지 B (iptables OUTPUT REDIRECT):** uid/gid 기반 또는 cgroup match로 443→8080 리다이렉트. mitmproxy `mode: transparent` 옵션 활성
- [ ] **1A-5.** Anthropic IP/SNI 식별 — eBPF는 L4까지만, SNI 기반 식별은 mitmproxy의 `--allow-hosts` 정규식으로 보강. 결정: **eBPF는 모든 443 트래픽을 mitmproxy로 라우팅, mitmproxy가 SNI로 통과/검사 분기.**
- [ ] **1A-6.** 자동 테스트: `pytest tests/integration/test_transparent.py` — VM 내부에서 `curl https://api.anthropic.com/healthcheck` 가 mitmproxy를 거치는지 확인 (HTTPS_PROXY 미설정)
- [ ] **1A-7.** 일반 트래픽 비간섭 검증: `curl https://www.google.com` 의 mitmproxy log 부재 확인
- [ ] **1A-8.** **로깅**(CLAUDE.md §5): eBPF 프로그램이 생성한 마킹·드롭 카운터를 5초 주기로 `logs/ebpf-stats.log`로 export

**Phase 1A Gate:** HTTPS_PROXY 미설정 + Claude Code 실행 → mitmproxy/UI에 정상 노출. 일반 트래픽은 영향 없음.

---

### Phase 1B: Endpoint — gRPC/HTTP2 Egress to EC2
- [ ] **1B-1.** `proto/inspect.proto` 정의: `InspectRequest{user_id, prompt, context_metadata}` / `InspectResponse{verdict, reason, event_id}`
- [ ] **1B-2.** Endpoint 측 gRPC 클라이언트 구현 (`grpcio` + connection pooling)
- [ ] **1B-3.** mTLS — Endpoint cert는 사내 PKI에서 발급(Task-2 범위에서는 self-signed로 PoC), EC2 측 cert pinning
- [ ] **1B-4.** Endpoint에서 verdict 수신까지 hang 가능 — timeout 5s 기본, 실패 시 안전 측 차단(close-on-fail)
- [ ] **1B-5.** 단위 테스트: gRPC 스텁 + mock 서버
- [ ] **1B-6.** 통합 테스트: Endpoint addon → 로컬 EC2 시뮬레이터 → verdict round-trip

**Phase 1B Gate:** addon이 verdict를 동기적으로 받아 forward/block 결정. mTLS 핸드쉐이크 검증.

---

### Phase 1C: EC2 Data Plane — gRPC 서버 + 정규식 차단

> 본 Phase는 LocalStack 없이 **실제 AWS EC2 t3.micro** 에 배포. AWS 자격증명·VPC·보안그룹은 사용자 협의 필요(R1 참조).

- [ ] **1C-1.** EC2 인스턴스 프로비저닝 — Terraform 또는 AWS CDK (Python). `infra/` 디렉터리.
- [ ] **1C-2.** systemd service로 gRPC 서버(`agentbox-server`) 기동
- [ ] **1C-3.** Pydantic 룰셋 (`rules.yaml`): regex 패턴 + severity + action(block/log)
- [ ] **1C-4.** 단위 테스트: `tests/unit/test_rule_engine.py` — 패턴 매칭, 우선순위, action 합성
- [ ] **1C-5.** 통합 테스트: gRPC InspectRequest → 차단된 패턴 포함 시 verdict=BLOCK
- [ ] **1C-6.** 로깅: 모든 요청을 `events` DynamoDB 테이블(또는 OpenSearch index) 에 기록 (`event_id`, `ts`, `user_id`, `prompt_hash`, `verdict`, `matched_rules`)

**Phase 1C Gate:** EC2 공인 endpoint(또는 VPN 내부)로 mTLS gRPC 호출, 룰 매칭 응답 확인.

---

### Phase 1D: Zero-Knowledge — KMS + In-memory Decryption PoC

- [ ] **1D-1.** AWS KMS Customer Managed Key 생성 — Terraform IaC
- [ ] **1D-2.** S3 버킷 + 객체 SSE-KMS 정책 — 사내 암호화 코드 업로드
- [ ] **1D-3.** EC2 IAM Role: `kms:Decrypt` + `s3:GetObject` 만 부여(최소 권한)
- [ ] **1D-4.** Validation Worker: 요청당 `decrypt → temporary buffer → AST/embedding 추출 → buffer wipe`
  - **Secure wipe**: Python `ctypes.memset(id(plaintext), 0, len(plaintext))` 는 CPython 내부 객체에 안전하지 않음. 대안: `bytearray` 사용 + 명시적 zero-fill, 또는 `cryptography.hazmat.primitives.ciphers` 의 `BufferedDecryptor` 컨텍스트로 한정
- [ ] **1D-5.** 디스크 비기록 검증: `auditd` 또는 `inotify`로 EC2 파일시스템 쓰기 감시 — 평문 코드 fingerprint(SHA256 of known string)가 디스크에 등장하지 않음
- [ ] **1D-6.** 통합 테스트: 암호화된 객체 → 복호화 → 인스펙션 → 메모리 zero 검증(읽기 시 0x00 채워짐)

**Phase 1D Gate:** 1회의 검사 라이프사이클 동안 평문이 디스크에 닿지 않음을 자동/감사 로그로 입증.

---

### Phase 2A: Bedrock Agent 연동

- [ ] **2A-1.** AWS Bedrock 모델 액세스 승인 (Console에서 Anthropic Claude 모델 enable)
- [ ] **2A-2.** Bedrock Agent 생성 — 시스템 프롬프트(System Prompt) 템플릿: "You are a code-leak detector. Compare the developer prompt to the proprietary code provided as context. Report whether prompt contains substantive overlap. Do NOT echo the context. Output JSON only."
- [ ] **2A-3.** RAG Knowledge Base 생성 — S3 데이터 소스 + Titan Embeddings (또는 사내 정책 문서 인덱싱)
- [ ] **2A-4.** Validation Worker 확장: Bedrock `InvokeAgent` 호출, `temporary_context=plaintext_code`, `prompt=user_prompt`. 응답 JSON 파싱 → verdict
- [ ] **2A-5.** 의미론적 유사도 fallback (Bedrock 장애 대비): 로컬 임베딩(`sentence-transformers/all-MiniLM-L6-v2`) + cosine similarity 임계치
- [ ] **2A-6.** 단위 테스트: `botocore.stub`으로 Bedrock 응답 mock
- [ ] **2A-7.** 통합 테스트: 실제 Bedrock invoke (저렴한 Haiku 모델) → 응답 스키마 안정성 검증
- [ ] **2A-8.** 비용 가드: 일일 토큰 한도 + per-request prompt 길이 cap (env-driven)

**Phase 2A Gate:** 알려진 leak 시나리오(샘플 proprietary 함수를 prompt에 그대로 포함)에서 BLOCK, 무관 prompt에서 ALLOW.

---

### Phase 2B: SaaS Dashboard (React/Vite)

- [ ] **2B-1.** Vite + React 18 + TypeScript 스캐폴드 — `dashboard/` 디렉터리
- [ ] **2B-2.** 인증: AWS Cognito Hosted UI 또는 사내 SSO PoC (Task-2 범위에서는 단일 admin 토큰 가능)
- [ ] **2B-3.** 화면:
  - **Live Stream** — Task-1 UI 확장(WebSocket), 필터(user, verdict, time range)
  - **Rule Editor** — YAML/JSON 룰 편집기, validate + apply
  - **RAG Manager** — 정책 문서 업로드 → S3 → Bedrock KB sync 트리거
  - **Audit** — DynamoDB/OpenSearch 쿼리, CSV export
- [ ] **2B-4.** Control Plane API(FastAPI) 확장: `/rules`, `/rag/objects`, `/audit/search`
- [ ] **2B-5.** Playwright E2E 테스트 (`tests/e2e/`): 5가지 주요 사용자 시나리오
- [ ] **2B-6.** Lighthouse 점수: Performance ≥ 80, Accessibility ≥ 90

**Phase 2B Gate:** End-to-end: dev VM에서 Claude Code → eBPF → mitmproxy → EC2 Bedrock 검사 → 대시보드 실시간 표시.

---

### Phase 2C: Logging & Visualization Hardening

- [ ] **2C-1.** OpenSearch Service domain 생성 (또는 ELK 자체 호스팅) — 로그 적재
- [ ] **2C-2.** Logstash/Fluent Bit pipeline: EC2 → OpenSearch
- [ ] **2C-3.** OpenSearch Dashboards: 차단율, 사용자별 시도 수, 룰 매칭 분포
- [ ] **2C-4.** 알람: `error_rate > 5%` 또는 `block_rate spike` SNS 알림 (10분 단위)
- [ ] **2C-5.** 보존 정책: hot 30d / warm 90d / cold S3 1y

---

## 4. 비기능 요구사항

| 영역 | 목표 |
|---|---|
| 지연(Endpoint→Verdict) | p50 < 150ms, p95 < 500ms (Bedrock 호출 포함) |
| 가용성 | EC2 단일 인스턴스 PoC. 후속 단계에서 ASG + ALB |
| 보안 | KMS CMK, mTLS, IAM 최소 권한, 디스크 미저장 검증 |
| 관측성 | 구조화 로그 + DynamoDB/OpenSearch 인덱싱, 핵심 메트릭 CloudWatch |
| 비용 | Bedrock 일일 한도, EC2 t3.micro PoC 단계 |

---

## 5. 테스트 전략

| 레벨 | 도구 | 대상 |
|---|---|---|
| Unit | pytest, pytest-asyncio | rule engine, kms wrapper, bedrock 클라이언트 어댑터 |
| Integration | pytest + LocalStack(KMS/S3/DynamoDB) + botocore.stub(Bedrock) | Validation Worker 파이프라인 |
| Contract | grpcio test + protobuf round-trip | gRPC schema 호환성 |
| E2E | Playwright + 실 AWS sandbox 계정 | 대시보드 워크플로우 |
| Security | `auditd`, `inotify`, `bandit`, `pip-audit` | 디스크 미저장 / 알려진 취약점 |
| Load | `locust` | gRPC 1k req/min PoC |

자동화 통합:
- GitHub Actions: PR마다 unit + integration(LocalStack), 매일 E2E(staging AWS)
- 모든 테스트 통과 후 `terraform apply` 수동 승인

---

## 6. 리스크 및 결정 보류 항목 (Task-2 시작 전 사용자 협의)

| ID | 항목 | 필요 결정 |
|---|---|---|
| R1 | AWS 계정/예산 | 사용자가 IAM credential 제공 + 월 예산 cap 합의 |
| R2 | 사내 PKI 부재 | mTLS 인증서를 self-signed로 PoC할지, 사내 CA 발급 받을지 |
| R3 | Bedrock 모델 액세스 승인 시간 | Anthropic Claude 모델 region(보통 us-east-1) 가용성 확인 |
| R4 | OpenSearch vs DynamoDB | 검색 요건이 단순하면 DynamoDB로 충분, 풀텍스트는 OpenSearch |
| R5 | 대시보드 인증 | Cognito vs 사내 SSO vs 단일 admin token (PoC는 단일 token 권장) |
| R6 | eBPF 사용자권한 | dev VM에서 `CAP_BPF` 또는 `CAP_SYS_ADMIN` 필요. 어디까지 허용 가능한지 |

---

## 7. TODO 마스터 체크리스트 (재개용)

### Phase 1A — eBPF Transparent Interception
- [ ] 1A-1 VM 부트스트랩
- [ ] 1A-2 eBPF 도구 설치
- [ ] 1A-3 BCC cgroup_skb 프로그램
- [ ] 1A-4 iptables REDIRECT 통합
- [ ] 1A-5 SNI 기반 mitmproxy 분기
- [ ] 1A-6 자동 transparent 테스트
- [ ] 1A-7 일반 트래픽 비간섭 검증
- [ ] 1A-8 eBPF stats 로깅

### Phase 1B — gRPC Egress
- [ ] 1B-1 proto 정의
- [ ] 1B-2 클라이언트 구현
- [ ] 1B-3 mTLS
- [ ] 1B-4 timeout/안전차단
- [ ] 1B-5 단위 테스트
- [ ] 1B-6 통합 테스트

### Phase 1C — EC2 gRPC 서버 + 정규식
- [ ] 1C-1 Terraform IaC
- [ ] 1C-2 systemd 서비스
- [ ] 1C-3 룰셋 모델
- [ ] 1C-4 단위 테스트
- [ ] 1C-5 통합 테스트
- [ ] 1C-6 DynamoDB/OpenSearch 로깅

### Phase 1D — Zero-Knowledge KMS
- [ ] 1D-1 KMS CMK
- [ ] 1D-2 S3 SSE-KMS
- [ ] 1D-3 IAM 최소 권한
- [ ] 1D-4 In-memory decrypt + wipe
- [ ] 1D-5 디스크 미기록 감사
- [ ] 1D-6 통합 테스트

### Phase 2A — Bedrock Agent
- [ ] 2A-1 모델 액세스 승인
- [ ] 2A-2 Agent 시스템 프롬프트
- [ ] 2A-3 RAG Knowledge Base
- [ ] 2A-4 InvokeAgent 통합
- [ ] 2A-5 로컬 임베딩 fallback
- [ ] 2A-6 단위 테스트(stub)
- [ ] 2A-7 통합 테스트(실 Bedrock)
- [ ] 2A-8 비용 가드

### Phase 2B — SaaS Dashboard
- [ ] 2B-1 Vite/React 스캐폴드
- [ ] 2B-2 인증
- [ ] 2B-3 4개 화면 구현
- [ ] 2B-4 Control Plane API
- [ ] 2B-5 Playwright E2E
- [ ] 2B-6 Lighthouse 통과

### Phase 2C — Logging & Viz
- [ ] 2C-1 OpenSearch domain
- [ ] 2C-2 로그 파이프라인
- [ ] 2C-3 Dashboards
- [ ] 2C-4 알람
- [ ] 2C-5 보존 정책

---

## 8. 재개 프로토콜
1. 본 파일 §7의 가장 최근 미체크 항목으로 이동.
2. 직전 Phase Gate 검증 재실행.
3. `git status`로 의도치 않은 변경 점검.
4. 변경 추적: 각 Phase는 별도 PR/브랜치 권장.

---

## 9. 코드 수정 금지 — 시작 조건

- Task-2의 모든 세부 작업은 **Task-1 완료 + 본 문서 사용자 검토 + 명시적 "Task-2 시작" 지시** 후에만 착수.
- 본 문서가 한 번에 완벽하지 않을 수 있으므로, 각 Phase 시작 전 §6 R1~R6 항목을 먼저 사용자와 협의한다.
