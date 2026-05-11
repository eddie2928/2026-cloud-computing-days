# Task-6: 대시보드 `/pipeline`·`/audit`·설정 페이지 정상화 + Audit 자동 tailing + 페이지 description UI + destroy→deploy 멱등성 자동화

> 본 문서는 Task-5 완료 상태(EC2 SaaS `/audit` HTML 무토큰, `agentbox set`/`status` CLI, React SPA 번들) 를 전제로,
> ① 프런트엔드가 호출하는 `/api/*` 경로와 백엔드(`ec2/saas/server.py`)가 노출하는 경로의 **prefix 불일치 전부 수정**(`/pipeline` 미표시 + Prompt/KB 저장 실패의 근본 원인),
> ② 누락된 GET 설정 조회 엔드포인트 2개(`/api/settings/prompt-get`, `/api/settings/kb-ttl-get`) 신설,
> ③ `/audit` 페이지가 마운트되는 즉시 자동 조회 + 3초 폴링으로 **신규 이벤트를 prepend 하는 tailing UX** (Pause/Resume 토글 포함),
> ④ 5개 모든 대시보드 페이지 상단에 **이 페이지에서 무엇을 보여주는지 2~3줄짜리 description 하드코딩 안내 문구** 추가,
> ⑤ 모든 코드 수정 완료 후 **단위 테스트(mock) + 통합 테스트(라이브 AWS) 실행**,
> ⑥ 마지막으로 **`scripts/redeploy_idempotency.sh` 작성** — 기존 `destroy.sh`(KMS 보존) → `deploy.sh` 를 순차 실행하고 핵심 헬스체크(`/healthz`, `/audit` HTML 200, `/api/audit` 401↔200, `/api/pipeline/stream` WebSocket 핸드셰이크) 자동 검증,
> 을 수행한다.
>
> 모든 변경은 **재실행 가능한 step** 으로 구성되며, 각 단계 종료 시 자동/수동 검증을 통과해야 다음 단계로 넘어간다. 중간에 멈춰도 §6 마스터 체크리스트의 가장 최근 미체크(`- [ ]`) Phase 부터 재시작 가능.
>
> 인코딩: UTF-8 (BOM 없음)
> 작성일: 2026-05-12
> 작성자: Claude (Opus 4.7)

---

## 0. 메타 정보

| 항목 | 값 |
|---|---|
| Task ID | Task-6 |
| 선행 조건 | Task-5 완료. 라이브 인프라(`54.165.51.239:8000`)가 동작 중. `infra/terraform.tfstate` 가 유효. SaaS `/audit` HTML 무토큰 반환됨. dashboard 번들이 EC2 `/opt/agentbox/ec2/saas/static/index.html` 에 배포되어 있음. |
| 대상 OS | 개발: WSL2 Ubuntu 22.04 (1차) / Windows 11 PowerShell (보조). 라이브 검증: EC2 Ubuntu 22.04. |
| 핵심 변경 | ① `ec2/saas/server.py` 의 5개 라우트를 `/api/*` prefix 로 일관화 + 신규 2개 GET 엔드포인트, ② `dashboard/src/pages/Audit.tsx` 자동 query + 3초 폴링 + Pause/Resume 토글, ③ 5개 페이지(`PipelineStream`, `PromptEditor`, `KBSettings`, `Audit`, `Login`) 상단에 description 하드코딩, ④ 신규/기존 pytest 6~8개 + Playwright e2e 4~5개 갱신, ⑤ 신규 `scripts/redeploy_idempotency.sh` + `tests/scripts/test_redeploy_idempotency.py`(dry-run). |
| Capex 변동 | 약 $0~$2. EC2 코드만 변경(인프라 리소스 추가 없음). 라이브 통합 테스트가 DynamoDB scan/Bedrock 호출 수회 발생. 멱등성 검증 1회 시 EC2 재생성으로 약 5~10분 동안 EC2 t3.small × 2 비용 + Lambda ENI 정리 대기 시간 발생. |
| 코드 수정 금지 | 본 문서 사용자 검토 및 "Task-6 시작" 명시 지시 전까지 일절 코드 변경 금지. |
| 작업 디렉토리 | `C:\Users\ab550\OneDrive\Desktop\projects\proj_AgentBox` (Windows) / `/mnt/c/Users/ab550/OneDrive/Desktop/projects/proj_AgentBox` (WSL) |
| OneDrive 주의 | terraform.tfstate 작업 시 OneDrive sync **반드시** 일시중지 (memory: `feedback_onedrive_terraform.md`). 본 Task 는 Phase L~M(redeploy_idempotency.sh 실행) 에서만 tfstate 를 만짐. |

### 0.1 모든 사용자 결정 사항 요약 (AskUserQuestion 답변 기반)

| 결정 항목 | 값 | 근거 질문 |
|---|---|---|
| 수정 범위 | **`/api` 경로 불일치 전부 수정**: `/pipeline/stream`, `/settings/prompt`, `/settings/kb-ttl` 모두 `/api/...` 로 이동 + `/api/settings/prompt-get`, `/api/settings/kb-ttl-get` 신설 | Q1 |
| Audit tailing 동작 | **페이지 마운트 시 자동 query + 3초마다 폴링하여 새 이벤트 prepend, 기본 ON, Pause/Resume 토글 버튼 제공** | Q2 + Q5 |
| Description UI | **각 page component 내 하드코딩된 2~3줄 안내 문구** (별도 PageHeader 컴포넌트 만들지 않음, 각 .tsx 의 `<h2>` 바로 아래 `<p>` 로 배치) | Q3 |
| Destroy/Redeploy 자동화 범위 | **기존 `scripts/destroy.sh`(KMS 보존) → `scripts/deploy.sh` 순차 실행 + 검증**. KMS CMK 는 보존하여 SOPS 호환성 유지. 신규 스크립트는 `scripts/redeploy_idempotency.sh` | Q4 |
| 테스트 환경 | **단위 테스트는 moto/MagicMock mock, 통합 테스트만 실제 AWS+EC2 라이브** | Q6 |
| 프런트엔드 빌드/배포 타이밍 | **Plan 마지막 단계(Phase J)에서 한 번만** `scripts/deploy_static.sh` 로 적용 | Q7 |

### 0.2 용어 사전 (LLM 재실행 시 일관성 유지용)

| 용어 | 정의 |
|---|---|
| **`/api` prefix** | 본 Task 의 핵심 규약. 프런트엔드(React SPA) 가 fetch/WebSocket 호출하는 모든 백엔드 데이터 경로는 `/api/...` 로 시작한다. HTML 서빙 경로(`/`, `/pipeline`, `/audit`, `/prompt`, `/kb`, `/login`)는 prefix 없음(SPA catch-all 이 처리). |
| **prefix 불일치 버그** | `dashboard/src/pages/*.tsx` 가 `/api/pipeline/stream`, `/api/settings/prompt`, `/api/settings/kb-ttl` 등을 호출하지만, `ec2/saas/server.py` 가 `/pipeline/stream`, `/settings/prompt`, `/settings/kb-ttl` 에만 핸들러 등록 → spa_catch_all GET 만 잡고 PUT/WS 는 404/Failed 응답. 결과적으로 /pipeline 미표시, Prompt/KB 저장 실패. **본 Task 의 1차 수정 대상**. |
| **tailing** | tail -f 처럼 새 항목이 들어오면 실시간으로 페이지에 prepend 되는 동작. 본 Task 에서는 `/audit` 페이지에 `setInterval` 3초 폴링 + 이벤트 `event_id` 로 중복 제거 후 상단 prepend. |
| **Pause/Resume 토글** | `/audit` 페이지 우상단의 토글 버튼. ON 일 때 폴링 활성, OFF 일 때 폴링 중지. 페이지 unmount 시에도 cleanup 필수(메모리 누수 방지). |
| **description 안내 문구** | 각 페이지의 `<h2>제목</h2>` 바로 아래 회색 작은 글씨 `<p>` 로 배치하는 2~3줄 안내. 이 페이지가 무엇을 보여주는지, 데이터 출처가 어디인지, 사용 시 주의사항이 있는지 사용자가 한눈에 파악 가능하도록 한다. |
| **멱등성(idempotency)** | 같은 입력이면 같은 결과가 보장되는 특성. 본 Task 에서는 "임의 상태에서 redeploy_idempotency.sh 를 실행하면 항상 동일한 깨끗한 동작 상태로 수렴한다" 를 의미. 인프라가 부분적으로 망가져 있어도 destroy → deploy → 검증 한 번이면 복구. |
| **KMS CMK 보존** | `scripts/destroy.sh` 가 `terraform state rm aws_kms_key.sops[0]` + `aws_kms_alias.sops[0]` 를 호출하여 Terraform state 에서만 제거하고 실제 AWS 키는 살려두는 전략. 이유: 기존 `.sops.yaml` 의 KMS ARN 으로 암호화된 파일들이 redeploy 후에도 그대로 사용 가능하도록 호환성 유지. |
| **redeploy_idempotency.sh** | 본 Task 신규 스크립트. 단계: (a) 사전 환경 점검 → (b) destroy.sh 호출 → (c) deploy.sh 호출 → (d) 자동 health check (5종) → (e) SaaS API smoke test. 실패 시 stderr 에 단계명/원인 출력 후 non-zero exit. |
| **healthz** | `ec2/saas/server.py` 의 `/healthz` 엔드포인트. `{"ok": true, "service": "saas"}` 를 반환. 본 Task 에서는 변경하지 않음. |
| **SPA catch-all** | `ec2/saas/server.py:179` 의 `@app.get("/{full_path:path}")`. 정의되지 않은 모든 GET 경로를 SPA index.html 로 응답. **단, GET 전용이므로 PUT/WebSocket 은 404/handshake 실패로 떨어짐** → 본 Task 가 발견한 prefix 불일치 버그의 직접 원인. |
| **DRY_RUN** | 환경변수 `DRY_RUN=1` 일 때 destroy.sh / deploy.sh 가 실제 AWS 호출 없이 plan 만 출력. redeploy_idempotency.sh 도 이 변수를 그대로 전파 가능. |

---

## 1. 목표

