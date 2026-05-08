# Task-3: AgentBox MCP 서버 분리 + EC2 부트스트랩 안정화 + 테스트 자동화

> 본 문서는 Task-2 구현 후 발견된 부트스트랩 실패와 Zero-Knowledge 격리 강화를 위해 **MCP 서버를 별도 EC2 인스턴스로 분리**하고, **userdata 실패 원인을 제거**하며, 사용자가 직접 답변한 4개 결정사항(Q&A)을 모두 반영하는 작업 계획이다. 모든 변경은 **재실행 가능한 step** 으로 구성하며, 각 단계 종료 시 자동/수동 검증을 통과해야 다음 단계로 넘어간다.
> 인코딩: UTF-8 (BOM 없음)
> 작성일: 2026-05-08

---

## 0. 메타 정보

| 항목 | 값 |
|---|---|
| Task ID | Task-3 |
| 선행 조건 | Task-2 코드(`ec2/`, `lambda/`, `infra/`) 가 git 상에 존재. 현재 EC2 부트스트랩 실패 상태에서 시작 가능. |
| 대상 OS | Endpoint: WSL2 Ubuntu 22.04 / App-EC2: Ubuntu 22.04 / MCP-EC2: Ubuntu 22.04 |
| 핵심 변경 | ① MCP 서버 별도 EC2 분리(IAM·SG·VPC 격리), ② userdata `apt-get install sops` 실패 원인 제거 후 GitHub release binary 사용, ③ `ec2/` + `src/agentbox/grpc/` 코드를 S3 경유로 EC2 에 자동 배포, ④ Lambda 를 VPC 내부로 이동 후 MCP private IP 로 호출, ⑤ MCP 평문 HTTP + admin_token 으로 단순화, ⑥ 기존 누락 3건 수정(`/mcp/cleanup` 호출, Bedrock 토큰 카운터, Bedrock Agent 리소스 자동 생성), ⑦ moto 기반 단위/통합 테스트 자동화, ⑧ `deploy.sh` 에 post_deploy 통합. |
| Capex 변동 | 기존 t3.micro × 1 → app(t3.micro) + mcp(t3.small). 월 +$8.4 ~ +$8.5 (us-east-1 on-demand 추정). NAT/VPC Endpoint 추가 없음. |
| 코드 수정 금지 | 본 문서 사용자 검토 및 "Task-3 시작" 명시 지시 전까지 일절 코드 변경 금지. |

---

## 1. 목표

1. **MCP 서버 격리**: KMS Decrypt + 평문 코드 일시 처리 권한이 별도 EC2(=mcp-EC2) 에만 존재. app-EC2(gRPC+SaaS) 가 침해당해도 평문 코드 접근 불가.
2. **부트스트랩 100% 성공**: 새 EC2 인스턴스의 user_data 가 끝까지 실행되어 `systemctl is-active` = active 가 systemd 3종(=app: grpc/saas, mcp: mcp) 에서 보장된다.
3. **재배포 1-커맨드**: `./scripts/deploy.sh -auto-approve` 하나로 terraform apply → SSM 등록 대기 → cert 푸시 → 헬스체크 까지 끝.
4. **자동 테스트**: 단위(moto) + 통합(moto + 로컬 gRPC + 로컬 FastAPI in-process) 으로 CI 가능. 실 AWS 의존 통합 테스트는 별도 마커(`@pytest.mark.aws`) 로 분리.

---

## 2. 아키텍처

### 2.1 변경 전(현재)

```
+----- 단일 EC2 (t3.micro) ----------+
|  gRPC :50051                       |  ← Endpoint
|  MCP  :8443  (평문 HTTP, 깨짐)     |  ← Lambda (https로 호출하다 fail)
|  SaaS :8000                        |  ← Admin
|  IAM: KMS Decrypt + Bedrock 모두   |
+------------------------------------+
Lambda: VPC 외부, public 인터넷 경유
```

### 2.2 변경 후(목표)

```
+--- App-EC2 (t3.micro, public subnet) ---+
|  gRPC :50051   (mTLS, Endpoint -> 50051) |
|  SaaS :8000    (admin_cidr -> 8000)      |
|  IAM: Bedrock InvokeAgent + DynamoDB     |
|  IAM: KMS 권한 없음, S3 enc-code 권한 X  |
+------------------------------------------+
            │ Bedrock InvokeAgent
            ▼
     Bedrock Agent (Claude Haiku)
            │ Action Group
            ▼
+--- Lambda (in VPC, lambda-sg) ---+
|  agentbox-mcp-bridge             |
|  egress: mcp-sg:8080 만 허용     |  ← 평문 HTTP + admin_token
+----------------------------------+
            │ POST http://<mcp-private-ip>:8080/mcp/decrypt_and_stage
            ▼
+--- MCP-EC2 (t3.small, public subnet) ---+
|  MCP :8080  (평문 HTTP + admin_token)    |  
|  sops binary (GitHub release)            |
|  IAM: KMS Decrypt + S3 enc-code Get     |
|       + S3 kb-staging RW                 |
|  IAM: Bedrock 권한 없음, DynamoDB 없음   |
+------------------------------------------+
```

