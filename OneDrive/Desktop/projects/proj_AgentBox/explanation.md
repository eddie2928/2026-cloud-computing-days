# AgentBox - 시스템 구조와 워크플로우

---

## 1. 한 줄 요약

AgentBox는 Claude Code와 Anthropic API 사이에 투명 프록시를 삽입해, **기업 코드 유출 여부를 Bedrock Agent가 자동으로 판단하고 차단**하는 보안 감사 시스템이다.

---

## 2. 전체 인프라 아키텍처

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ Endpoint  (WSL2 / Linux VM)                                                    │
│                                                                                │
│  [1회성 초기화]                                                                  │
│  $ encrypt_and_upload.sh ./src/  ─────────────────────────────────────────────►│
│                                                                                │
│  Claude Code (Node.js)                                                         │
│      │                                                                         │
│      │ iptables OUTPUT REDIRECT                                                │
│      │ (uid-based, dport 443 → :8080)                                          │
│      ▼                                                                         │
│  mitmproxy :8080 (AgentBoxAddon)                                               │
│  ├── TLS 복호화 (agentbox-ca.crt, 동적 leaf cert)                               │
│  ├── api.anthropic.com/v1/messages 만 필터                                     │
│  └── gRPC Inspect(prompt, user_id) ──── mTLS ──────────────────────────────►  │
│         │ verdict{ALLOW|BLOCK, reasons}  ◄────────────────────────────────── │
│         │                                                                      │
│         ├── BLOCK → 403 "Blocked by AgentBox"                                 │
│         └── ALLOW → upstream forward                                           │
└────────────────────────────────────────────────────────────────────────────────┘
                                    │ mTLS gRPC :50051
                                    ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│ AWS  us-east-1                                          VPC  10.0.0.0/16       │
│                                                                                │
│  ┌───────────────────── Public Subnet 10.0.1.0/24 + EIP ──────────────────┐   │
│  │                                                                         │   │
│  │  EC2  t3.micro                                                          │   │
│  │                                                                         │   │
│  │  ┌── agentbox-grpc :50051 ─────────────────────────────────────────┐   │   │
│  │  │   SG: endpoint CIDR 만 허용                                      │   │   │
│  │  │   IAM: KMS Decrypt · S3 Read(encrypted-code)                    │   │   │
│  │  │        S3 Write/Delete(kb-staging) · Bedrock · DynamoDB         │   │   │
│  │  │                                                                  │   │   │
│  │  │   ① regex 1차 필터 (rules.yaml) — 패턴 매칭 시 즉시 BLOCK        │   │   │
│  │  │   ② bedrock-agent-runtime.invoke_agent(prompt)                  │   │   │
│  │  │   ③ 검사 완료 후 DynamoDB events 기록                            │   │   │
│  │  │   ④ InspectResponse{verdict, reasons, event_id} 반환            │   │   │
│  │  └──────────────────────────────────────────────────────────────────┘   │   │
│  │                                                                         │   │
│  │  ┌── agentbox-mcp :8443 ───────────────────────────────────────────┐   │   │
│  │  │   SG: VPC CIDR 만 허용 (Lambda ENI)                              │   │   │
│  │  │                                                                  │   │   │
│  │  │   POST /mcp/decrypt_and_stage                                    │   │   │
│  │  │     S3 encrypted-code ──► sops --decrypt ──► kb-staging 업로드  │   │   │
│  │  │     bytearray zero-fill                                          │   │   │
│  │  │   DELETE /mcp/cleanup/{session_id}                               │   │   │
│  │  │     kb-staging 객체 즉시 삭제                                    │   │   │
│  │  └──────────────────────────────────────────────────────────────────┘   │   │
│  │                                                                         │   │
│  │  ┌── agentbox-saas :8000 ───────────────────────────────────────────►  Browser
│  │  │   SG: 관리자 IP 만 허용                                             │   │
│  │  │   WS  /pipeline/stream  — DynamoDB 실시간 이벤트                   │   │
│  │  │   GET  /audit            — 날짜·verdict 필터 + CSV export           │   │
│  │  │   PUT  /settings/prompt  — Bedrock 시스템 프롬프트 편집             │   │
│  │  │   PUT  /settings/kb-ttl  — KB 버킷 객체 보존 기간                  │   │
│  │  └──────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
│  Lambda: {project}-mcp-bridge  (Bedrock Action Group)                         │
│  ├── Bedrock → Lambda: decrypt_and_stage(project_id, session_id)              │
│  └── Lambda → EC2 MCP: POST /mcp/decrypt_and_stage  (HTTP, VPC 내부)          │
│                                                                                │
│  Lambda: {project}-metrics-publisher  (DynamoDB Streams 트리거)               │
│  └── INSERT/MODIFY 이벤트 → BlockRate · EventCount · ErrorRate → CloudWatch   │
│                                                                                │
│  Bedrock Agent  (claude-haiku-20240307)                                        │
│  ├── Action Group: mcp-bridge Lambda                                           │
│  ├── Knowledge Base: kb-staging 버킷                                           │
│  └── 반환: {"verdict": "BLOCK"|"ALLOW", "reasons": [...]}                     │
│                                                                                │
│  KMS CMK  alias/agentbox-sops-key                                              │
│  ├── 개발자 IAM: kms:Encrypt · kms:GenerateDataKey                            │
│  └── EC2 IAM Role: kms:Decrypt 만                                              │
│                                                                                │
│  S3: {project}-encrypted-code   SSE-KMS · 버전관리 · 퍼블릭 차단              │
│  S3: {project}-kb-staging       SSE-KMS · Bedrock Agent IAM만 GetObject       │
│                                                                                │
│  DynamoDB: events    PK=event_id  SK=ts  GSI=user_id-ts  TTL=365일  Stream=ON │
│  DynamoDB: settings  PK=key  (Bedrock 시스템 프롬프트, KB TTL 등)              │
│                                                                                │
│  CloudWatch                                                                    │
│  ├── Log Groups: /agentbox/ec2/{grpc,mcp,saas}  보존 90일                     │
│  ├── Alarm: BlockRate  > 10% (10분 평균) → SNS → 이메일                       │
│  └── Alarm: ErrorRate  > 5%  (10분 평균) → SNS → 이메일                       │
└────────────────────────────────────────────────────────────────────────────────┘
                         │ verdict == ALLOW
                         ▼
                  api.anthropic.com