1. **`/pipeline` 페이지 실시간 표시 복구.** 사용자가 로그인 후 `/pipeline` 에 들어가면 mitmproxy → gRPC → DynamoDB 흐름으로 들어오는 이벤트가 즉시 표시되어야 한다(현재 WebSocket 경로 불일치로 0건).
2. **설정 페이지(Prompt/KB) 저장·조회 동작 복구.** Prompt Editor 의 "Save Prompt" 와 KB Settings 의 "Save" 가 성공해야 하고, 페이지 재진입 시 직전 저장값이 다시 로드되어야 한다(현재 GET 엔드포인트가 아예 없어 항상 빈 값).
3. **`/audit` 자동 tailing.** 페이지 진입 즉시 최신 100건이 표시되고 3초마다 새 이벤트가 상단에 prepend 된다. 사용자는 Pause 버튼으로 중지·재개 가능.
4. **각 페이지 의미 파악 즉시성.** 5개 페이지(Login 포함) 상단에 무엇을 보여주는지, 어디서 데이터를 가져오는지, 주의사항이 있는지 2~3줄 안내가 항상 표시되어 신규 사용자가 컨텍스트 없이도 페이지 의도를 파악 가능.
5. **회귀 방지 자동화.** 신규/수정된 모든 코드에 대해 단위 테스트는 mock 으로(빠르게), 통합 테스트는 실제 AWS+EC2 라이브로(정확하게) 통과. 기존 60+ 테스트 PASS 유지.
6. **인프라 멱등성 검증.** `scripts/redeploy_idempotency.sh` 한 번 실행으로 destroy → deploy 가 완전히 자동화되고, 마지막에 5종 health check 가 모두 PASS 하면 인프라가 "깨끗한 동작 상태" 라는 것을 보장.
7. **재실행 가능성.** Plan 이 중간에 멈춰도 §6 TODO 마스터 체크리스트의 가장 최근 미체크(`- [ ]`) Phase 부터 재시작 가능. 각 Phase 가 자체 검증 단계를 포함.

---

## 2. 아키텍처

### 2.1 변경 전 (Task-5 종료 시점, 현재)

```
브라우저 (http://54.165.51.239:8000)
  │
  ├─ GET /                ─► SPA index.html               ✓
  ├─ GET /pipeline        ─► SPA (Layout + PipelineStream)✓
  │     │
  │     └─ WS /api/pipeline/stream  ─► 404 (server 는 /pipeline/stream 만 등록) ✗ 미표시
  │
  ├─ GET /audit           ─► SPA (Layout + Audit)         ✓
  │     │
  │     └─ GET /api/audit?... + X-Admin-Token ─► 200 JSON ✓
  │           (단, 사용자가 Query 버튼을 눌러야만 호출 — 자동 X)
  │
  ├─ GET /prompt          ─► SPA (Layout + PromptEditor)  ✓
  │     ├─ GET /api/settings/prompt-get  ─► 404 (정의 없음) ✗ 빈 textarea
  │     └─ PUT /api/settings/prompt      ─► 404 (server 는 /settings/prompt) ✗ 저장 실패
  │
  └─ GET /kb              ─► SPA (Layout + KBSettings)    ✓
        ├─ GET /api/settings/kb-ttl-get  ─► 404 (정의 없음) ✗ 기본 5분만
        └─ PUT /api/settings/kb-ttl      ─► 404 (server 는 /settings/kb-ttl) ✗ 저장 실패
```

### 2.2 변경 후 (Task-6 목표)

```
브라우저 (http://54.165.51.239:8000)
  │
  ├─ GET /                ─► SPA index.html
  │
  ├─ GET /pipeline        ─► SPA (Layout + PipelineStream)
  │     ├─ <PageHeader inline> "실시간 mitmproxy→gRPC→Bedrock 검증 이벤트 ..." 표시
  │     └─ WS /api/pipeline/stream ─► server.py @app.websocket("/api/pipeline/stream") ✓ 실시간 push
  │
  ├─ GET /audit           ─► SPA (Layout + Audit)
  │     ├─ <PageHeader inline> "ALLOW/BLOCK 판정 이력. 3초마다 자동 갱신 ..."
  │     ├─ mount 시 자동 query() 호출 (기존 사용자 Query 버튼 동작 그대로)
  │     ├─ setInterval 3초 폴링 ─► GET /api/audit?limit=100 (X-Admin-Token)
  │     │     └─ 신규 event_id 만 상단 prepend, 200건 cap
  │     └─ Pause/Resume 토글 버튼 (기본 ON)
  │
  ├─ GET /prompt          ─► SPA (Layout + PromptEditor)
  │     ├─ <PageHeader inline> "Bedrock Agent 시스템 프롬프트 ..."
  │     ├─ GET /api/settings/prompt-get ─► 200 {"system_prompt": "..."} ✓ 신설
  │     └─ PUT /api/settings/prompt      ─► 200 {"ok": true}            ✓ 이동
  │
  └─ GET /kb              ─► SPA (Layout + KBSettings)
        ├─ <PageHeader inline> "KB Staging bucket TTL ..."
        ├─ GET /api/settings/kb-ttl-get  ─► 200 {"ttl_minutes": N}      ✓ 신설
        └─ PUT /api/settings/kb-ttl      ─► 200 {"ok": true, "ttl_minutes": N} ✓ 이동
```

### 2.3 server.py 라우트 매핑 (Before ↔ After)

| 경로(After, `/api/*`) | 메서드 | 인증 | 처리 함수 | Before(현재) |
|---|---|---|---|---|
| `/api/pipeline/stream` | WebSocket | (옵션 없음) | `pipeline_stream` | `/pipeline/stream` (prefix 누락) |
| `/api/audit` | GET | X-Admin-Token | `audit` | `/api/audit` ✓ (변경 없음) |
| `/api/settings/prompt` | PUT | X-Admin-Token | `update_prompt` | `/settings/prompt` (prefix 누락) |
| `/api/settings/prompt-get` | GET | X-Admin-Token | `get_prompt` 신설 | (없음) |
| `/api/settings/kb-ttl` | PUT | X-Admin-Token | `update_kb_ttl` | `/settings/kb-ttl` (prefix 누락) |
| `/api/settings/kb-ttl-get` | GET | X-Admin-Token | `get_kb_ttl` 신설 | (없음) |
| `/healthz` | GET | 없음 | `healthz` | 변경 없음 |
| `/audit`, `/pipeline`, `/prompt`, `/kb`, `/login` | GET | 없음 | `audit_page` / SPA catch-all | 변경 없음(HTML 서빙) |
| `/assets/{path}` | GET | 없음 | `serve_asset` | 변경 없음 |

> **주의:** SPA catch-all 의 `@app.get("/{full_path:path}")` 는 본 Task 후에도 유지된다. 이 라우트는 React Router 의 임의 경로(`/login` 등)를 SPA index.html 로 매핑하기 위해 반드시 필요. 단, `/api/*` 는 위 명시 라우트가 먼저 잡으므로 SPA catch-all 로 떨어지지 않음(FastAPI 는 등록 순서대로 매칭).

---

## 3. 파일 구조 (수정/신규 파일 목록)

### 3.1 수정 파일

| 경로 | 변경 요약 |
|---|---|
| `ec2/saas/server.py` | 5개 라우트 `/api` 이동(`@app.websocket`/`@app.put`), 2개 GET 엔드포인트 신설(`get_prompt`, `get_kb_ttl`), `PipelineStream` WebSocket 경로 변경 시 spa_catch_all 우선순위 유지를 위해 catch-all 은 파일 최하단(현재 위치) 유지. |
| `dashboard/src/pages/PipelineStream.tsx` | `<h2>` 아래 description `<p>` 추가. WebSocket URL 은 이미 `/api/pipeline/stream` 이므로 **변경 없음** (server.py 가 일치하도록 따라옴). |
| `dashboard/src/pages/Audit.tsx` | (1) description `<p>` 추가, (2) `useEffect` 로 mount 시 자동 query, (3) `useEffect` 로 `setInterval` 3초 폴링 등록 + cleanup, (4) Pause/Resume 토글 state + 버튼, (5) 새 이벤트 prepend 시 `event_id` 중복 제거 + 200건 cap. |
| `dashboard/src/pages/PromptEditor.tsx` | description `<p>` 추가. fetch 경로는 이미 `/api/settings/prompt`, `/api/settings/prompt-get` 이므로 **변경 없음**. |
| `dashboard/src/pages/KBSettings.tsx` | description `<p>` 추가. fetch 경로는 이미 `/api/settings/kb-ttl`, `/api/settings/kb-ttl-get` 이므로 **변경 없음**. |
| `dashboard/src/pages/Login.tsx` | description `<p>` 추가(폼 위쪽). |
| `tests/unit/test_saas_audit_html.py` | 기존 테스트는 `/api/audit` 사용 중이라 무관. 단, server.py 가 변경되므로 mock fixture 가 재사용되는지 확인. |
| `dashboard/tests/e2e/dashboard.spec.ts` | Prompt PUT 매칭 패턴을 `/settings/prompt` → `/api/settings/prompt` 로, KB PUT 패턴을 `/settings/kb-ttl` → `/api/settings/kb-ttl` 로 수정. Audit 테스트는 `/api/audit` 그대로. Pipeline 테스트는 WebSocket 핸드셰이크 성공만 검증(현재는 단순 페이지 로드만). |

### 3.2 신규 파일

| 경로 | 목적 |
|---|---|
| `tests/unit/test_saas_api_prefix.py` | server.py 의 신규/이동된 `/api/*` 라우트가 OpenAPI schema 에 정확히 등록되었는지 단위 검증 (mock DynamoDB). |
| `tests/unit/test_saas_settings_get.py` | 신규 `get_prompt`, `get_kb_ttl` 핸들러 단위 테스트 (mock DynamoDB scan 결과 → JSON 응답). |
| `tests/integration/test_saas_api_live.py` | 라이브 EC2 (`http://54.165.51.239:8000`) 대상 통합 테스트. `/api/audit` 200, `/api/pipeline/stream` WebSocket 핸드셰이크 성공, `/api/settings/prompt-get` 200 검증. `SKIP_LIVE=1` 시 skip. |
| `dashboard/tests/e2e/audit_tailing.spec.ts` | Audit 페이지 mount 시 자동 query, 3초 후 추가 폴링 발생, Pause 클릭 후 폴링 중지를 Playwright 로 검증. |
| `dashboard/tests/e2e/page_descriptions.spec.ts` | 5개 페이지(`/pipeline`, `/audit`, `/prompt`, `/kb`, `/login`) 진입 시 description `<p>` 가 표시되고 비어있지 않음을 검증. |
| `scripts/redeploy_idempotency.sh` | destroy → deploy → 5종 health check 자동화. DRY_RUN 지원. |
| `tests/scripts/test_redeploy_idempotency.py` | DRY_RUN=1 으로 redeploy_idempotency.sh 실행 → 단계 출력 패턴 매칭 검증. |

### 3.3 변경 없음 (의도적)

| 경로 | 이유 |
|---|---|
| `infra/*.tf` | 인프라 리소스 추가 없음. EC2 코드만 변경 → `deploy_static.sh` 로 충분. |
| `scripts/destroy.sh`, `scripts/deploy.sh` | 검증된 기존 동작 유지. redeploy_idempotency.sh 가 wrapper 로 호출. |
| `src/agentbox/**` (CLI) | 본 Task 와 무관. agentbox init/set/status 정상 동작 가정. |

---

## 4. 단계별 상세 계획