> 포트 8443 → 8080 으로 변경. **이유**: 8443 은 관용적으로 TLS 포트인데 평문 HTTP 로 가니 혼동 방지. 또한 Lambda env `MCP_SERVER_URL` 도 `http://<private_ip>:8080` 으로 명확히 한다.

> Lambda 가 같은 VPC 의 ENI 로 들어가면서 lambda-sg 가 mcp-sg 의 8080 인그레스 소스로 사용된다. 트래픽은 인터넷에 나가지 않는다.

### 2.3 검사 1회 라이프사이클(변경 사항 강조)

| 단계 | 주체 | 동작 | 변경 |
|---|---|---|---|
| (1)~(3) | mitmproxy → gRPC client → app-EC2 gRPC | 동일 | - |
| (4) | Bedrock Agent | Action Group `decrypt_and_stage` 호출 → Lambda invoke | Bedrock Agent 리소스 신규 생성 |
| (5) | Lambda(VPC) | `POST http://mcp-priv-ip:8080/mcp/decrypt_and_stage` | URL 스킴/포트 변경 + private IP |
| (6) | MCP-EC2 | S3 enc-code → sops decrypt → kb-staging put | 위치만 변경(별 EC2) |
| (7) | Bedrock Agent | KB 조회 후 verdict JSON 반환 | - |
| (8) | **app-EC2 gRPC 서버** | `DELETE http://mcp-priv-ip:8080/mcp/cleanup/{event_id}` 호출 | **신규 추가(현재 누락)** |
| (9) | app-EC2 gRPC | DynamoDB events PutItem + 토큰 카운터 ADD `_increment_token_count` | **토큰 카운터 추가(현재 누락)** |
| (10) | mitmproxy | BLOCK 또는 forward | - |

---

## 3. 디렉터리 / 파일 변경 매트릭스

| 경로 | 동작 | 비고 |
|---|---|---|
| `infra/main.tf` | 수정 | private subnet 1개 + private RT 추가. NAT/VPC Endpoint 없음(Lambda 가 외부 호출 안 함). |
| `infra/ec2.tf` | 수정 | `aws_instance.main` 삭제 → `aws_instance.app` + `aws_instance.mcp` 신설. SG 둘(`app-sg`, `mcp-sg`). IAM Role 둘(`app-role`, `mcp-role`). Instance Profile 둘. SSM 정책 둘 다 부착. |
| `infra/kms.tf` | 수정 | 키 정책 `EC2Decrypt` Sid → principal 을 `aws_iam_role.mcp.arn` 으로 변경. |
| `infra/s3.tf` | 수정 | encrypted-code bucket policy 에 mcp-role 만 GetObject 허용. kb-staging RW 도 mcp-role + bedrock-agent-role. |
| `infra/lambda.tf` | 수정 | `vpc_config { subnet_ids = [private], security_group_ids = [lambda-sg] }`. `MCP_SERVER_URL` = `"http://${aws_instance.mcp.private_ip}:8080"`. lambda-sg 신설(egress: mcp-sg:8080). lambda IAM 에 `AWSLambdaVPCAccessExecutionRole` 부착. |
| `infra/dynamodb.tf` | 미변경 | 테이블 자체는 동일. (IAM 은 ec2.tf 에서 app-role 에만 부여.) |
| `infra/cloudwatch.tf` | 수정 | metrics_publisher Lambda 도 동일하나 IAM 분리는 없음. CloudWatch agent SSM parameter 유지. |
| `infra/bedrock.tf` | 수정 | 주석 처리된 `aws_bedrockagent_agent` 활성화 + `aws_bedrockagent_agent_action_group` + `aws_bedrockagent_agent_alias` 추가. App-EC2 env 에 `BEDROCK_AGENT_ID`, `BEDROCK_AGENT_ALIAS_ID` 자동 주입. |
| `infra/code_dist.tf` | **신규** | 로컬 `ec2/` + `src/agentbox/grpc/` 를 zip → S3 `agentbox-encrypted-code/_dist/code-${sha}.zip` 업로드. App/MCP userdata 가 download 후 압축 해제. |
| `infra/userdata-app.sh.tpl` | **신규** | sops 미포함. CloudWatch agent + venv + 코드 압축 해제 + 의존성(sentence-transformers 포함) + systemd unit 두 개(`agentbox-grpc`, `agentbox-saas`) + enable/start. |
| `infra/userdata-mcp.sh.tpl` | **신규** | sops GitHub release binary 다운로드(`v3.12.2`) → `/usr/local/bin/sops`. CloudWatch agent + venv + 코드 압축 해제 + 의존성(boto3, fastapi, uvicorn, pydantic, loguru) + systemd unit 한 개(`agentbox-mcp`) + enable/start. |
| `infra/userdata.sh.tpl` | **삭제** | 위 두 파일이 대체. |
| `ec2/grpc_server/server.py` | 수정 | `_invoke_bedrock_agent` 호출 후 `requests.delete(f"{MCP_SERVER_URL}/mcp/cleanup/{event_id}", headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}, timeout=5)` 추가. 토큰 카운터 `_increment_token_count(...)` 호출 추가(invoke 직후, chunks 길이 추정 토큰값 사용). |
| `ec2/mcp_server/server.py` | 수정 | uvicorn 포트 default 를 8443 → 8080. healthcheck `GET /healthz` 추가(인증 없음, `{"ok": true}`). |
| `lambda/mcp_bridge.py` | 미변경 | URL 은 환경변수에서 받음. |
| `scripts/deploy.sh` | 수정 | terraform apply 종료 후 자동으로 SSM 등록 대기 → cert SSM 푸시(2개 인스턴스) → MCP healthz curl(VPC 내부에선 안 닿으니 SSM 통한 EC2 자체 헬스체크) → systemd is-active 확인. 모든 단계 통과 시 OK. 실패 시 명확한 에러 메시지. |
| `scripts/post_deploy.sh` | **삭제(통합됨)** | deploy.sh 에 흡수. |
| `scripts/test_lifecycle_45.sh` | 미변경 | bucket/lambda 이름이 그대로라 동작. |
| `tests/unit/test_mcp_server.py` | **신규** | moto + FastAPI TestClient. KMS+S3 mock. decrypt_and_stage 정상/오류 케이스. cleanup. healthz. admin_token 검증. |
| `tests/unit/test_lambda_mcp_bridge.py` | **신규** | 환경변수 + Bedrock 이벤트 페이로드 → urllib mock 으로 MCP HTTP POST 호출 검증. |
| `tests/unit/test_grpc_cleanup_call.py` | **신규** | gRPC `Inspect` 후 `requests.delete` 가 정확히 호출되는지 검증(moto 또는 responses 라이브러리). |
| `tests/unit/test_token_counter.py` | **신규** | `_increment_token_count` 가 invoke 후 호출되는지 검증(moto DynamoDB). |
| `tests/integration/test_mcp_e2e.py` | **신규** | moto KMS+S3 → 실제 sops 바이너리 호출 → MCP FastAPI in-process → kb-staging upload 확인 → cleanup. |
| `tests/integration/test_lambda_to_mcp.py` | **신규** | moto+responses. Lambda handler 를 직접 import 후 호출, 내부 urllib 가 정확한 URL/헤더로 호출하는지 검증. |
| `tests/conftest.py` | 수정 | 공통 fixture(`mock_aws`, `tmp_kms_key`, `sops_yaml`, `admin_token` 등) 추가. |
| `tests/aws/test_real_lifecycle.py` | **신규(선택)** | 실 AWS 통합 테스트. `@pytest.mark.aws` 로 분리. 기본은 skip, `pytest -m aws` 로만 실행. |
| `requirements-dev.txt` 또는 `pyproject.toml [dev]` | 수정 | `moto[all]>=5`, `responses>=0.24`, `httpx`, `pytest-mock`, `aws-sam-cli` (선택) 추가. |