```

---

## 3. 요청 1건 처리 워크플로우

Claude Code가 Anthropic API를 호출할 때마다 다음 흐름이 실행된다.

```
Claude Code
  │  HTTPS POST /v1/messages
  │  (iptables가 443 → :8080 리다이렉트)
  ▼
mitmproxy AddonBox
  │  TLS 복호화 → prompt, user_id, model 추출
  │  gRPC Inspect(prompt, user_id, model)  timeout=5s
  ▼
EC2 agentbox-grpc
  │
  ├─[패턴 매칭]─ rules.yaml regex 1차 필터
  │                AWS Access Key / 비밀번호 / API Key 등
  │                매칭 시: 즉시 BLOCK 반환 (Bedrock 생략)
  │
  └─[통과]─ bedrock-agent-runtime.invoke_agent(prompt, session_id=event_id)
                │
                ▼
            Bedrock Agent  (claude-haiku)
                │  "코드 샘플 가져와서 비교하라"
                │  → Action Group Lambda 호출
                ▼
            Lambda mcp-bridge
                │  POST https://ec2-eip:8443/mcp/decrypt_and_stage
                │       {project_id, session_id}
                ▼
            EC2 agentbox-mcp
                │  S3 encrypted-code 다운로드 (.enc 파일)
                │  sops --decrypt  →  bytearray 버퍼
                │  S3 kb-staging/staging/{session_id}/ 업로드
                │  bytearray[:] = b'\x00' * len  (zero-fill)
                │  반환: {kb_bucket, prefix}
                ▼
            Bedrock Agent
                │  KB 버킷 내용과 prompt 비교
                │  반환: {"verdict": "BLOCK"|"ALLOW", "reasons": [...]}
                ▼
EC2 agentbox-grpc
  │  DELETE /mcp/cleanup/{session_id}  (KB 버킷 객체 삭제)
  │  DynamoDB events 기록
  │    (event_id, ts, user_id, prompt_hash, verdict, reasons, latency_ms)
  │  InspectResponse{verdict, reasons, event_id} 반환
  ▼
mitmproxy AddonBox
  ├── BLOCK → flow.response = HTTP 403 "Blocked by AgentBox: {reasons}"
  └── ALLOW → return  (upstream forward to api.anthropic.com)