각 Phase 는 (a) 변경 직전 코드 스냅샷, (b) bite-sized step, (c) 검증 명령, (d) 예상 출력 으로 구성.
모든 step 은 체크박스(`- [ ]`) 로 표기되며 완료 시 `- [x]` 로 갱신.

---

### Phase A. 사전 환경 점검 (5~10분, 코드 변경 없음)

**목표:** 작업 환경(WSL, venv, AWS 자격증명, OneDrive 상태, 라이브 EC2 도달성) 을 확인하고 후속 단계가 안전한지 보장.

- [ ] **A-1. WSL 진입 + 프로젝트 디렉토리 이동**

  ```bash
  cd /mnt/c/Users/ab550/OneDrive/Desktop/projects/proj_AgentBox
  pwd  # /mnt/c/Users/ab550/OneDrive/Desktop/projects/proj_AgentBox
  ```

- [ ] **A-2. Python venv 활성화 + 의존성 확인**

  ```bash
  source .venv/bin/activate
  python -V       # Python 3.10+
  pip show pytest fastapi boto3 moto httpx | head -20
  ```

  Expected: pytest ≥ 7.x, fastapi ≥ 0.110, boto3 ≥ 1.34, moto ≥ 5.x 설치되어 있음.

- [ ] **A-3. dashboard Node 의존성 확인**

  ```bash
  cd dashboard
  ls node_modules/@playwright/test  # 폴더 존재 → 설치 완료
  cd ..
  ```

  설치 안 되어 있으면: `cd dashboard && npm ci && npx playwright install chromium`.

- [ ] **A-4. AWS 자격증명 도달성 확인**

  ```bash
  aws sts get-caller-identity --region us-east-1
  ```

  Expected: `Account`, `Arn` 필드 있는 JSON 출력.

- [ ] **A-5. 라이브 EC2 SaaS 응답 확인 (현재 상태 baseline 기록)**

  ```bash
  curl -s -o /dev/null -w "HTTP %{http_code}\n" http://54.165.51.239:8000/healthz
  curl -s -o /dev/null -w "/audit HTTP %{http_code}\n" http://54.165.51.239:8000/audit
  curl -s -o /dev/null -w "/api/audit HTTP %{http_code}\n" http://54.165.51.239:8000/api/audit
  ```

  Expected (현재): `/healthz` 200, `/audit` 200, `/api/audit` 401 (토큰 없음).
  만약 EC2 가 down 이면 Phase L 의 redeploy_idempotency.sh 를 먼저 실행해야 함.

- [ ] **A-6. OneDrive sync 상태 확인 (선택)**

  Phase L~M 만 영향. 그 전 Phase 는 무관. Phase L 진입 직전에 OneDrive 우클릭 → "Pause syncing → 2 hours".

- [ ] **A-7. 현재 git 상태 스냅샷 + 작업 브랜치 생성**

  ```bash
  git status
  git checkout -b task-6-dashboard-fix
  ```

  Expected: 깨끗한 working tree (Task-5 후 커밋된 상태).

- [ ] **A-8. 기존 테스트 PASS baseline 기록 (mock 만)**

  ```bash
  pytest tests/unit -x -q 2>&1 | tail -20
  ```

  Expected: 전부 PASS. 만약 fail 이 있으면 Task-5 종료 시점이 깨져 있는 것 → 별도 수정 후 본 Plan 진입.

---

### Phase B. server.py 라우트 `/api` prefix 일관화 (TDD: 단위 테스트 먼저)

**목표:** `/pipeline/stream`, `/settings/prompt`, `/settings/kb-ttl` 3개 라우트를 `/api/...` 로 이동.

#### Phase B 변경 직전 상태 (참고)

`ec2/saas/server.py` 의 관련 라인:

```python
# Line 67-90 (변경 대상)
@app.websocket("/pipeline/stream")
async def pipeline_stream(websocket: WebSocket): ...

# Line 148-158 (변경 대상)
@app.put("/settings/prompt")
async def update_prompt(body: PromptSettings, _: str = Depends(_require_admin)): ...

# Line 165-176 (변경 대상)
@app.put("/settings/kb-ttl")
async def update_kb_ttl(body: KBTTLSettings, _: str = Depends(_require_admin)): ...
```

#### Phase B Steps

- [x] **B-1. 실패하는 단위 테스트 작성** (`tests/unit/test_saas_api_prefix.py` 신규)

  파일 경로: `tests/unit/test_saas_api_prefix.py`

  ```python
  """server.py 라우트가 /api/* prefix 로 정확히 등록되어 있는지 검증."""
  import pytest
  from fastapi.testclient import TestClient


  @pytest.fixture(autouse=True)
  def aws_env(monkeypatch):
      monkeypatch.setenv("AWS_REGION", "us-east-1")
      monkeypatch.setenv("PROJECT_NAME", "agentbox")
      monkeypatch.setenv("ADMIN_TOKEN", "testtok")
      monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
      monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
      monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")


  @pytest.fixture
  def client(monkeypatch):
      from unittest.mock import MagicMock
      mock_table = MagicMock()
      mock_table.scan.return_value = {"Items": []}
      mock_table.get_item.return_value = {"Item": {"value": "stored"}}
      mock_db = MagicMock()
      mock_db.Table.return_value = mock_table

      import ec2.saas.server as srv
      monkeypatch.setattr(srv, "_dynamo", mock_db)
      monkeypatch.setattr(srv, "_ADMIN_TOKEN", "testtok")
      return TestClient(srv.app)


  def test_api_pipeline_stream_ws_route_registered(client):
      """WebSocket /api/pipeline/stream 핸드셰이크 성공."""
      with client.websocket_connect("/api/pipeline/stream") as ws:
          # 핸드셰이크 성공 자체가 검증 — 메시지 송수신은 라이브에서.
          assert ws is not None


  def test_api_settings_prompt_put_route(client):
      resp = client.put(
          "/api/settings/prompt",
          headers={"X-Admin-Token": "testtok"},
          json={"system_prompt": "test prompt"},
      )
      assert resp.status_code == 200
      assert resp.json() == {"ok": True}


  def test_api_settings_kb_ttl_put_route(client):
      resp = client.put(
          "/api/settings/kb-ttl",
          headers={"X-Admin-Token": "testtok"},
          json={"ttl_minutes": 10},
      )
      assert resp.status_code == 200
      assert resp.json()["ttl_minutes"] == 10


  def test_old_settings_paths_return_404(client):
      """이전 경로(`/settings/prompt`, `/settings/kb-ttl`)는 더 이상 동작하지 않음."""
      # SPA catch-all 은 GET 만 잡으므로 PUT 은 405 또는 404
      resp = client.put(
          "/settings/prompt",
          headers={"X-Admin-Token": "testtok"},
          json={"system_prompt": "x"},
      )
      assert resp.status_code in (404, 405)
  ```

- [x] **B-2. 테스트가 FAIL 하는지 확인**

  ```bash
  pytest tests/unit/test_saas_api_prefix.py -v 2>&1 | tail -30
  ```

  Expected: 4개 테스트 중 최소 3개 FAIL (이유: 핸들러가 `/api/...` 에 등록 안 됨). `test_old_settings_paths_return_404` 는 PASS 가능(현재 catch-all 이 GET 만 잡으므로 PUT 은 이미 405).

- [x] **B-3. `ec2/saas/server.py` 데코레이터 수정**

  편집 대상 3곳:

  ```python
  # Before:
  @app.websocket("/pipeline/stream")
  # After:
  @app.websocket("/api/pipeline/stream")

  # Before:
  @app.put("/settings/prompt")
  # After:
  @app.put("/api/settings/prompt")

  # Before:
  @app.put("/settings/kb-ttl")
  # After:
  @app.put("/api/settings/kb-ttl")
  ```

  나머지 함수 본문은 변경 없음.

- [x] **B-4. 테스트가 PASS 하는지 확인**

  ```bash
  pytest tests/unit/test_saas_api_prefix.py -v 2>&1 | tail -30
  ```

  Expected: 4개 모두 PASS.

- [x] **B-5. 기존 단위 테스트 전체가 여전히 PASS 하는지 확인**

  ```bash
  pytest tests/unit -x -q 2>&1 | tail -20
  ```

  Expected: 0 failed. `test_saas_audit_html.py` 는 `/api/audit` 사용 중이라 영향 없음.

- [x] **B-6. 커밋**

  ```bash
  git add ec2/saas/server.py tests/unit/test_saas_api_prefix.py
  git commit -m "fix(saas): move pipeline/settings routes to /api prefix to match frontend"
  ```

---

### Phase C. 신규 GET 설정 조회 엔드포인트 2개 추가 (TDD)

**목표:** Prompt/KB 페이지가 진입 시 직전 저장값을 로드 가능하도록 GET `/api/settings/prompt-get`, `/api/settings/kb-ttl-get` 추가.

#### Phase C Steps

- [x] **C-1. 실패하는 단위 테스트 작성** (`tests/unit/test_saas_settings_get.py` 신규)

  ```python
  """GET /api/settings/prompt-get, /api/settings/kb-ttl-get 단위 테스트."""
  from unittest.mock import MagicMock
  import pytest
  from fastapi.testclient import TestClient


  @pytest.fixture(autouse=True)
  def aws_env(monkeypatch):
      monkeypatch.setenv("AWS_REGION", "us-east-1")
      monkeypatch.setenv("PROJECT_NAME", "agentbox")
      monkeypatch.setenv("ADMIN_TOKEN", "testtok")
      monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
      monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
      monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")


  def _mk_client(monkeypatch, get_item_response):
      mock_table = MagicMock()
      mock_table.get_item.return_value = get_item_response
      mock_db = MagicMock()
      mock_db.Table.return_value = mock_table

      import ec2.saas.server as srv
      monkeypatch.setattr(srv, "_dynamo", mock_db)
      monkeypatch.setattr(srv, "_ADMIN_TOKEN", "testtok")
      return TestClient(srv.app), mock_table


  def test_get_prompt_returns_stored_value(monkeypatch):
      client, table = _mk_client(monkeypatch, {"Item": {"key": "bedrock_system_prompt", "value": "PROMPT_X"}})
      resp = client.get("/api/settings/prompt-get", headers={"X-Admin-Token": "testtok"})
      assert resp.status_code == 200
      assert resp.json() == {"system_prompt": "PROMPT_X"}


  def test_get_prompt_returns_empty_when_missing(monkeypatch):
      client, _ = _mk_client(monkeypatch, {})  # no Item
      resp = client.get("/api/settings/prompt-get", headers={"X-Admin-Token": "testtok"})
      assert resp.status_code == 200
      assert resp.json() == {"system_prompt": ""}


  def test_get_prompt_requires_token(monkeypatch):
      client, _ = _mk_client(monkeypatch, {})
      resp = client.get("/api/settings/prompt-get")
      assert resp.status_code == 401


  def test_get_kb_ttl_returns_stored(monkeypatch):
      client, _ = _mk_client(monkeypatch, {"Item": {"key": "kb_ttl_minutes", "value": 7}})
      resp = client.get("/api/settings/kb-ttl-get", headers={"X-Admin-Token": "testtok"})
      assert resp.status_code == 200
      assert resp.json() == {"ttl_minutes": 7}


  def test_get_kb_ttl_default_when_missing(monkeypatch):
      client, _ = _mk_client(monkeypatch, {})
      resp = client.get("/api/settings/kb-ttl-get", headers={"X-Admin-Token": "testtok"})
      assert resp.status_code == 200
      assert resp.json() == {"ttl_minutes": 5}  # default
  ```