---

## 4. 단계별 작업 계획 (Phase)

> 각 Phase 는 **자체 완결 검증** 을 가진다. Plan 이 중간에 끊겨도 §8 TODO 마스터 체크리스트의 가장 최근 미체크(`- [ ]`) Phase 부터 재시작 가능.

### Phase 3A — Terraform 인프라 분리 (코드만, apply 안 함)

**목적**: `infra/` 의 Terraform 코드만 변경. `terraform plan` 에 새 리소스가 정확히 보이고 destructive 변화 범위 명확.

- [ ] **3A-1** `infra/main.tf` 에 private subnet `aws_subnet.private` (10.0.2.0/24, AZ-a) + `aws_route_table.private`(IGW 없음, 0.0.0.0/0 라우트 미설정) + association 추가.
  - 검증: `terraform validate` 통과.
- [ ] **3A-2** `infra/ec2.tf` 에서 `aws_instance.main` 와 그 SG·IAM 을 다음과 같이 분리.
  - `aws_security_group.app`: ingress `:50051` ← `var.endpoint_cidr`, `:8000` ← `var.admin_cidr`. egress 0.0.0.0/0(Bedrock/S3/Dynamo 호출).
  - `aws_security_group.mcp`: ingress `:8080` ← `aws_security_group.lambda.id`(SG-as-source). egress 0.0.0.0/0(KMS/S3 호출).
  - `aws_iam_role.app` + `aws_iam_role_policy.app`: Bedrock(`bedrock-agent-runtime:InvokeAgent`, `bedrock:InvokeModel`), DynamoDB(events/settings R/W), `bedrock-agent:UpdateAgent`(SaaS prompt 편집용).
  - `aws_iam_role.mcp` + `aws_iam_role_policy.mcp`: `kms:Decrypt`+`kms:GenerateDataKey` (CMK ARN), S3 GetObject (encrypted-code), S3 PutObject+DeleteObject+GetObject+ListBucket (kb-staging).
  - 두 Role 모두 `arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore` attachment + `arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy` attachment.
  - `aws_instance.app` (t3.micro, public subnet, app-sg, app-role profile, user_data = userdata-app.sh.tpl).
  - `aws_instance.mcp` (t3.small, public subnet, mcp-sg, mcp-role profile, user_data = userdata-mcp.sh.tpl).
  - `output "app_public_ip"`, `output "mcp_public_ip"`, `output "mcp_private_ip"`, `output "saas_url"`.
  - 검증: `terraform validate` 통과, `terraform plan -no-color | grep -c "will be created"` 가 충분한 수.
