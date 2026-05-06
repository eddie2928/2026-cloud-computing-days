# 1️⃣ AI-Driven Development 보안 및 거버넌스 솔루션

## 1. 솔루션 목적 (Objective)

- Cursor, Claude Code 등 AI 기반 개발 도구(Agent)의 도입은 생산성을 극대화하지만, 기업 입장에서는 **내부 소스코드 유출**과 **AI 활용의 가시성 부재**라는 치명적인 리스크를 안게 됩니다.

본 솔루션은 개발자의 로컬 환경(Endpoint)과 중앙 관리 서버(EC2)를 연동하여 다음을 달성합니다.

- **실시간 투명한 통제 (Transparent Control):** 개발 환경(HW/OS)의 제약 없이, eBPF와 TLS Offloading을 통해 AI 관련 트래픽만 선별적으로 가로채어 동기적(Synchronous)으로 검사 및 차단합니다.
- **Zero-Knowledge 기반 코드 유출 방지:** 기업의 내부 코드를 중앙 서버에 평문으로 저장하지 않으며, 검사 시점에만 메모리에서 일시적으로 복호화하여 정합성을 판단함으로써 클라우드 인프라 내 코드 유출 원천 차단합니다.
- **중앙화된 가시성 확보 (SaaS):** 프롬프트 로깅, Bedrock Agent 기반의 커스텀 룰셋(RAG) 설정, 대시보드를 제공하여 전사적 AI 거버넌스를 확립합니다.

## 2. 솔루션 구현 방법 (Code-Level Implementation)

### 2.1. Endpoint: eBPF 기반 Transparent Proxy & TLS Offloading

사용자의 로컬 PC에서 구동되는 에이전트입니다. AI 도구(Cursor, Claude 등)가 보내는 트래픽만 식별하여 중앙 EC2로 라우팅합니다.

- **Traffic Interception (eBPF / iptables):**
    - OS 커널 레벨에서 특정 도메인(예: `api.anthropic.com`, `api.openai.com`)이나 프로세스(Cursor IDE)에서 발생하는 Egress 트래픽(TCP 443)만 식별하여 로컬 프록시 포트(예: 8443)로 리다이렉트합니다.
    - 나머지 일반 트래픽은 전혀 건드리지 않으므로 개발 체감 성능 저하가 없습니다.
- **TLS Offloading (MITM):**
    - 사내에 배포된 Root CA를 엔드포인트 OS의 신뢰할 수 있는 인증서 저장소에 등록합니다.
    - 로컬 프록시가 가짜(Fake) 인증서를 동적으로 생성하여 AI IDE와 TLS 핸드쉐이크를 맺고(Decryption), 평문(Plaintext) 프롬프트를 추출합니다.