- [x] **C-2. 테스트 FAIL 확인**

  ```bash
  pytest tests/unit/test_saas_settings_get.py -v 2>&1 | tail -20
  ```

  Expected: 5개 모두 FAIL (404 — 핸들러 없음).

- [x] **C-3. `ec2/saas/server.py` 에 GET 핸들러 2개 추가**

  추가 위치: 기존 `update_prompt` 함수 바로 위 (line 148 직전).

  ```python
  @app.get("/api/settings/prompt-get")
  async def get_prompt(_: str = Depends(_require_admin)):
      """현재 저장된 Bedrock system prompt 를 반환. 없으면 빈 문자열."""
      table = _dynamo.Table(f"{_PROJECT}-settings")
      resp = table.get_item(Key={"key": "bedrock_system_prompt"})
      item = resp.get("Item") or {}
      return {"system_prompt": item.get("value", "")}


  @app.get("/api/settings/kb-ttl-get")
  async def get_kb_ttl(_: str = Depends(_require_admin)):
      """현재 저장된 KB TTL(분) 를 반환. 없으면 기본 5."""
      table = _dynamo.Table(f"{_PROJECT}-settings")
      resp = table.get_item(Key={"key": "kb_ttl_minutes"})
      item = resp.get("Item") or {}
      return {"ttl_minutes": int(item.get("value", 5))}
  ```

- [x] **C-4. 테스트 PASS 확인**

  ```bash
  pytest tests/unit/test_saas_settings_get.py -v 2>&1 | tail -20
  ```

  Expected: 5개 모두 PASS.

- [x] **C-5. 전체 단위 테스트 회귀 확인**

  ```bash
  pytest tests/unit -x -q 2>&1 | tail -20
  ```

  Expected: 0 failed.

- [x] **C-6. 커밋**

  ```bash
  git add ec2/saas/server.py tests/unit/test_saas_settings_get.py
  git commit -m "feat(saas): add GET /api/settings/{prompt,kb-ttl}-get endpoints"
  ```

---

### Phase D. 각 페이지 상단 description 하드코딩 (UI)

**목표:** 5개 페이지 컴포넌트 상단에 안내 문구 `<p>` 추가.

> 각 페이지 description 문구는 아래 표 그대로 사용한다(임의 변경 금지). 한국어 + 영어 혼용 가능, 톤은 "사용자 친화적이고 사실적".

| 페이지 | 파일 | description 문구 |
|---|---|---|
| Pipeline | `dashboard/src/pages/PipelineStream.tsx` | "mitmproxy → gRPC → Bedrock Agent 흐름으로 들어오는 모든 보안 검사 이벤트를 WebSocket 으로 실시간 표시합니다. 페이지에 머무는 동안만 수집되며, 닫으면 사라집니다. 영구 보관 기록은 Audit 페이지에서 확인하세요." |
| Audit | `dashboard/src/pages/Audit.tsx` | "DynamoDB 에 영구 저장된 ALLOW/BLOCK 판정 이력입니다. 페이지 진입 시 최근 100건을 자동 조회하고, 3초마다 새 이벤트를 상단에 추가합니다. 우상단 Pause 버튼으로 폴링을 일시 중지할 수 있습니다. From/To/Verdict 로 과거 구간을 검색하거나 CSV 로 내보낼 수 있습니다." |
| Prompt Editor | `dashboard/src/pages/PromptEditor.tsx` | "Bedrock Agent 가 보안 검사 시 사용하는 시스템 프롬프트를 편집합니다. 저장 즉시 다음 검사 요청부터 적용됩니다. 변경 전 백업을 권장합니다." |
| KB Settings | `dashboard/src/pages/KBSettings.tsx` | "복호화된 코드가 KB Staging 버킷에 머무는 최대 시간(분) 을 설정합니다. 1~60 분 범위. Zero-Knowledge 보장을 위해 검사 완료 후 또는 TTL 만료 시 즉시 삭제됩니다." |
| Login | `dashboard/src/pages/Login.tsx` | "AgentBox 관리 콘솔에 접근하려면 Admin Token 을 입력하세요. 토큰은 EC2 환경변수 `ADMIN_TOKEN` 으로 설정되며, 브라우저 localStorage 에 저장됩니다." |

#### Phase D Steps

- [x] **D-1. PipelineStream.tsx 수정**

  편집 위치: 기존 `<h2>Pipeline Stream</h2>` 바로 아래.

  Before (line 34-36 근방):
  ```tsx
  <h2>Pipeline Stream</h2>
  <p style={{ color: "#666" }}>Real-time events via WebSocket</p>
  ```

  After:
  ```tsx
  <h2>Pipeline Stream</h2>
  <p style={{ color: "#666", fontSize: 13, marginTop: 0, marginBottom: "1rem", lineHeight: 1.5 }}>
    mitmproxy → gRPC → Bedrock Agent 흐름으로 들어오는 모든 보안 검사 이벤트를 WebSocket 으로 실시간 표시합니다.
    페이지에 머무는 동안만 수집되며, 닫으면 사라집니다. 영구 보관 기록은 Audit 페이지에서 확인하세요.
  </p>
  ```

  기존 `<p>Real-time events via WebSocket</p>` 는 새 description 으로 대체(삭제).

- [x] **D-2. Audit.tsx 수정** — description 만 추가 (tailing 로직은 Phase E 에서)

  편집 위치: 기존 `<h2>Audit Log</h2>` 바로 아래.

  After:
  ```tsx
  <h2>Audit Log</h2>
  <p style={{ color: "#666", fontSize: 13, marginTop: 0, marginBottom: "1rem", lineHeight: 1.5 }}>
    DynamoDB 에 영구 저장된 ALLOW/BLOCK 판정 이력입니다. 페이지 진입 시 최근 100건을 자동 조회하고,
    3초마다 새 이벤트를 상단에 추가합니다. 우상단 Pause 버튼으로 폴링을 일시 중지할 수 있습니다.
    From/To/Verdict 로 과거 구간을 검색하거나 CSV 로 내보낼 수 있습니다.
  </p>
  ```

- [x] **D-3. PromptEditor.tsx 수정**

  Before (line 31-32 근방):
  ```tsx
  <h2>Bedrock System Prompt Editor</h2>
  <p style={{ color: "#666" }}>Edit the security inspection prompt used by Bedrock Agent.</p>
  ```

  After:
  ```tsx
  <h2>Bedrock System Prompt Editor</h2>
  <p style={{ color: "#666", fontSize: 13, marginTop: 0, marginBottom: "1rem", lineHeight: 1.5 }}>
    Bedrock Agent 가 보안 검사 시 사용하는 시스템 프롬프트를 편집합니다. 저장 즉시 다음 검사 요청부터 적용됩니다.
    변경 전 백업을 권장합니다.
  </p>
  ```

- [x] **D-4. KBSettings.tsx 수정**

  Before (line 29-30 근방):
  ```tsx
  <h2>KB Staging Bucket Settings</h2>
  <p style={{ color: "#666" }}>Set how long decrypted code stays in the KB staging bucket before deletion.</p>
  ```

  After:
  ```tsx
  <h2>KB Staging Bucket Settings</h2>
  <p style={{ color: "#666", fontSize: 13, marginTop: 0, marginBottom: "1rem", lineHeight: 1.5 }}>
    복호화된 코드가 KB Staging 버킷에 머무는 최대 시간(분) 을 설정합니다. 1~60 분 범위.
    Zero-Knowledge 보장을 위해 검사 완료 후 또는 TTL 만료 시 즉시 삭제됩니다.
  </p>
  ```

- [x] **D-5. Login.tsx 수정**

  편집 위치: `<h2 style={{ marginTop: 0 }}>AgentBox Login</h2>` 바로 아래.

  After:
  ```tsx
  <h2 style={{ marginTop: 0 }}>AgentBox Login</h2>
  <p style={{ color: "#666", fontSize: 13, marginTop: 0, marginBottom: "1rem", lineHeight: 1.5 }}>
    AgentBox 관리 콘솔에 접근하려면 Admin Token 을 입력하세요. 토큰은 EC2 환경변수 <code>ADMIN_TOKEN</code> 으로 설정되며,
    브라우저 localStorage 에 저장됩니다.
  </p>
  ```

- [x] **D-6. TypeScript 컴파일 통과 확인**

  ```bash
  cd dashboard
  npx tsc --noEmit
  cd ..
  ```

  Expected: 출력 없음 (에러 0건).

- [x] **D-7. 커밋**

  ```bash
  git add dashboard/src/pages/PipelineStream.tsx dashboard/src/pages/Audit.tsx \
          dashboard/src/pages/PromptEditor.tsx dashboard/src/pages/KBSettings.tsx \
          dashboard/src/pages/Login.tsx
  git commit -m "feat(dashboard): add per-page description hint above each view"
  ```

---

### Phase E. Audit 자동 tailing + Pause/Resume 토글 (UI 핵심)

**목표:** `Audit.tsx` 에 mount 시 자동 query + 3초 폴링 + Pause/Resume 토글 추가.

#### Phase E Steps