- [ ] **3A-3** `infra/kms.tf` 의 `EC2Decrypt` Sid principal 을 `aws_iam_role.mcp.arn` 으로 교체.
- [ ] **3A-4** `infra/s3.tf` encrypted-code 정책: mcp-role 만 GetObject. kb-staging 정책: bedrock-agent-role(GetObject) + mcp-role(전체 RW).
- [ ] **3A-5** `infra/lambda.tf`:
  - `aws_security_group.lambda`: egress `:8080` → `aws_security_group.mcp.id`(SG-as-target). ingress 없음.
  - Lambda 에 `vpc_config { subnet_ids = [aws_subnet.private.id], security_group_ids = [aws_security_group.lambda.id] }`.
  - `aws_iam_role_policy_attachment` 로 `AWSLambdaVPCAccessExecutionRole` 부착.
  - `MCP_SERVER_URL = "http://${aws_instance.mcp.private_ip}:8080"`.
- [ ] **3A-6** `infra/code_dist.tf` 신설.
  - `data "archive_file" "code"` type=zip, `source_dir = "${path.module}/.."`, `excludes = [".venv", "__pycache__", ".pytest_cache", "tests", "infra", "scripts", "encrypted", "sample_project", "lambda/*.zip"]`.
  - `aws_s3_object` 로 zip 업로드: `bucket = aws_s3_bucket.encrypted_code.id`, `key = "_dist/code-${data.archive_file.code.output_base64sha256}.zip"`, `source = data.archive_file.code.output_path`.
  - `output "code_zip_s3_uri"`.
- [ ] **3A-7** `infra/bedrock.tf` 의 `aws_bedrockagent_agent` 주석 해제.
  - `aws_bedrockagent_agent.inspector`: foundation_model = `anthropic.claude-haiku-20240307-v1:0`, instruction = `file("${path.module}/bedrock_system_prompt.txt")`.
  - `aws_bedrockagent_agent_action_group.decrypt_and_stage`: agent_id = inspector.id, function schema 정의(`function_schema { functions { name = "decrypt_and_stage", parameters = { project_id = { type = "string", required = true } } } }`), action_group_executor.lambda = lambda function arn.
  - `aws_bedrockagent_agent_alias.live`: agent_id = inspector.id, name = "live".
  - output `bedrock_agent_id`, `bedrock_agent_alias_id`.
- [ ] **3A-8** `aws_instance.app` 의 user_data 에 `BEDROCK_AGENT_ID`, `BEDROCK_AGENT_ALIAS_ID` 환경변수 자동 주입(`templatefile` vars 추가). MCP-EC2 user_data 에는 미주입.

**Phase 3A Gate**: `terraform validate` + `terraform plan` 성공. 새 리소스 개수와 삭제 대상(기존 `aws_instance.main`, 기존 SG, 기존 IAM Role) 이 의도와 일치.

---

### Phase 3B — Userdata 두 개 분리 작성

**목적**: 부트스트랩이 끝까지 실행되어 systemd 서비스가 active.

- [ ] **3B-1** `infra/userdata-app.sh.tpl` 작성.
  ```sh
  #!/usr/bin/env bash
  set -eux  # -x 로 모든 줄을 cloud-init-output.log 에 기록
  exec > /var/log/agentbox-userdata.log 2>&1

  PROJECT="${project}"; REGION="${region}"
  ADMIN_TOKEN="${admin_token}"; CODE_S3_URI="${code_s3_uri}"
  BEDROCK_AGENT_ID="${bedrock_agent_id}"; BEDROCK_AGENT_ALIAS_ID="${bedrock_agent_alias_id}"

  apt-get update -qq
  apt-get install -y python3.11 python3.11-venv python3-pip git unzip awscli amazon-cloudwatch-agent

  mkdir -p /opt/agentbox/logs
  aws s3 cp "$CODE_S3_URI" /tmp/code.zip --region "$REGION"
  unzip -q -o /tmp/code.zip -d /opt/agentbox
  chown -R ubuntu:ubuntu /opt/agentbox

  cd /opt/agentbox
  python3.11 -m venv venv
  source venv/bin/activate
  pip install --quiet grpcio protobuf fastapi uvicorn boto3 pydantic loguru pyyaml \
      sentence-transformers numpy requests
  cat > /opt/agentbox/.env <<EOF
  AWS_REGION=$REGION
  PROJECT_NAME=$PROJECT
  ADMIN_TOKEN=$ADMIN_TOKEN
  GRPC_CERTS_DIR=/opt/agentbox/certs/grpc
  BEDROCK_AGENT_ID=$BEDROCK_AGENT_ID
  BEDROCK_AGENT_ALIAS_ID=$BEDROCK_AGENT_ALIAS_ID
  MCP_SERVER_URL=http://${mcp_private_ip}:8080
  EOF

  # systemd units (agentbox-grpc, agentbox-saas) - same as before, minus mcp.
  # (구체 unit 파일은 본 plan §3B-2 와 동일 패턴.)

  amazon-cloudwatch-agent-ctl -a fetch-config \
    -m ec2 -c ssm:/agentbox/cloudwatch-agent-config -s
  systemctl daemon-reload
  systemctl enable agentbox-grpc agentbox-saas
  systemctl start  agentbox-grpc agentbox-saas
  ```
  - 검증(배포 후): SSM 로 `systemctl is-active agentbox-grpc agentbox-saas` 두 줄 모두 `active`.