```

**Bedrock 장애 시 Fallback 순서:**
1. regex 1차 필터 통과 후 Bedrock 오류 → semantic fallback (sentence-transformers/all-MiniLM-L6-v2, cosine ≥ 0.85 시 BLOCK)
2. gRPC timeout(5s) 또는 RpcError → 안전 차단 (BLOCK)

**비용 가드:**
- `BEDROCK_MAX_TOKENS_PER_DAY` (기본 100,000) 초과 시 regex-only 모드
- `PROMPT_MAX_CHARS` (기본 8,000) 초과 시 즉시 BLOCK

---

## 4. 코드 암호화 워크플로우 (초기 1회 + 코드 변경 시)

```
[개발자 로컬]

  $ ./scripts/encrypt_and_upload.sh ./src/
        │
        │ SOPS + KMS CMK (alias/agentbox-sops-key)
        │ Developer IAM: kms:Encrypt 권한
        ▼
  ./encrypted/src/**/*.enc    ← 암호문 파일 (바이너리)
        │
        │ aws s3 sync
        ▼
  S3: {project}-encrypted-code/
      SSE-KMS (서버 측 2중 암호화)
      버전관리 ON

[EC2 agentbox-mcp — 검사 요청 1건당]

  S3에서 .enc 다운로드
        │
        │ sops --decrypt --output-type binary (subprocess)
        │ EC2 IAM Role: kms:Decrypt 권한
        ▼
  bytearray 버퍼  (메모리, 디스크 미기록)
        │
        │ aws s3 put-object
        ▼
  S3: {project}-kb-staging/staging/{session_id}/
      Bedrock Agent IAM Role만 GetObject 허용
        │
        ▼
  Bedrock Agent 판단 완료
        │
        │ DELETE (즉시 또는 TTL 5분 이내)
        ▼
  KB 버킷 객체 삭제 + bytearray[:] = b'\x00' * len (zero-fill)
```

평문 코드는 검사 순간에만 Bedrock-only 접근 버킷에 임시 존재한다.
EC2 디스크, 로그, 기타 저장소에 평문이 남지 않는다.

---

## 5. 관측성

| 채널 | 내용 | 보존 |
|------|------|------|
| CloudWatch Logs `/agentbox/ec2/grpc` | gRPC 서버 stdout (loguru JSON) | 90일 |
| CloudWatch Logs `/agentbox/ec2/mcp` | MCP 서버 stdout | 90일 |
| CloudWatch Logs `/agentbox/ec2/saas` | SaaS 서버 stdout | 90일 |
| CloudWatch Metrics `AgentBox/BlockRate` | DynamoDB Streams → Lambda → CW | - |
| CloudWatch Metrics `AgentBox/EventCount` | 동일 | - |
| CloudWatch Metrics `AgentBox/ErrorRate` | 동일 | - |
| SNS 이메일 알람 | BlockRate > 10% 또는 ErrorRate > 5% (10분 평균) | - |
| DynamoDB events 테이블 | event_id, verdict, reasons, latency_ms 등 전체 감사 로그 | TTL 365일 |
| SaaS 대시보드 `/pipeline/stream` | WebSocket 실시간 이벤트 | - |

---

## 6. 보안 모델 요약

| 영역 | 적용 메커니즘 |
|------|--------------|
| 트래픽 인터셉트 | iptables uid-based REDIRECT (HTTPS_PROXY 환경변수 불필요) |
| TLS 복호화 | 자체 Root CA → 동적 leaf cert → agentbox-ca 신뢰 등록 |
| Endpoint ↔ EC2 통신 | mTLS (자체 CA 서명 endpoint.crt + ec2.crt 양방향 검증) |
| 코드 암호화 | SOPS + KMS CMK; 개발자=Encrypt 전용, EC2=Decrypt 전용 |
| KB 버킷 격리 | Bedrock Agent IAM Role만 GetObject; EC2 직접 읽기 불가 |
| 평문 수명 | 검사 1건 기간만 존재 → 삭제 + zero-fill |
| EC2 네트워크 | SG로 포트별 소스 CIDR 최소화; 외부 아웃바운드 IGW 직접 |
| 감사 | DynamoDB events 전건 기록; CloudWatch 알람 자동 통지 |

---

## 7. 로컬 엔드포인트 활성화/비활성화

```
agentbox on   ← shell 함수 (source scripts/activate.sh)
  ├── CA 없으면 agentbox ca  →  certs/ 생성
  ├── trust store 미등록이면  →  install_ca.sh (sudo)
  ├── AGENTBOX_TRANSPARENT=1 이면
  │     iptables_redirect.sh on  (uid-based 443→8080 REDIRECT)
  │     HTTPS_PROXY 미설정
  └── 아니면 (일반 모드)
        export HTTPS_PROXY=http://127.0.0.1:8080
  export NODE_EXTRA_CA_CERTS=certs/agentbox-ca.crt
  nohup agentbox run &  →  .agentbox.pid 저장