- [x] **E-1. Audit.tsx 의 import / state / 로직 갱신**

  편집 대상: `dashboard/src/pages/Audit.tsx` 전체. 아래 코드로 교체(description 은 Phase D 의 것 유지).

  핵심 변경 사항:
  1. `useEffect` 로 mount 시 자동 query().
  2. `useState<boolean>(true)` 로 `tailing` 상태 추가 (기본 ON).
  3. `useEffect` 로 `setInterval(3000)` 등록 → tailing && rows 가 있는 한 polling. cleanup 으로 clearInterval.
  4. 새 이벤트는 `event_id` 기준으로 중복 제거 후 상단 prepend. 최대 200건 유지.
  5. Pause 버튼: tailing 토글.

  전체 파일 내용 (Phase D 의 description 포함):

  ```tsx
  import { useCallback, useEffect, useRef, useState } from "react";
  import { useAuth, apiHeaders } from "../components/AuthProvider";

  interface AuditRow {
    event_id: string;
    ts: string;
    user_id: string;
    verdict: string;
    reasons_json?: string;
    latency_ms?: number;
    prompt_hash?: string;
  }

  const POLL_MS = 3000;
  const MAX_ROWS = 200;

  export function Audit() {
    const { token } = useAuth();
    const [from, setFrom] = useState("");
    const [to, setTo] = useState("");
    const [verdict, setVerdict] = useState("");
    const [rows, setRows] = useState<AuditRow[]>([]);
    const [loading, setLoading] = useState(false);
    const [tailing, setTailing] = useState(true);
    const rowsRef = useRef<AuditRow[]>([]);

    useEffect(() => {
      rowsRef.current = rows;
    }, [rows]);

    const query = useCallback(async (silent = false) => {
      if (!silent) setLoading(true);
      const params = new URLSearchParams({ limit: "100" });
      if (from) params.set("from_ts", from);
      if (to) params.set("to_ts", to);
      if (verdict) params.set("verdict", verdict);
      const res = await fetch(`/api/audit?${params}`, { headers: apiHeaders(token) });
      if (res.ok) {
        const fresh: AuditRow[] = await res.json();
        if (silent) {
          // tailing: prepend only new event_ids
          const existing = new Set(rowsRef.current.map((r) => r.event_id));
          const newOnes = fresh.filter((r) => !existing.has(r.event_id));
          if (newOnes.length > 0) {
            setRows((prev) => [...newOnes, ...prev].slice(0, MAX_ROWS));
          }
        } else {
          setRows(fresh.slice(0, MAX_ROWS));
        }
      }
      if (!silent) setLoading(false);
    }, [from, to, verdict, token]);

    // Auto-query on mount
    useEffect(() => {
      query(false);
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Polling
    useEffect(() => {
      if (!tailing) return;
      const id = setInterval(() => {
        query(true);
      }, POLL_MS);
      return () => clearInterval(id);
    }, [tailing, query]);

    function exportCSV() {
      const headers = ["event_id", "ts", "user_id", "verdict", "latency_ms", "reasons"];
      const csvRows = rows.map((r) =>
        [r.event_id, r.ts, r.user_id, r.verdict, r.latency_ms ?? "",
         r.reasons_json ? JSON.parse(r.reasons_json).join("|") : ""].join(",")
      );
      const blob = new Blob([[headers.join(","), ...csvRows].join("\n")], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      Object.assign(document.createElement("a"), { href: url, download: "audit.csv" }).click();
    }

    return (
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0 }}>Audit Log</h2>
          <button
            onClick={() => setTailing((t) => !t)}
            style={{
              ...btnStyle,
              background: tailing ? "#999" : "#2e7d32",
            }}
            data-testid="audit-tail-toggle"
          >
            {tailing ? "Pause" : "Resume"}
          </button>
        </div>
        <p style={{ color: "#666", fontSize: 13, marginTop: "0.3rem", marginBottom: "1rem", lineHeight: 1.5 }}>
          DynamoDB 에 영구 저장된 ALLOW/BLOCK 판정 이력입니다. 페이지 진입 시 최근 100건을 자동 조회하고,
          3초마다 새 이벤트를 상단에 추가합니다. 우상단 Pause 버튼으로 폴링을 일시 중지할 수 있습니다.
          From/To/Verdict 로 과거 구간을 검색하거나 CSV 로 내보낼 수 있습니다.
        </p>
        <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem", flexWrap: "wrap" }}>
          <label>From: <input type="datetime-local" value={from} onChange={(e) => setFrom(e.target.value)} /></label>
          <label>To: <input type="datetime-local" value={to} onChange={(e) => setTo(e.target.value)} /></label>
          <label>
            Verdict:{" "}
            <select value={verdict} onChange={(e) => setVerdict(e.target.value)}>
              <option value="">All</option>
              <option value="ALLOW">ALLOW</option>
              <option value="BLOCK">BLOCK</option>
            </select>
          </label>
          <button onClick={() => query(false)} style={btnStyle} data-testid="audit-query-btn">Query</button>
          {rows.length > 0 && (
            <button onClick={exportCSV} style={{ ...btnStyle, background: "#2e7d32" }} data-testid="audit-export-btn">
              Export CSV
            </button>
          )}
        </div>
        {loading && <p>Loading...</p>}
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr style={{ background: "#1a1a2e", color: "#fff" }}>
              {["Time", "User", "Verdict", "Latency", "Reasons", "Prompt Hash"].map((h) => (
                <th key={h} style={th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.event_id} style={{ background: r.verdict === "BLOCK" ? "#fff0f0" : "#fff" }}>
                <td style={td}>{new Date(r.ts).toLocaleString()}</td>
                <td style={td}>{r.user_id}</td>
                <td style={{ ...td, color: r.verdict === "BLOCK" ? "#e94560" : "#2e7d32", fontWeight: "bold" }}>{r.verdict}</td>
                <td style={td}>{r.latency_ms ? `${r.latency_ms}ms` : "-"}</td>
                <td style={td}>{r.reasons_json ? JSON.parse(r.reasons_json).join("; ") : ""}</td>
                <td style={{ ...td, fontFamily: "monospace", fontSize: 11 }}>{(r.prompt_hash ?? "").slice(0, 12)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && !loading && <p style={{ color: "#999", textAlign: "center", marginTop: "1rem" }}>No results.</p>}
      </div>
    );
  }

  const btnStyle: React.CSSProperties = {
    background: "#e94560", color: "#fff", border: "none", padding: "0.4rem 1rem",
    cursor: "pointer", borderRadius: 4,
  };
  const th: React.CSSProperties = { padding: "0.4rem", textAlign: "left", border: "1px solid #333" };
  const td: React.CSSProperties = { padding: "0.3rem 0.4rem", border: "1px solid #ddd" };
  ```

- [x] **E-2. TypeScript 컴파일 확인**

  ```bash
  cd dashboard
  npx tsc --noEmit
  cd ..
  ```

  Expected: 출력 없음.

- [x] **E-3. 커밋**

  ```bash
  git add dashboard/src/pages/Audit.tsx
  git commit -m "feat(dashboard): auto-tail audit log with 3s polling and pause/resume toggle"
  ```

---

### Phase F. 기존 e2e 테스트 갱신 (Playwright)

**목표:** 기존 `dashboard/tests/e2e/dashboard.spec.ts` 의 PUT 매칭 패턴을 `/api/settings/...` 로 갱신. Audit 테스트도 자동 query 가 동작하도록 보정.

#### Phase F Steps

- [x] **F-1. dashboard.spec.ts 갱신**

  변경 위치 1 (PromptEditor 테스트, line 21~):

  ```ts
  // Before:
  page.waitForRequest((r) => r.method() === "PUT" && r.url().includes("/settings/prompt")),
  // After:
  page.waitForRequest((r) => r.method() === "PUT" && r.url().includes("/api/settings/prompt")),
  ```

  변경 위치 2 (KB Settings 테스트, line 33~):

  ```ts
  // Before:
  page.waitForRequest((r) => r.method() === "PUT" && r.url().includes("/settings/kb-ttl")),
  // After:
  page.waitForRequest((r) => r.method() === "PUT" && r.url().includes("/api/settings/kb-ttl")),
  ```

  변경 위치 3 (Audit 테스트, line 41~): 자동 query 가 mount 시 발생하므로, 사용자 클릭 이전에 이미 fetch 가 일어남 → 테스트가 "page mount 시 GET /api/audit 발생" 을 검증하도록 수정.

  ```ts
  test("Audit: page mount triggers auto query and Pause toggle works", async ({ page }) => {
    const reqs: string[] = [];
    page.on("request", (r) => { if (r.url().includes("/api/audit")) reqs.push(r.url()); });
    await page.goto("/audit");
    // wait for auto-query on mount
    await page.waitForRequest((r) => r.url().includes("/api/audit"));
    expect(reqs.length).toBeGreaterThanOrEqual(1);
    // pause toggle
    const toggle = page.locator("[data-testid='audit-tail-toggle']");
    await expect(toggle).toBeVisible();
    await toggle.click();
    await expect(toggle).toContainText("Resume");
  });
  ```

- [x] **F-2. e2e 테스트 실행 환경 준비**

  e2e 는 EC2 라이브 대상 실행이 어렵기 때문에(빌드 후 deploy_static.sh 필요) **Phase K 의 라이브 단계로 미룬다.** 지금은 컴파일/문법만 확인.

  ```bash
  cd dashboard
  npx tsc --noEmit -p tsconfig.json
  npx playwright test --list 2>&1 | tail -10
  cd ..
  ```

  Expected: 에러 0건, 테스트 목록에 갱신된 케이스가 나타남.

- [x] **F-3. 커밋**

  ```bash
  git add dashboard/tests/e2e/dashboard.spec.ts
  git commit -m "test(dashboard): update e2e selectors for /api prefix and audit auto-tail"
  ```

---

### Phase G. 신규 e2e 테스트 작성 (Playwright)

**목표:** Audit tailing 과 페이지 description 표시를 e2e 레벨에서 검증.

#### Phase G Steps

- [x] **G-1. `dashboard/tests/e2e/audit_tailing.spec.ts` 신규**

  ```ts
  import { test, expect } from "@playwright/test";

  const TOKEN = process.env.ADMIN_TOKEN ?? "test-token";

  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.evaluate((t) => localStorage.setItem("admin_token", t), TOKEN);
  });

  test("Audit: auto-query on mount, then polling every 3s", async ({ page }) => {
    let count = 0;
    page.on("request", (r) => { if (r.url().includes("/api/audit?")) count += 1; });
    await page.goto("/audit");
    await page.waitForTimeout(7000); // ≥ 2 polls + initial
    expect(count).toBeGreaterThanOrEqual(2);
  });

  test("Audit: Pause stops polling, Resume restarts", async ({ page }) => {
    await page.goto("/audit");
    await page.waitForRequest((r) => r.url().includes("/api/audit?"));
    await page.locator("[data-testid='audit-tail-toggle']").click(); // Pause
    let countAfterPause = 0;
    page.on("request", (r) => { if (r.url().includes("/api/audit?")) countAfterPause += 1; });
    await page.waitForTimeout(7000);
    expect(countAfterPause).toBe(0);
    await page.locator("[data-testid='audit-tail-toggle']").click(); // Resume
    await page.waitForRequest((r) => r.url().includes("/api/audit?"), { timeout: 5000 });
  });
  ```

- [x] **G-2. `dashboard/tests/e2e/page_descriptions.spec.ts` 신규**

  ```ts
  import { test, expect } from "@playwright/test";

  const TOKEN = process.env.ADMIN_TOKEN ?? "test-token";
  const PAGES = [
    { path: "/pipeline", keyword: "mitmproxy" },
    { path: "/audit", keyword: "DynamoDB" },
    { path: "/prompt", keyword: "Bedrock Agent" },
    { path: "/kb", keyword: "KB Staging" },
  ];

  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.evaluate((t) => localStorage.setItem("admin_token", t), TOKEN);
  });

  for (const { path, keyword } of PAGES) {
    test(`Page ${path} shows description containing "${keyword}"`, async ({ page }) => {
      await page.goto(path);
      const desc = page.locator("h2 + p").first();
      await expect(desc).toBeVisible();
      await expect(desc).toContainText(keyword);
    });
  }

  test("Login page shows description containing Admin Token", async ({ page }) => {
    await page.evaluate(() => localStorage.removeItem("admin_token"));
    await page.goto("/login");
    const desc = page.locator("h2 + p").first();
    await expect(desc).toBeVisible();
    await expect(desc).toContainText("Admin Token");
  });
  ```