- [ ] **3B-2** `infra/userdata-mcp.sh.tpl` 작성. 위와 동일 패턴이되:
  - `apt-get install -y python3.11 python3.11-venv python3-pip git unzip awscli amazon-cloudwatch-agent` (sops 제외).
  - sops 별도 다운로드: `curl -fsSL https://github.com/getsops/sops/releases/download/v3.12.2/sops-v3.12.2.linux.amd64 -o /usr/local/bin/sops && chmod +x /usr/local/bin/sops`.
  - pip 의존: `boto3 fastapi uvicorn pydantic loguru` (sentence-transformers 불필요).
  - systemd unit 1개: `agentbox-mcp` (ExecStart `python -m ec2.mcp_server.server`, MCP_PORT=8080).
  - 검증: `systemctl is-active agentbox-mcp` = `active`.

**Phase 3B Gate**: 두 userdata 가 lint(`bash -n`) 통과. 변수 치환 placeholder 가 templatefile 인자와 일치(`project, region, admin_token, code_s3_uri, bedrock_agent_id, bedrock_agent_alias_id, mcp_private_ip`).

---

### Phase 3C — 코드 변경(누락 수정 3건)

> Plan 의 §3 매트릭스에 정의된 application code 수정. 모두 단위 테스트로 커버한다.

- [ ] **3C-1** `ec2/grpc_server/server.py` `_invoke_bedrock_agent` 수정.
  - 함수 끝에 토큰 추정값을 계산: `tokens_used = sum(len(c) for c in chunks) // 4 + len(prompt) // 4` (대략 4 char/token).
  - `_increment_token_count(tokens_used)` 호출.
  - 함수 반환은 그대로 `(verdict, reasons)`.
  - 검증: `tests/unit/test_token_counter.py` 통과.
- [ ] **3C-2** `ec2/grpc_server/server.py` `Inspect` 메서드의 Bedrock 분기 종료 후(verdict 결정 후, `_record_event` 전):
  ```python
  try:
      requests.delete(
          f"{_MCP_SERVER_URL}/mcp/cleanup/{event_id}",
          headers={"Authorization": f"Bearer {os.environ['ADMIN_TOKEN']}"},
          timeout=5,
      )
  except Exception as exc:
      logger.warning("mcp_cleanup_failed", event_id=event_id, error=str(exc))
  ```
  - 검증: `tests/unit/test_grpc_cleanup_call.py` 통과(responses 라이브러리로 HTTP mock).
- [ ] **3C-3** `ec2/mcp_server/server.py` 수정.
  - `MCP_PORT` default 8443 → 8080.
  - `@app.get("/healthz")`: 인증 없이 `{"ok": True, "service": "mcp"}` 반환.
  - 검증: `tests/unit/test_mcp_server.py::test_healthz_no_auth` 통과.

**Phase 3C Gate**: 3개 단위 테스트 모두 PASS. `git diff` 가 위 3건 외 변경 없음.

---

### Phase 3D — 단위 테스트 추가 (moto + pytest)

> moto 5.x 의 `@mock_aws` 컨텍스트 매니저로 KMS/S3/DynamoDB 통합 mock.

- [ ] **3D-1** `requirements-dev.txt` 또는 `pyproject.toml [project.optional-dependencies] dev` 에 `moto[all]>=5,<6`, `responses>=0.24`, `pytest-mock>=3` 추가.
- [ ] **3D-2** `tests/conftest.py` 에 fixture 추가:
  - `aws_credentials_env`: `AWS_ACCESS_KEY_ID=test`, `AWS_SECRET_ACCESS_KEY=test`, `AWS_DEFAULT_REGION=us-east-1` 환경변수 (autouse).
  - `mock_aws_stack`: `with mock_aws(): yield` 컨텍스트 + KMS CMK 생성 + S3 두 버킷 생성 + DynamoDB events/settings 테이블 생성.
- [ ] **3D-3** `tests/unit/test_mcp_server.py`:
  - `test_decrypt_and_stage_happy_path`: encrypted-code 에 SOPS-shaped 더미 파일 업로드 → MCP 서버에 `subprocess.run` 을 mock 하여 평문 반환 → kb-staging put 확인.
  - `test_decrypt_no_files_404`: 빈 prefix → 404.
  - `test_cleanup_deletes_objects`: kb-staging 에 객체 3개 → DELETE → empty.
  - `test_admin_token_required`: 잘못된 token → 401.
  - `test_healthz_no_auth`: 401 없이 200.
- [ ] **3D-4** `tests/unit/test_lambda_mcp_bridge.py`:
  - `responses` 로 `http://mcp:8080/mcp/decrypt_and_stage` mock.
  - Bedrock event payload(`messageVersion=1.0, parameters=[{name:project_id,value:default}]`) 로 handler 호출.
  - 응답 JSON 의 `response.functionResponse.responseBody.TEXT.body` 가 dict serialize 인지 검증.
  - `test_authorization_header_present`: 호출 시 Bearer 토큰 헤더 검증.
- [ ] **3D-5** `tests/unit/test_grpc_cleanup_call.py`:
  - InspectorServicer 인스턴스 생성. `_invoke_bedrock_agent` mock(verdict ALLOW). `_record_event` mock. responses 로 `DELETE http://.../mcp/cleanup/{event_id}` 등록.
  - InspectRequest 로 호출. responses.calls 길이 1 확인.