agentbox off  ← shell 함수 (source scripts/deactivate.sh)
  ├── AGENTBOX_TRANSPARENT=1 이면  iptables_redirect.sh off
  ├── .agentbox.pid  →  kill
  └── unset HTTPS_PROXY, NODE_EXTRA_CA_CERTS
```

> **왜 shell 함수인가?**
> 자식 프로세스는 부모 shell의 환경변수를 변경할 수 없다.
> `source`로 현재 shell에서 직접 실행해야 `export`가 반영된다.

---

## 8. 핵심 용어

| 용어 | 의미 |
|------|------|
| **MITM** | 두 통신 주체 사이에 끼어 트래픽을 투명하게 감청/조작하는 기법. |
| **iptables REDIRECT** | 커널 netfilter에서 특정 uid의 443 패킷을 로컬 포트로 강제 리다이렉트. |
| **Root CA** | 다른 인증서를 서명할 수 있는 최상위 인증 기관. trust store 등록 시 하위 인증서 자동 신뢰. |
| **mTLS** | Mutual TLS. 서버·클라이언트 양방향 인증서 검증. Endpoint ↔ EC2 gRPC에 적용. |
| **gRPC** | Protocol Buffers 기반 고성능 RPC 프레임워크. `inspect.proto`로 서비스 정의. |
| **Connection Pool** | gRPC 채널을 재사용해 매 요청마다 핸드쉐이크 오버헤드 제거. 최대 5채널. |
| **SOPS** | Mozilla Secrets OPerationS. 파일을 KMS 키로 암호화. 암호화 파일 git 커밋 가능. |
| **KMS CMK** | AWS Customer Managed Key. 키 정책으로 IAM별 Encrypt/Decrypt 권한 분리. |
| **SSE-KMS** | S3 서버 측 KMS 암호화. SOPS 파일이 S3에 2중 암호화되어 저장됨. |
| **Zero-fill** | 복호화 후 bytearray 버퍼를 0으로 덮어쓰는 보안 기법. `buf[:] = b'\x00' * len(buf)`. |
| **Bedrock Agent** | System Prompt + Action Group(Lambda) + Knowledge Base로 구성된 AWS 완전관리형 AI 에이전트. |
| **Action Group** | Bedrock Agent가 호출할 수 있는 Lambda 함수 집합. 함수 스펙을 JSON 스키마로 정의. |
| **Knowledge Base** | Bedrock Agent가 참조하는 문서 저장소. S3 버킷 + 임베딩 인덱스. |
| **KB Staging 버킷** | 검사 시점에만 복호화 코드를 임시 저장하는 S3 버킷. Bedrock Agent IAM만 읽기 가능. |
| **MCP (Model Context Protocol)** | Anthropic 설계 AI 모델-도구 통신 표준. Lambda가 EC2 MCP Server를 호출하는 브릿지 역할. |
| **Semantic Fallback** | Bedrock 장애 시 sentence-transformers 코사인 유사도 ≥ 0.85로 대체 판정. |
| **DynamoDB GSI** | Global Secondary Index. 기본 키 외 속성(user_id-ts)으로 조회하기 위한 보조 인덱스. |
| **DynamoDB Streams** | 테이블 변경(INSERT/MODIFY)을 이벤트로 발행. Lambda metrics-publisher 트리거에 사용. |
| **EIP (Elastic IP)** | EC2에 고정 공인 IP 할당. 퍼블릭 서브넷 + IGW 조합으로 NAT Gateway 없이 외부 통신. |
| **Terraform IaC** | AWS 리소스를 HCL 코드로 선언 관리. `terraform apply`로 실제 리소스 생성. |