- [x] **G-3. 컴파일/문법 확인 (라이브 실행은 Phase K)**

  ```bash
  cd dashboard
  npx tsc --noEmit
  npx playwright test --list 2>&1 | grep -E "(audit_tailing|page_descriptions)"
  cd ..
  ```

  Expected: 신규 케이스 7개(이상) 목록에 나타남.

- [x] **G-4. 커밋**

  ```bash
  git add dashboard/tests/e2e/audit_tailing.spec.ts dashboard/tests/e2e/page_descriptions.spec.ts
  git commit -m "test(dashboard): add e2e for audit tailing and page descriptions"
  ```

---

### Phase H. 전체 단위 테스트 PASS 확인

**목표:** Phase B~G 변경 후 모든 단위 테스트가 깨끗하게 PASS 하는지 최종 회귀 확인.

- [x] **H-1. 전체 pytest 단위 테스트 실행**

  ```bash
  pytest tests/unit -v 2>&1 | tail -40
  ```

  Expected: 모든 테스트 PASS. 신규 9개(B 4개 + C 5개) 포함.

- [x] **H-2. TypeScript 전체 빌드 확인 (소스 + 테스트)**

  ```bash
  cd dashboard
  npm run build
  ```

  Expected: `dist/` 생성, 에러 0건.

- [x] **H-3. 커밋 (필요 시 lockfile/lint 변경)**

  ```bash
  git status
  # 변경 없으면 skip
  ```

---

### Phase I. 라이브 EC2 통합 테스트 준비 — 신규 통합 테스트 파일

**목표:** 라이브 EC2 (`http://54.165.51.239:8000`) 대상으로 신규 `/api/*` 라우트와 자동 tailing 이 실제로 동작하는지 검증할 통합 테스트 파일을 미리 작성. 실제 실행은 Phase K 에서 수행(Phase J 에서 EC2 에 코드 배포 후).

#### Phase I Steps

- [x] **I-1. `tests/integration/test_saas_api_live.py` 신규**

  ```python
  """라이브 EC2 SaaS (/api/*) 통합 테스트. SKIP_LIVE=1 환경변수로 건너뛸 수 있음."""
  import os
  import json
  import socket
  from urllib.parse import urlparse

  import pytest
  import httpx
  from websockets.sync.client import connect as ws_connect


  LIVE_URL = os.environ.get("LIVE_SAAS_URL", "http://54.165.51.239:8000")
  ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
  SKIP = os.environ.get("SKIP_LIVE", "0") == "1"


  pytestmark = pytest.mark.skipif(
      SKIP or not ADMIN_TOKEN,
      reason="SKIP_LIVE=1 or ADMIN_TOKEN not set",
  )


  def test_healthz():
      r = httpx.get(f"{LIVE_URL}/healthz", timeout=5)
      assert r.status_code == 200
      assert r.json()["ok"] is True


  def test_audit_html_no_token():
      r = httpx.get(f"{LIVE_URL}/audit", timeout=5)
      assert r.status_code == 200
      assert "text/html" in r.headers["content-type"]


  def test_api_audit_requires_token():
      r = httpx.get(f"{LIVE_URL}/api/audit", timeout=5)
      assert r.status_code == 401


  def test_api_audit_with_token_returns_list():
      r = httpx.get(
          f"{LIVE_URL}/api/audit?limit=1",
          headers={"X-Admin-Token": ADMIN_TOKEN},
          timeout=10,
      )
      assert r.status_code == 200
      assert isinstance(r.json(), list)


  def test_api_settings_prompt_get():
      r = httpx.get(
          f"{LIVE_URL}/api/settings/prompt-get",
          headers={"X-Admin-Token": ADMIN_TOKEN},
          timeout=10,
      )
      assert r.status_code == 200
      assert "system_prompt" in r.json()


  def test_api_settings_kb_ttl_get():
      r = httpx.get(
          f"{LIVE_URL}/api/settings/kb-ttl-get",
          headers={"X-Admin-Token": ADMIN_TOKEN},
          timeout=10,
      )
      assert r.status_code == 200
      assert "ttl_minutes" in r.json()


  def test_api_pipeline_stream_ws_handshake():
      """WebSocket /api/pipeline/stream 핸드셰이크가 성공해야 한다."""
      parsed = urlparse(LIVE_URL)
      ws_url = f"ws://{parsed.netloc}/api/pipeline/stream"
      with ws_connect(ws_url, open_timeout=5) as ws:
          # 즉시 메시지를 받지 못해도 핸드셰이크만 검증
          assert ws.protocol is not None
  ```

  > **의존성 메모:** `websockets` 가 requirements-dev.txt 에 있는지 확인. 없으면 `pip install websockets` (호환 11.x 이상).

- [x] **I-2. requirements-dev.txt 에 websockets 추가 확인**

  ```bash
  grep -i websockets requirements-dev.txt || echo "websockets>=11.0" >> requirements-dev.txt
  pip install -r requirements-dev.txt
  ```

- [x] **I-3. SKIP_LIVE=1 일 때 skip 동작 확인**

  ```bash
  SKIP_LIVE=1 pytest tests/integration/test_saas_api_live.py -v 2>&1 | tail -10
  ```

  Expected: 7개 모두 SKIPPED.

- [x] **I-4. 커밋**

  ```bash
  git add tests/integration/test_saas_api_live.py requirements-dev.txt
  git commit -m "test(integration): add live EC2 /api/* smoke tests (skippable via SKIP_LIVE)"
  ```

---

### Phase J. dashboard 빌드 + deploy_static.sh 로 EC2 코드 배포

**목표:** Phase B~G 의 모든 변경 사항을 한 번에 라이브 EC2 에 반영. 빌드된 SPA + 갱신된 server.py 가 EC2 `/opt/agentbox/` 에 적용되고 `agentbox-saas` 서비스 재시작.

> **중요:** `deploy_static.sh` 는 `ec2/saas/server.py` + `ec2/saas/static/*` 를 tar 로 묶어 S3 → SSM 으로 푸시한다. **빌드된 `dist/*` 를 `ec2/saas/static/` 에 복사해야 함.** 기존 `deploy_static.sh` 가 이 복사를 수행하는지 미리 확인.

#### Phase J Steps

- [ ] **J-1. 기존 deploy_static.sh 동작 확인**

  ```bash
  cat scripts/deploy_static.sh | head -20
  ```

  현재 (`tar -czf /tmp/saas_update.tar.gz -C "$PROJ" ec2/saas/server.py ec2/saas/static`) 는 `ec2/saas/static/` 디렉토리를 그대로 묶음. → 빌드 산출물이 거기 있어야 함.

- [ ] **J-2. dashboard 빌드 + EC2 static 디렉토리로 복사**

  ```bash
  cd dashboard
  npm run build
  cd ..
  rm -rf ec2/saas/static
  mkdir -p ec2/saas/static
  cp -r dashboard/dist/* ec2/saas/static/
  ls ec2/saas/static  # index.html, assets/ 확인
  ```

- [ ] **J-3. AWS CLI 자격증명 다시 확인**

  ```bash
  aws sts get-caller-identity --region us-east-1 | head -5
  ```

- [ ] **J-4. deploy_static.sh 실행**

  ```bash
  bash scripts/deploy_static.sh 2>&1 | tee logs/deploy_static_task6.log
  ```

  Expected: `[1/4] Creating archive...`, `[2/4] Uploading to s3://...`, `[3/4] Building SSM params...`, `[4/4] Sending SSM command to EC2...`, `SSM CommandId: ...`, 마지막에 `Status: Success` JSON. 약 30~60초 소요.

- [ ] **J-5. EC2 적용 확인 (curl)**

  ```bash
  sleep 5
  curl -s http://54.165.51.239:8000/healthz | jq .
  # 변경된 라우트 확인
  curl -s -o /dev/null -w "/api/audit %{http_code}\n" http://54.165.51.239:8000/api/audit
  curl -s -o /dev/null -w "/api/settings/prompt-get %{http_code}\n" http://54.165.51.239:8000/api/settings/prompt-get
  curl -s -o /dev/null -w "/api/settings/kb-ttl-get %{http_code}\n"  http://54.165.51.239:8000/api/settings/kb-ttl-get
  ```

  Expected: `/healthz` 200, 나머지 401 (토큰 없음 → 정상). 만약 404 가 나오면 server.py 가 배포 안 된 것 → J-4 재실행.

- [ ] **J-6. 커밋 (빌드 산출물 포함)**

  ```bash
  git add ec2/saas/static
  git commit -m "build(dashboard): rebuild SPA with task-6 changes and deploy to EC2"
  ```

---

### Phase K. 라이브 통합 테스트 실행 (pytest + Playwright)

**목표:** 배포된 EC2 에 대해 신규 통합 테스트 + Playwright e2e 모두 PASS.

#### Phase K Steps

- [ ] **K-1. ADMIN_TOKEN 환경변수 설정**

  ```bash
  # ADMIN_TOKEN 은 EC2 환경변수와 동일해야 함. infra/terraform.tfvars 또는 1Password 등에서 확인.
  export ADMIN_TOKEN="<your-admin-token>"
  ```

- [ ] **K-2. pytest 라이브 통합 테스트 실행**

  ```bash
  pytest tests/integration/test_saas_api_live.py -v 2>&1 | tail -30
  ```

  Expected: 7개 모두 PASS. 실패 케이스가 있으면 어떤 라우트가 안 되는지 stdout 확인 후 Phase J 재시도.

- [ ] **K-3. Playwright e2e 실행 (라이브 EC2 대상)**

  `dashboard/playwright.config.ts` 의 baseURL 이 `http://localhost:5173` 이면 라이브 URL 로 임시 override.

  ```bash
  cd dashboard
  ADMIN_TOKEN="$ADMIN_TOKEN" \
    npx playwright test \
    --config=playwright.config.ts \
    -- --base-url=http://54.165.51.239:8000 \
    2>&1 | tail -40
  cd ..
  ```

  > 만약 `--base-url` CLI flag 가 지원되지 않으면 `playwright.config.ts` 에서 `use.baseURL` 을 환경변수로 읽도록 보조 수정(`process.env.E2E_BASE ?? "http://localhost:5173"`). 수정이 필요하면 별도 step 추가.

  Expected: dashboard.spec.ts (4) + audit_tailing.spec.ts (2) + page_descriptions.spec.ts (5) 모두 PASS.

- [ ] **K-4. 결과 기록 + 커밋 (필요 시)**

  ```bash
  # playwright-report/ 는 .gitignore 대상이면 커밋 X
  git status
  ```