- [ ] **3D-6** `tests/unit/test_token_counter.py`:
  - moto DynamoDB. `_invoke_bedrock_agent` 호출 후 `bedrock_tokens_YYYY-MM-DD` 항목의 `value` 가 양수인지 검증.

**Phase 3D Gate**: `pytest tests/unit -v` 100% PASS. 라인 커버리지 신규 코드 ≥ 90 %.

---

### Phase 3E — 통합 테스트 추가

- [ ] **3E-1** `tests/integration/test_mcp_e2e.py`:
  - moto KMS+S3 환경. 실제 `sops` 바이너리(이미 ~/.local/bin 에 존재) 로 암호화한 파일을 S3 에 업로드.
  - MCP 서버를 FastAPI TestClient 로 in-process 부팅. `/mcp/decrypt_and_stage` 호출 → `/mcp/cleanup` 호출 → kb-staging 비어있는지 확인.
  - 환경변수: `MCP_PORT=auto`, `ADMIN_TOKEN=test-token`.
- [ ] **3E-2** `tests/integration/test_lambda_to_mcp.py`:
  - MCP 서버를 FastAPI TestClient 로 띄우고 그 base_url 을 `MCP_SERVER_URL` 로 set.
  - `lambda.mcp_bridge.handler(event, ctx)` 직접 호출 → MCP 의 kb-staging put 확인.
  - 검증 핵심: Bedrock Action Group 응답 포맷(`response.actionGroup`, `response.function`, `responseBody.TEXT.body`) 정확.
- [ ] **3E-3** `tests/integration/test_grpc_full_flow.py`:
  - moto stack + responses 로 MCP cleanup endpoint mock + Bedrock invoke_agent unittest.mock.
  - mTLS 없이 insecure_port. clean prompt → ALLOW + cleanup 호출 + 토큰 카운터 증가 동시 검증.

**Phase 3E Gate**: `pytest tests/integration -v` (단, `-m "not aws"`) 100% PASS.

---

### Phase 3F — `scripts/deploy.sh` 통합 + 헬스체크

> deploy.sh 가 다음 6단계를 순차 수행. 어느 단계에서 실패해도 명확한 에러 출력 후 stop.

- [ ] **3F-1** deploy.sh 단계:
  1. `terraform -chdir=infra init -upgrade=false`
  2. KMS 키 reuse 가드(현행 유지) + `aws kms describe-key` 결과의 `KeyState != Enabled` 면 abort + 안내 문구.
  3. `terraform -chdir=infra apply "$@"`
  4. terraform output → 변수 추출 (`app_public_ip`, `mcp_public_ip`, `mcp_private_ip`, `app_instance_id`, `mcp_instance_id`, `kms_key_arn` 등).
  5. `.sops.yaml` 갱신, `gen_mtls_certs.sh` 호출(이미 있으면 skip).
  6. `.env.endpoint` 작성 (`EC2_GRPC_HOST=app_public_ip` 만, MCP IP 는 endpoint 가 사용 안 함).
  7. SSM 등록 폴링(루프 18회 × 10초). 두 인스턴스 모두 `Online` 도달 시까지.
  8. SSM Send-Command (1회) 로 두 인스턴스에 cert/CA 푸시 + systemctl restart.
  9. SSM 로 `systemctl is-active` 확인. app 은 grpc/saas 둘 다 active, mcp 는 active 일 때 OK.
  10. SSM 로 `curl -sf http://localhost:8080/healthz` (mcp), `ss -tlnp | grep :50051` (app) 확인.
  11. 모두 통과 시 "Deployment OK" 출력 + `saas_url`.
- [ ] **3F-2** 실패 처리:
  - 7단계 timeout → "SSM 등록 실패. `aws ssm describe-instance-information` 으로 점검" 안내.
  - 9단계에서 inactive → "journalctl -u <service>" 명령을 SSM 로 자동 실행해서 마지막 30줄 출력.
- [ ] **3F-3** `scripts/post_deploy.sh` 삭제.

**Phase 3F Gate**: 로컬에서 deploy.sh 가 lint(`bash -n`) 통과 + 더미 mode (DRY_RUN=1 환경변수) 로 syntax 통과.

---

### Phase 3G — 배포 + 실 AWS 검증 (사용자 직접 실행 단계)

> Claude 는 §3F 까지 완료 후 멈춘다. 이하 단계는 사용자가 본인 손으로 실행하며 결과를 보고한다.

- [ ] **3G-1** **사전 조건**: us-east-1 에서 Bedrock model access (Anthropic Claude Haiku) 승인 완료. 미승인이면 `terraform apply` 가 `aws_bedrockagent_agent` 에서 실패. 사용자 확인 후 진행.
- [ ] **3G-2** `git status` 깨끗(이전 작업 잔여물 없음). 필요 시 `git stash`.
- [ ] **3G-3** `./scripts/deploy.sh -auto-approve` 실행. 정상 종료 확인.
- [ ] **3G-4** `./scripts/test_lifecycle_45.sh` 실행. ALL PASSED 확인.
- [ ] **3G-5** Endpoint 측 통합:
  - `source .env.endpoint`
  - WSL 에서 mitmproxy + addon 가동(Task-1 흐름) 후 `claude --print "..."` 실행.
  - SaaS `${SAAS_URL}/audit` 에서 이벤트 row 확인.