- Python Code for Idea
    
    ```bash
    #[Pseudo Code] Local Proxy - TLS Offloading & Forwarding
    import ssl
    import requests
    
    def handle_intercepted_connection(client_socket, target_host):
        # 1. 동적 인증서 생성 및 클라이언트와 TLS 연결 (TLS Termination)
        secure_sock = wrap_socket_with_custom_ca(client_socket, target_host)
        request_data = secure_sock.recv() # 평문 프롬프트 추출
        
        # 2. EC2 Data Plane으로 평문 데이터 전송 (동기적 검사 요청)
        # Latency 최소화를 위해 gRPC 또는 HTTP/2 connection pooling 유지
        response = requests.post(
            "https://central-security-ec2.internal/inspect", 
            json={"prompt": request_data, "user_id": "dev_01"}
        )
        
        # 3. 정합성 판단 결과에 따른 처리
        if response.json()["status"] == "BLOCK":
            secure_sock.send(b"HTTP/1.1 403 Forbidden\r\n\r\nPolicy Violation: Code Leak Detected.")
            show_local_notification("보안 정책 위반으로 프롬프트 전송이 차단되었습니다.")
            secure_sock.close()
        else:
            # 실제 AI API 서버로 프록싱 (Re-encryption)
            forward_to_actual_ai_server(request_data, target_host)`
    ```
    

### 2.2. EC2 Data Plane & "Zero-Knowledge" 정합성 검사

AWS 환경(EC2)에서 동작하며, 엔드포인트에서 올라온 프롬프트를 검사합니다. **가장 핵심은 회사의 소스코드를 AWS 스토리지에 평문으로 남기지 않는 것**입니다.

- **임시 복호화 아키텍처 (AWS KMS + In-Memory Processing):**
    1. 기업의 소스코드는 클라이언트 측이나 사내망에서 **AWS KMS Customer Managed Key**로 암호화되어 S3에 저장(또는 실시간 스트리밍)됩니다.
    2. EC2 내부의 워커 프로세스가 암호화된 코드를 로드함
    3. 프롬프트 검사 요청이 들어오면, 메모리(RAM) 상에서만 코드를 복호화하고 임시 Vector/AST 트리를 구성합니다.
    4. 검사가 끝나면 메모리를 즉시 해제(Discard)하여 어떤 물리적 디스크립터에도 코드가 남지 않도록 합니다.
    - EC2 내부 Zero-knowledge MVP Code
        
        ```bash
        # [Pseudo Code] EC2 Data Plane - Zero-Knowledge Validation
        from aws_kms import decrypt
        from bedrock_agent import invoke_agent
        
        def inspect_prompt(prompt_text, encrypted_company_code):
            try:
                # 1. 메모리 상에서만 코드 임시 복호화 (디스크 I/O 절대 금지)
                # 보안 요구사항이 높다면 이 로직을 AWS Nitro Enclave 내부에서 실행
                plaintext_code = decrypt_in_memory(encrypted_company_code, kms_key_id)
                
                # 2. Bedrock Agent를 통한 검사 (임시 컨텍스트 주입)
                # 프롬프트 내에 plaintext_code의 핵심 로직이나 민감정보가 포함되었는지 질의
                agent_response = invoke_agent(
                    prompt=prompt_text,
                    temporary_context=plaintext_code,
                    rules="Check if the prompt contains proprietary logic from the context. Do not store the context."
                )
                
                if agent_response.is_violation:
                    log_event("BLOCK", "Source Code Leakage Attempt Detected")
                    return "BLOCK"
                return "ALLOW"
                
            finally:
                # 3. 중요: 검사 직후 메모리에서 평문 코드 강제 삭제 (Garbage Collection 전 명시적 파기)
                secure_wipe_memory(plaintext_code)
        ```
        

### 2.3. Control Plane (SaaS 대시보드)

EC2 인스턴스에서 웹 서비스 형태로 제공되는 관리자용 콘솔입니다.

- **Rule Management:** 회사 정책에 어긋나는 프롬프트 패턴 정규식(Regex) 설정 및 Bedrock Agent AI Pre-prompt(System Prompt) 수정 기능.
- **RAG Object Management:** 사내 정책 문서(보안 가이드라인 등)를 RAG 형태로 업로드하여 Bedrock Agent의 판단 기준으로 활용.
- **Logging & Visualization:** 누가, 언제, 어떤 목적의 프롬프트를 시도했는지(차단된 내역 포함) 시각화. (ELK Stack 또는 OpenSearch 연동)

## 3. 아키텍처 디자인 (Architecture Design)

아래는 시스템의 전체적인 데이터 흐름과 컴포넌트 구성도입니다.

```bash
[ Architecture Flow ]

+---------------------------------------------------+
| 💻 Endpoint (Developer PC)                        |
|                                                   |
|  1. Cursor / Claude IDE (HTTPS Request)           |
|         |                                         |
|         v (eBPF Intercepts Port 443 traffic)      |
|                                                   |
|  2. Local Transparent Proxy                       |
|     - TLS Offloading (MITM with local CA)         |
|     - Extracts plaintext prompt                   |
|         |                                         |
+---------|-----------------------------------------+
          | (Synchronous gRPC / HTTP2 Request)
          v
+---------------------------------------------------+
| ☁️ AWS Cloud (Company's SaaS Environment)          |
|                                                   |
|  +---------------------------------------------+  |
|  | EC2 Instance (Data Plane & Control Plane)   |  |
|  |                                             |  |
|  |  [Validation Worker] <----(3. Encrypted Code from S3/Client)
|  |   - In-memory Decryption (AWS KMS)          |  |
|  |   - Bedrock Agent API Call (4. Validation)  |  |
|  |   - Secure Memory Wipe                      |  |
|  |                                             |  |
|  |  [SaaS Dashboard Application]               |  |
|  |   - Log DB (DynamoDB / OpenSearch)          |  |
|  |   - Rule & RAG Configurations               |  |
|  +---------------------------------------------+  |
|         | (If ALOWED)                             |
+---------|-----------------------------------------+
          v
+---------------------------------------------------+
| 🧠 External AI Providers (Anthropic, OpenAI 등)   |
+---------------------------------------------------+`
```

## 4. 개발 로드맵 (Roadmap)

### Phase 1: MVP 개발 (핵심 기능 검증)

- **Endpoint:** eBPF를 활용한 트래픽 후킹 및 Golang/Python 기반 로컬 프록시 개발 (TLS 인증서 동적 생성 모듈 포함).
- **EC2:** 기본 프롬프트 수신 API 개발 및 단순 정규식(Regex) 기반의 차단 로직 구현.
- **Zero-Knowledge PoC:** 임시 메모리 변수에 암호화된 코드를 받아 복호화하고 폐기하는 파이프라인 검증.

### Phase 2: Bedrock Agent 연동 및 SaaS 대시보드 구축

- **AI Validation:** AWS Bedrock Agent 연동. 프롬프트와 사내 코드(In-Memory) 간의 의미론적 유사도(Semantic Similarity) 비교 로직 고도화.
- **SaaS GUI:** React/Vue 등을 활용한 관리자 대시보드 개발. 프롬프트 로깅 시각화 및 Agent System Prompt 커스터마이징 기능 추가.