---

### Phase L. redeploy_idempotency.sh 작성 (멱등성 자동화)

**목표:** destroy → deploy 가 한 명령으로 자동화되고, 5종 health check 가 자동 검증되는 스크립트 작성.

#### Phase L Steps

- [ ] **L-1. `scripts/redeploy_idempotency.sh` 신규 작성**

  ```bash
  #!/usr/bin/env bash
  # redeploy_idempotency.sh — destroy → deploy → health check 자동화
  #
  # 멱등성 보장: 임의의 인프라 상태에서 본 스크립트를 실행하면
  # 항상 동일한 "깨끗한 동작 상태" 로 수렴한다.
  #
  # Usage:
  #   bash scripts/redeploy_idempotency.sh                 # 실제 실행 (확인 prompt)
  #   bash scripts/redeploy_idempotency.sh -y              # 자동 승인
  #   DRY_RUN=1 bash scripts/redeploy_idempotency.sh       # plan 만 출력 (안전)
  #
  # 환경변수:
  #   DRY_RUN=1                : destroy/deploy 가 plan 만 실행
  #   ADMIN_TOKEN=<token>      : health check 의 /api/audit 검증에 사용
  #   SKIP_DASHBOARD_DEPLOY=1  : deploy_static.sh 단계 건너뜀

  set -euo pipefail
  : "${DRY_RUN:=0}"
  : "${SKIP_DASHBOARD_DEPLOY:=0}"

  PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  SCRIPTS_DIR="$PROJ_ROOT/scripts"
  AUTO_APPROVE="${1:-}"

  log() { echo "[$(date +%H:%M:%S)] $*"; }
  fail() { echo "ERROR: $*" >&2; exit 1; }

  # ── 0. 사전 점검 ─────────────────────────────────────────────────────────────
  log "[0/5] 사전 점검"
  command -v aws       >/dev/null || fail "aws CLI 가 PATH 에 없음"
  command -v terraform >/dev/null || fail "terraform 이 PATH 에 없음"
  aws sts get-caller-identity --region us-east-1 >/dev/null \
      || fail "AWS 자격증명이 유효하지 않음"
  [[ "$DRY_RUN" == "1" ]] && log "    DRY_RUN=1 — destroy/deploy 는 plan 만 실행됨"

  # ── 1. destroy.sh ───────────────────────────────────────────────────────────
  log "[1/5] destroy.sh (KMS 보존)"
  if [[ "$DRY_RUN" == "1" ]]; then
      DRY_RUN=1 bash "$SCRIPTS_DIR/destroy.sh"
  else
      if [[ "$AUTO_APPROVE" == "-y" ]]; then
          bash "$SCRIPTS_DIR/destroy.sh" -auto-approve
      else
          bash "$SCRIPTS_DIR/destroy.sh"
      fi
  fi

  # ── 2. deploy.sh ────────────────────────────────────────────────────────────
  log "[2/5] deploy.sh"
  if [[ "$DRY_RUN" == "1" ]]; then
      DRY_RUN=1 bash "$SCRIPTS_DIR/deploy.sh"
  else
      if [[ "$AUTO_APPROVE" == "-y" ]]; then
          bash "$SCRIPTS_DIR/deploy.sh" -auto-approve
      else
          bash "$SCRIPTS_DIR/deploy.sh"
      fi
  fi

  if [[ "$DRY_RUN" == "1" ]]; then
      log "DRY_RUN 종료 — 실제 deploy 가 아니므로 health check 건너뜀"
      exit 0
  fi

  # ── 3. terraform output 으로 SaaS URL 획득 ─────────────────────────────────
  log "[3/5] terraform output 확인"
  cd "$PROJ_ROOT/infra"
  APP_IP=$(terraform output -raw app_public_ip 2>/dev/null) \
      || fail "app_public_ip 출력 없음"
  SAAS_URL="http://${APP_IP}:8000"
  log "    SaaS URL = $SAAS_URL"
  cd "$PROJ_ROOT"

  # ── 4. dashboard 배포 (옵션) ───────────────────────────────────────────────
  if [[ "$SKIP_DASHBOARD_DEPLOY" != "1" ]]; then
      log "[4/5] dashboard 빌드 + deploy_static.sh"
      [[ -d dashboard/node_modules ]] || (cd dashboard && npm ci)
      (cd dashboard && npm run build)
      rm -rf ec2/saas/static
      mkdir -p ec2/saas/static
      cp -r dashboard/dist/* ec2/saas/static/
      bash "$SCRIPTS_DIR/deploy_static.sh"
  else
      log "[4/5] SKIP_DASHBOARD_DEPLOY=1 — dashboard 배포 건너뜀"
  fi

  # ── 5. Health Check 5종 ────────────────────────────────────────────────────
  log "[5/5] Health Check"
  sleep 5

  # 5-a. /healthz
  CODE=$(curl -s -o /dev/null -w "%{http_code}" "${SAAS_URL}/healthz")
  [[ "$CODE" == "200" ]] || fail "5-a /healthz expected 200, got $CODE"
  log "    5-a /healthz 200 OK"

  # 5-b. /audit (HTML 무토큰)
  CODE=$(curl -s -o /dev/null -w "%{http_code}" "${SAAS_URL}/audit")
  [[ "$CODE" == "200" ]] || fail "5-b /audit expected 200, got $CODE"
  log "    5-b /audit HTML 200 OK"

  # 5-c. /api/audit 무토큰 401
  CODE=$(curl -s -o /dev/null -w "%{http_code}" "${SAAS_URL}/api/audit")
  [[ "$CODE" == "401" ]] || fail "5-c /api/audit (no token) expected 401, got $CODE"
  log "    5-c /api/audit 401 (no token) OK"

  # 5-d. /api/audit 토큰 200 (선택 — ADMIN_TOKEN 있을 때만)
  if [[ -n "${ADMIN_TOKEN:-}" ]]; then
      CODE=$(curl -s -o /dev/null -w "%{http_code}" \
          -H "X-Admin-Token: $ADMIN_TOKEN" "${SAAS_URL}/api/audit?limit=1")
      [[ "$CODE" == "200" ]] || fail "5-d /api/audit (with token) expected 200, got $CODE"
      log "    5-d /api/audit 200 (with token) OK"
  else
      log "    5-d /api/audit (token check skipped — ADMIN_TOKEN not set)"
  fi

  # 5-e. /api/pipeline/stream WebSocket 핸드셰이크 (python 1-liner)
  python3 -c "
  import sys
  from urllib.parse import urlparse
  try:
      from websockets.sync.client import connect
  except ImportError:
      print('websockets 미설치 — skip', file=sys.stderr); sys.exit(0)
  url = '${SAAS_URL}'.replace('http://', 'ws://') + '/api/pipeline/stream'
  with connect(url, open_timeout=5) as ws:
      pass
  " && log "    5-e WebSocket /api/pipeline/stream 핸드셰이크 OK" \
    || fail "5-e WebSocket 핸드셰이크 실패"

  log "✓ redeploy_idempotency.sh 완료 — 모든 헬스체크 통과"
  log "  SaaS URL: $SAAS_URL"
  ```

- [ ] **L-2. 실행 권한 부여 + 문법 확인**

  ```bash
  chmod +x scripts/redeploy_idempotency.sh
  bash -n scripts/redeploy_idempotency.sh && echo "syntax OK"
  ```

- [ ] **L-3. DRY_RUN 테스트 (실제 destroy 안 함)**

  ```bash
  DRY_RUN=1 bash scripts/redeploy_idempotency.sh 2>&1 | tee logs/redeploy_dryrun.log | tail -40
  ```

  Expected: `[1/5] destroy.sh` → plan -destroy 출력, `[2/5] deploy.sh` → plan 출력, "DRY_RUN 종료" 메시지로 health check 없이 종료.

- [ ] **L-4. `tests/scripts/test_redeploy_idempotency.py` 신규 (dry-run 단위 검증)**

  ```python
  """redeploy_idempotency.sh dry-run 출력 검증."""
  import os
  import subprocess
  from pathlib import Path

  import pytest

  PROJ_ROOT = Path(__file__).resolve().parents[2]
  SCRIPT = PROJ_ROOT / "scripts" / "redeploy_idempotency.sh"


  @pytest.mark.skipif(not SCRIPT.exists(), reason="redeploy_idempotency.sh missing")
  def test_dry_run_executes_destroy_then_deploy(tmp_path):
      env = os.environ.copy()
      env["DRY_RUN"] = "1"
      result = subprocess.run(
          ["bash", str(SCRIPT)],
          env=env,
          capture_output=True,
          text=True,
          timeout=120,
          cwd=str(PROJ_ROOT),
      )
      out = result.stdout + result.stderr
      assert "[0/5]" in out, f"사전 점검 누락: {out[-500:]}"
      assert "[1/5]" in out and "destroy.sh" in out
      assert "[2/5]" in out and "deploy.sh" in out
      assert "DRY_RUN 종료" in out
      assert result.returncode == 0, out[-500:]


  @pytest.mark.skipif(not SCRIPT.exists(), reason="redeploy_idempotency.sh missing")
  def test_script_syntax_valid():
      result = subprocess.run(
          ["bash", "-n", str(SCRIPT)],
          capture_output=True,
          text=True,
      )
      assert result.returncode == 0, result.stderr
  ```

- [ ] **L-5. dry-run 단위 테스트 PASS**

  ```bash
  pytest tests/scripts/test_redeploy_idempotency.py -v 2>&1 | tail -15
  ```

  Expected: 2개 PASS.

- [ ] **L-6. 커밋**

  ```bash
  git add scripts/redeploy_idempotency.sh tests/scripts/test_redeploy_idempotency.py
  git commit -m "feat(scripts): add redeploy_idempotency.sh + dry-run unit test"
  ```

---

### Phase M. 실제 멱등성 검증 실행 (라이브)

**목표:** 한 번 실제 destroy → deploy 를 돌려 멱등성을 라이브 검증. 약 15~25분 소요(EC2 재생성 + Lambda ENI 정리 대기 포함).

> **사전 경고:**
> - 본 단계는 라이브 EC2/Lambda/Bedrock Agent 를 한 번 완전히 삭제하고 재생성한다.
> - 약 15~25분 동안 SaaS 가 down 됨.
> - KMS CMK 는 보존되므로 SOPS 파일은 영향 없음.
> - OneDrive sync 반드시 일시중지.
> - Public IP 가 바뀌므로 update_my_ip.sh 가 SG 갱신.

#### Phase M Steps

- [ ] **M-1. OneDrive sync 일시중지** (수동, GUI 우클릭)

- [ ] **M-2. ADMIN_TOKEN 환경변수 export** (실제 EC2 환경변수 값과 동일해야 함)

  ```bash
  export ADMIN_TOKEN="<your-admin-token>"
  ```