- [ ] **3G-6** 비용 가드 동작 확인:
  - DynamoDB `agentbox-settings` 테이블에 `bedrock_tokens_<YYYY-MM-DD>` 항목 존재 + `value > 0`.

**Phase 3G Gate**: 라이프사이클 4-5 자동 테스트 + 1회 실 prompt 검사 round-trip + 토큰 카운터 동작.

---

## 5. 비기능 요구사항 (Task-2 §5 에서 변경된 부분)

| 영역 | 목표 | 변경 |
|---|---|---|
| 지연 | p50 < 200ms, p95 < 500ms | Lambda VPC ENI 추가로 cold start 1~3s 발생 가능. 첫 호출 외 ≤ 500ms 유지 가능. |
| 보안 | KMS Decrypt 권한이 mcp-EC2 IAM 만, app-EC2 IAM 은 Bedrock/DDB 만 | 강화 |
| 가용성 | 두 EC2 모두 단일 인스턴스 PoC. 어느 한 쪽 다운 시 mitmproxy timeout → BLOCK(안전 차단) | 변경 없음 |
| 비용 | Capex: $8.35(t3.micro app) + $16.70(t3.small mcp) + $1(KMS) ≈ **$26/월** | NAT 없으므로 +$8 정도만 증가 |

---

## 6. 리스크 및 결정 보류 (Task-2 §6 + 신규)

| ID | 항목 | 결정 |
|---|---|---|
| R1 | Bedrock 모델 액세스 사전 승인 | 사용자 책임. Phase 3G-1 에서 검증. |
| R2 | Lambda cold start 영향 | 첫 호출 1~3s 추가. 단일 prompt 검사라 ALLOW 시 사용자가 인지 못 함. p95 측정 후 판단. |
| R3 | sentence-transformers 메모리 | t3.micro 1GB RAM 에서 모델 로드 시 ~500MB. 동시 inference 부하 시 OOM 위험. 단일 사용자 PoC 라 일단 진행. |
| R4 | 코드 변경 시 EC2 재생성 | 사용자 결정: 허용. 매 apply 마다 새 IP. deploy.sh 가 admin_cidr 갱신은 자동화하지 **않음** (terraform.tfvars 의 admin_cidr 는 사용자 머신 IP 라 변하지 않음). |
| R5 | private subnet AZ 단일 | Lambda ENI 가 단일 AZ. 해당 AZ 장애 시 Lambda 호출 실패. PoC 허용. |
| R6 | Bedrock Agent prepare 시간 | `aws_bedrockagent_agent_alias` 가 prepare 후 alias 만드는 데 1~2분 소요. terraform apply 가 이를 기다리는지 확인 필요(테라폼 provider가 핸들링). |
| R7 | sops binary 다운로드 의존 | userdata 가 GitHub release 에 의존. github.com 다운로드 실패 시 부트 실패. 우회: zip 안에 sops binary 같이 패키징하는 옵션도 가능(향후 개선). |

---

## 7. 테스트 전략

| 레벨 | 도구 | 대상 | 위치 |
|---|---|---|---|
| Unit | pytest, moto, responses, unittest.mock | grpc_server 내부 함수, mcp_server 핸들러, lambda handler, rules engine, semantic fallback | `tests/unit/` |
| Integration (mock) | pytest, moto, FastAPI TestClient | MCP E2E (KMS+S3), Lambda↔MCP, grpc full flow | `tests/integration/` |
| Integration (real) | pytest with `@pytest.mark.aws`, real boto3, real Lambda invoke | `test_lifecycle_45.sh` 와 동일 시나리오의 pytest 버전 | `tests/aws/` (선택) |
| Bash | `bash -n`, shellcheck (선택) | deploy.sh, gen_mtls_certs.sh | CI 단계 |
| Terraform | `terraform validate`, `terraform plan` | infra/ | local |

CI 명령:
```bash
pytest tests/unit tests/integration -m "not aws" -v --cov=ec2 --cov=lambda --cov-report=term-missing
terraform -chdir=infra validate
bash -n scripts/deploy.sh
```

실 AWS 통합:
```bash
pytest tests/aws -m aws -v
```

---

## 8. TODO 마스터 체크리스트 (재실행용)

### Phase 3A — Terraform 코드 분리
- [x] 3A-1 `infra/main.tf` private subnet 추가
- [x] 3A-2 `infra/ec2.tf` 두 인스턴스/SG/IAM 으로 분리
- [x] 3A-3 `infra/kms.tf` EC2Decrypt principal → mcp-role
- [ ] 3A-4 `infra/s3.tf` 정책 mcp-role 한정
- [ ] 3A-5 `infra/lambda.tf` VPC 진입 + private IP URL
- [ ] 3A-6 `infra/code_dist.tf` 신설 (zip + S3 업로드)
- [ ] 3A-7 `infra/bedrock.tf` Agent + ActionGroup + Alias 활성화
- [ ] 3A-8 app userdata 에 BEDROCK_AGENT_ID/ALIAS_ID 주입