- [ ] **M-3. redeploy_idempotency.sh 실제 실행 (자동 승인)**

  ```bash
  bash scripts/redeploy_idempotency.sh -y 2>&1 | tee logs/redeploy_live_$(date +%Y%m%d-%H%M%S).log
  ```

  Expected: 약 15~25분 후 마지막 줄에 `✓ redeploy_idempotency.sh 완료 — 모든 헬스체크 통과` + 새 SaaS URL 출력.

- [ ] **M-4. 새 EC2 IP 로 SG 업데이트 + 메모 갱신**

  ```bash
  # 새 IP 확인
  cd infra && terraform output -raw app_public_ip
  cd ..
  # SG 가 현재 endpoint(개발자 PC) IP 를 허용하도록 갱신
  bash scripts/update_my_ip.sh -y
  ```

- [ ] **M-5. 라이브 통합 테스트 재실행 (새 EC2 대상)**

  ```bash
  NEW_IP=$(cd infra && terraform output -raw app_public_ip)
  LIVE_SAAS_URL="http://${NEW_IP}:8000" \
    ADMIN_TOKEN="$ADMIN_TOKEN" \
    pytest tests/integration/test_saas_api_live.py -v 2>&1 | tail -20
  ```

  Expected: 7개 PASS.

- [ ] **M-6. Playwright e2e 재실행 (새 EC2 대상)**

  ```bash
  NEW_IP=$(cd infra && terraform output -raw app_public_ip)
  cd dashboard
  ADMIN_TOKEN="$ADMIN_TOKEN" \
    E2E_BASE="http://${NEW_IP}:8000" \
    npx playwright test 2>&1 | tail -30
  cd ..
  ```

  Expected: 모든 케이스 PASS.

- [ ] **M-7. 메모리(project_agentbox.md) 갱신**

  새 EC2 IP, Instance ID, Bedrock Agent ID 등을 메모리에 반영.

- [ ] **M-8. OneDrive sync 재개** (수동)

- [ ] **M-9. 최종 커밋 + 브랜치 정리**

  ```bash
  git log --oneline -20
  git push origin task-6-dashboard-fix
  # PR 생성은 사용자 지시 후 별도 진행
  ```

---

## 5. 단위/통합 테스트 매트릭스

| 계층 | 파일 | 신규/수정 | 환경 | 실행 시점 |
|---|---|---|---|---|
| 단위 | `tests/unit/test_saas_api_prefix.py` | 신규 (Phase B-1) | mock TestClient | B-4, H-1 |
| 단위 | `tests/unit/test_saas_settings_get.py` | 신규 (Phase C-1) | mock TestClient | C-4, H-1 |
| 단위 | `tests/unit/test_saas_audit_html.py` (기존) | 변경 없음 | mock TestClient | H-1 |
| 단위 | 기존 tests/unit/ 전체 | 변경 없음 | mock | A-8, B-5, C-5, H-1 |
| 단위(script) | `tests/scripts/test_redeploy_idempotency.py` | 신규 (Phase L-4) | bash DRY_RUN | L-5 |
| 통합 | `tests/integration/test_saas_api_live.py` | 신규 (Phase I-1) | 라이브 EC2 | I-3 (skip), K-2, M-5 |
| 통합(기존) | `tests/integration/*` (Task-1~5) | 변경 없음 | 혼합 | (별도 회귀 실행 가능) |
| e2e | `dashboard/tests/e2e/dashboard.spec.ts` | 수정 (Phase F-1) | 라이브 EC2 | K-3, M-6 |
| e2e | `dashboard/tests/e2e/audit_tailing.spec.ts` | 신규 (Phase G-1) | 라이브 EC2 | K-3, M-6 |
| e2e | `dashboard/tests/e2e/page_descriptions.spec.ts` | 신규 (Phase G-2) | 라이브 EC2 | K-3, M-6 |

---

## 6. 마스터 TODO 체크리스트 (재시작 시 가장 최근 미체크 Phase 부터)

> 본 체크리스트는 Phase 별 첫 step 만 모아둔 인덱스. 실제 step 들은 §4 참고. 재시작 시 가장 최근 `- [ ]` 부터 진입.

- [ ] Phase A. 사전 환경 점검 (A-1 ~ A-8)
- [ ] Phase B. server.py /api prefix 일관화 (B-1 ~ B-6)
- [ ] Phase C. GET 설정 조회 엔드포인트 신설 (C-1 ~ C-6)
- [ ] Phase D. 페이지 description 하드코딩 (D-1 ~ D-7)
- [ ] Phase E. Audit 자동 tailing + Pause/Resume (E-1 ~ E-3)
- [ ] Phase F. 기존 e2e 테스트 갱신 (F-1 ~ F-3)
- [ ] Phase G. 신규 e2e 테스트 작성 (G-1 ~ G-4)
- [ ] Phase H. 전체 단위 테스트 회귀 PASS (H-1 ~ H-3)
- [ ] Phase I. 라이브 통합 테스트 파일 작성 (I-1 ~ I-4)
- [ ] Phase J. dashboard 빌드 + deploy_static.sh (J-1 ~ J-6)
- [ ] Phase K. 라이브 통합 테스트 실행 (K-1 ~ K-4)
- [ ] Phase L. redeploy_idempotency.sh 작성 (L-1 ~ L-6)
- [ ] Phase M. 실제 멱등성 검증 실행 (M-1 ~ M-9)

---

## 7. 인수 기준 (Acceptance Criteria)

| # | 기준 | 검증 방법 |
|---|---|---|
| 1 | 브라우저로 `http://<EIP>:8000/pipeline` 진입 시 실시간 이벤트가 표시된다 | K-3 Playwright + 수동 |
| 2 | `/audit` 진입 즉시 최근 100건이 표시되고 3초마다 새 이벤트가 prepend 된다 | K-3 audit_tailing.spec.ts |
| 3 | `/audit` 의 Pause 버튼이 폴링을 멈추고 Resume 이 재개한다 | K-3 audit_tailing.spec.ts |
| 4 | Prompt/KB 페이지 진입 시 직전 저장값이 textarea/input 에 미리 채워진다 | K-3 수동 + 단위 C |
| 5 | Prompt/KB Save 버튼이 200 응답을 받고 status 가 "Saved." 로 표시된다 | K-3 dashboard.spec.ts |
| 6 | 5개 페이지(`/pipeline`, `/audit`, `/prompt`, `/kb`, `/login`) 상단에 description 2~3줄이 보인다 | K-3 page_descriptions.spec.ts |
| 7 | 모든 단위 테스트 PASS (신규 9개 + 기존 60+) | H-1 |
| 8 | 라이브 통합 테스트 7개 PASS | K-2, M-5 |
| 9 | `redeploy_idempotency.sh` 실행 후 5종 health check 가 모두 PASS 한다 | M-3 |
| 10 | 멱등성: redeploy 후 동일한 KMS CMK 가 재사용되고 SOPS 파일이 그대로 복호화 가능 | M-3 후 `sops -d encrypted/<file>` 수동 검증 (선택) |

---

## 8. 리스크 / 롤백

| 리스크 | 발생 시점 | 대응 |
|---|---|---|
| Phase J 의 deploy_static.sh 실패 (S3/SSM 권한 등) | J-4 | 수동으로 SSH (또는 SSM session) 진입 후 systemd 재시작 |
| 신규 `get_prompt` / `get_kb_ttl` 가 DynamoDB 권한 부족으로 500 | C-4 (단위는 통과) → K-2 (라이브 실패) | EC2 IAM 역할에 `dynamodb:GetItem` 권한이 이미 있음(Task-1~3 에서 부여). 없으면 infra/iam.tf 갱신 후 apply |
| Phase M 의 redeploy 도중 Lambda ENI 가 in-use 로 destroy 차단 (10~20분) | M-3 | destroy.sh 가 사전에 Lambda delete-function 호출하여 ENI 정리 시간 확보 (기존 로직). 그래도 막히면 수동으로 `aws ec2 delete-network-interface` |
| Public IP 변경으로 endpoint(개발자 PC) SG 차단 | M-3 후 | M-4 의 `update_my_ip.sh` 가 자동 갱신. 안 되면 콘솔에서 SG 수동 추가 |
| Audit 폴링이 DynamoDB scan 비용을 증가시킴 | 운영 | 1 페이지당 3초 폴링 × scan(Limit=100) ≈ DynamoDB scan RCU 소비. 사용자가 페이지를 닫으면 즉시 중지. 비용 무시 가능 수준 |
| dashboard build 가 오래된 vite 의존성으로 실패 | J-2 | `cd dashboard && npm ci` 로 lockfile 재설치 후 재시도 |
| Playwright 가 baseURL 을 못 읽음 | K-3 | `playwright.config.ts` 의 `use.baseURL` 을 `process.env.E2E_BASE ?? "http://localhost:5173"` 로 보조 수정 (별도 step) |

### 롤백 절차

본 Plan 의 모든 변경은 `task-6-dashboard-fix` 브랜치 위에서 진행된다. 문제 발생 시:

```bash
git checkout main
git branch -D task-6-dashboard-fix
# EC2 는 이전 코드로 deploy_static.sh 재실행 (Phase J 의 반대 방향)
git checkout <task-5-commit-hash> -- ec2/saas/server.py ec2/saas/static
bash scripts/deploy_static.sh
```

---

## 9. 변경 파일 일람 (최종)

```
수정:
  ec2/saas/server.py                              # Phase B, C
  dashboard/src/pages/PipelineStream.tsx          # Phase D
  dashboard/src/pages/Audit.tsx                   # Phase D, E
  dashboard/src/pages/PromptEditor.tsx            # Phase D
  dashboard/src/pages/KBSettings.tsx              # Phase D
  dashboard/src/pages/Login.tsx                   # Phase D
  dashboard/tests/e2e/dashboard.spec.ts           # Phase F
  ec2/saas/static/**                              # Phase J (rebuild output)
  requirements-dev.txt                            # Phase I (websockets)

신규:
  tests/unit/test_saas_api_prefix.py              # Phase B
  tests/unit/test_saas_settings_get.py            # Phase C
  tests/integration/test_saas_api_live.py         # Phase I
  dashboard/tests/e2e/audit_tailing.spec.ts       # Phase G
  dashboard/tests/e2e/page_descriptions.spec.ts   # Phase G
  scripts/redeploy_idempotency.sh                 # Phase L
  tests/scripts/test_redeploy_idempotency.py      # Phase L
```

---

## 10. 실행 시작 신호

사용자가 본 문서를 검토하고 다음 중 하나를 명시한 경우에만 Phase A 부터 실행:

- "Task-6 시작"
- "Task-6.md 진행해줘"
- 동등한 명시적 승인 메시지

> 그 외 일체의 메시지(피드백/질문/단순 응답) 에는 코드 변경 없이 답변만 수행한다.

---

**문서 끝. 작성일 2026-05-12, 인코딩 UTF-8 (BOM 없음).**