### Phase 3B — Userdata 분리
- [ ] 3B-1 `infra/userdata-app.sh.tpl` 작성 (sops 미포함)
- [ ] 3B-2 `infra/userdata-mcp.sh.tpl` 작성 (sops GitHub release)
- [ ] 3B-3 기존 `infra/userdata.sh.tpl` 삭제

### Phase 3C — 코드 누락 수정
- [ ] 3C-1 `_increment_token_count` 호출 추가
- [ ] 3C-2 `/mcp/cleanup` 호출 추가
- [ ] 3C-3 MCP 서버 포트 8080 + `/healthz`

### Phase 3D — 단위 테스트
- [ ] 3D-1 dev 의존성 (moto, responses) 추가
- [ ] 3D-2 conftest fixtures
- [ ] 3D-3 test_mcp_server.py
- [ ] 3D-4 test_lambda_mcp_bridge.py
- [ ] 3D-5 test_grpc_cleanup_call.py
- [ ] 3D-6 test_token_counter.py

### Phase 3E — 통합 테스트
- [ ] 3E-1 test_mcp_e2e.py (실 sops 바이너리)
- [ ] 3E-2 test_lambda_to_mcp.py
- [ ] 3E-3 test_grpc_full_flow.py

### Phase 3F — deploy.sh 통합
- [ ] 3F-1 deploy.sh 11단계 작성
- [ ] 3F-2 실패 안내 분기
- [ ] 3F-3 post_deploy.sh 삭제

### Phase 3G — 사용자 손에서 실행
- [ ] 3G-1 Bedrock model access 승인 확인
- [ ] 3G-2 git status 깨끗
- [ ] 3G-3 deploy.sh 성공
- [ ] 3G-4 test_lifecycle_45.sh ALL PASSED
- [ ] 3G-5 Endpoint round-trip 1회
- [ ] 3G-6 토큰 카운터 row 확인

---

## 9. 재개 프로토콜

1. §8 의 가장 최근 미체크(`- [ ]`) 항목으로 이동.
2. **Phase 3A~3F 의 모든 변경은 git commit 으로 분리** 권장 (`feat(task-3,3A-2): split EC2 into app/mcp` 식). 중단 시 `git log` 로 어디까지 갔는지 자명.
3. Phase 3D/3E 는 idempotent — `pytest` 만 다시 돌리면 된다.
4. Phase 3F 까지 코드만 변경하므로 `terraform apply` 는 사용자 명시 지시 후에만 실행.
5. Phase 3G 가 중간에 실패 시: deploy.sh 의 어느 단계에서 멈췄는지 stdout 보고 → 해당 단계만 재실행. 예: SSM 등록 실패 → 인스턴스 reboot 후 재시도. systemctl inactive → SSM 로 journalctl 확인 후 코드/userdata 수정 → `terraform taint aws_instance.app && terraform apply`.

---

## 10. 코드 수정 금지 — 시작 조건

- 본 문서 사용자 검토 + "Task-3 시작" 명시적 지시 전까지 어떤 파일도 수정 금지.
- 사용자가 검토 중 수정 요청한 항목은 본 문서를 직접 갱신 후 다시 검토 받음.
- 첫 실행 단계는 §8 의 **3A-1**.

---

## 부록 A — 합의된 결정 요약

| 결정 항목 | 값 |
|---|---|
| MCP 인스턴스 타입 | t3.small |
| App 인스턴스 타입 | t3.micro |
| MCP ↔ Lambda 프로토콜 | 평문 HTTP + admin_token (VPC private) |
| MCP 포트 | 8080 (8443 → 8080 변경) |
| Lambda 위치 | VPC private subnet, lambda-sg |
| 누락 수정 범위 | `_increment_token_count` 호출, `/mcp/cleanup` 호출, Bedrock Agent 리소스 자동 생성 |
| EC2 재생성 정책 | user_data 변경 시 자동 재생성(매 apply 마다 새 IP) |
| post_deploy 통합 | `scripts/deploy.sh` 한 파일에 통합 |
| 테스트 모킹 | moto + pytest + responses |
| 새 SaaS URL 변경 | 사용자 동의 |

---

## 부록 B — 용어 정의 (반복 등장)

- **mTLS**: 양방향 TLS. 서버·클라이언트 모두 인증서 제출. gRPC 서버에 적용.
- **SOPS envelope**: SOPS 암호화 결과 JSON. `sops` 키 하위에 KMS 메타데이터 포함. 평문이 아니다.
- **moto**: AWS SDK 호출을 in-memory 로 가짜 처리. `@mock_aws` 데코레이터 또는 `with mock_aws():` 컨텍스트.
- **responses**: `requests` 라이브러리 호출을 mock 하는 라이브러리.
- **archive_file (Terraform)**: 로컬 파일/디렉터리를 zip 으로 묶는 data source. content hash 가 변하면 의존 리소스도 재생성.
- **SG-as-source**: 보안 그룹 인그레스 규칙 source 를 CIDR 대신 다른 SG 의 ID 로 지정. 동일 VPC 내 자원만 매칭.
- **Bedrock Action Group**: Bedrock Agent 가 외부 함수(=Lambda) 를 호출할 수 있게 정의한 함수 집합.
- **`user_data_replace_on_change`**: terraform `aws_instance` 옵션. true 면 user_data 가 바뀔 때 EC2 가 destroy/create.

---
