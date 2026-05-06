# Task-1: AgentBox Local Sandbox MVP

> 본 문서는 `rough-plan.md`의 Phase 1 중에서, 사용자 협의를 통해 축소된 **로컬 샌드박스 + Claude Code 트래픽 로깅 + Tailing UI + HITL Block 버튼** 범위를 정의한다. 전체 Phase 1+2 구현은 `Task-2.md` 참조.
> 인코딩: 본 문서 및 모든 산출물은 **UTF-8 (BOM 없음)** 으로 통일한다.

---

## 0. 메타 정보

| 항목 | 값 |
|---|---|
| Task ID | Task-1 |
| 작성일 | 2026-05-06 |
| 범위 | Local Sandbox MVP (HTTPS_PROXY 기반 인터셉트) |
| 대상 OS | WSL2 Ubuntu 22.04 (Windows 11 호스트) |
| 대상 클라이언트 | Claude Code CLI (WSL2 내부 실행) |
| 언어 | Python 3.11+ |
| 본 작업 시작 조건 | 사용자 명시적 승인 ("Task-1 시작") |
| 코드 수정 금지 | 사용자 승인 전까지 본 문서 외 어떤 파일도 생성/수정 금지 |

---

## 1. 솔루션 목적 (Scope of Task-1)

### 1.1. 무엇을 만드는가
1. WSL2 Ubuntu 환경에서 동작하는 로컬 TLS 인터셉트 프록시 (`mitmproxy` 기반)
2. Claude Code(`claude` CLI)가 `api.anthropic.com`으로 보내는 모든 HTTPS 요청을 평문으로 가시화
3. 각 요청을 **PENDING 상태로 보류** → 사용자가 Web UI의 Allow/Block 버튼을 누르기 전까지 **Anthropic 서버로 전송되지 않음**
4. Web UI에서 실시간 (Tailing) 로그 스트림 + 승인/차단 액션
5. 모든 이벤트(요청·결정·결과)를 SQLite + 파일 로그로 영속화

### 1.2. 무엇을 만들지 않는가 (Out of scope, → Task-2)
- eBPF / iptables 기반 투명(Transparent) 인터셉트
- AWS EC2 / KMS / Bedrock Agent / Zero-Knowledge 검사
- Multi-user, RBAC, SaaS 다중 테넌시
- 정규식 룰셋 자동 차단 (Task-1은 100% HITL)
- 프로덕션 배포 / 모니터링 / 알람

### 1.3. Success Criteria (반드시 검증 가능)
| # | 기준 | 검증 방법 |
|---|---|---|
| SC-1 | WSL2에서 `agentbox run` 단일 명령으로 프록시(:8080) + API/UI(:8000) 동시 기동 | `ss -ltnp \| grep -E ':(8080\|8000)'` 두 줄 표시 |
| SC-2 | `HTTPS_PROXY` + `NODE_EXTRA_CA_CERTS` 설정 후 `claude --print "hello"` 실행 시 UI에 새 PENDING 항목 출현 | 브라우저 UI에서 prompt 텍스트 확인 |
| SC-3 | UI에서 **Block** 클릭 시 `claude` CLI가 4xx/오류로 종료하고 응답 본문이 Anthropic으로 전달되지 않음 | tcpdump로 api.anthropic.com 향 패킷 부재 확인 |
| SC-4 | UI에서 **Allow** 클릭 시 `claude` CLI가 정상 응답 수신 | CLI에 정상 출력 |
| SC-5 | `pytest tests/` 전체 통과 (단위 + 통합) | exit code 0, coverage 보고서 생성 |
| SC-6 | 로그 파일(`logs/agentbox.log`) 및 SQLite(`data/agentbox.db`)에 모든 이벤트 영속화 | 종료 후 `sqlite3 ... "SELECT count(*) FROM events"` ≥ 1 |

---

## 2. 아키텍처

### 2.1. 데이터 흐름

```
+-----------------------------+
| WSL2 Ubuntu 22.04           |
|                             |
|  [claude CLI]               |
|       |                     |
|       | HTTPS_PROXY=http://127.0.0.1:8080
|       | NODE_EXTRA_CA_CERTS=certs/agentbox-ca.crt
|       v                     |
|  [mitmproxy (addon)]        |  -- :8080
|       |                     |
|       | (in-process call)   |
|       v                     |
|  [HITL Queue (asyncio)]     |
|       |                     |
|       | request_id 발급 + Future 대기
|       |                     |
|       |  +--------> [SQLite events] (audit log)
|       |  |                  |
|       |  +--------> [WebSocket broadcast] --> Browser UI
|       |                     |              (실시간 tailing)
|       |                     |
|       |   <-- POST /verdict/{id} {Allow|Block} -- Browser
|       v                     |
|  verdict == ALLOW           |
|     --> mitmproxy forwards to api.anthropic.com
|  verdict == BLOCK           |
|     --> mitmproxy returns 403, kills flow
|                             |
+-----------------------------+
```

### 2.2. 프로세스 토폴로지
- **단일 Python 프로세스** 내에서 asyncio 이벤트 루프 위에 다음을 동시 구동:
  1. `mitmproxy.tools.dump.DumpMaster` (포트 8080)
  2. `uvicorn` 으로 FastAPI 앱 (포트 8000)
- 프로세스 간 통신 없이 메모리 공유 큐(`HITLQueue`)로 결합 → IPC 제거.

### 2.3. 핵심 컴포넌트와 책임

| 컴포넌트 | 책임 | 파일 |
|---|---|---|
| `proxy.ca` | 로컬 Root CA + 도메인별 leaf 인증서 동적 생성 | `src/agentbox/proxy/ca.py` |
| `proxy.addon` | mitmproxy addon: request 후킹, 평문 추출, HITL 큐 enqueue, verdict에 따라 forward/reject | `src/agentbox/proxy/addon.py` |
| `proxy.master` | mitmproxy DumpMaster 부팅, addon 등록 | `src/agentbox/proxy/master.py` |
| `api.hitl` | `asyncio.Future` 기반 PENDING 큐, `enqueue(event)→Future`, `resolve(id, verdict)` | `src/agentbox/api/hitl.py` |
| `api.routes` | REST: `GET /`, `POST /verdict/{id}`, `GET /events`, `GET /events/{id}` | `src/agentbox/api/routes.py` |
| `api.ws` | WebSocket `/ws` 브로드캐스트 (event_created, verdict_set, completed) | `src/agentbox/api/ws.py` |
| `storage.sqlite` | aiosqlite 기반 events 테이블 CRUD | `src/agentbox/storage.py` |
| `models` | Pydantic v2: `PromptEvent`, `Verdict`, `WSMessage` | `src/agentbox/models.py` |
| `config` | Pydantic Settings: 포트, CA 경로, DB 경로 | `src/agentbox/config.py` |
| `logging_setup` | 구조화 로깅 (loguru) — 콘솔 + `logs/agentbox.log` rotation | `src/agentbox/logging_setup.py` |
| `__main__` | CLI 엔트리: `agentbox run`, `agentbox ca install` | `src/agentbox/__main__.py` |
| Web UI | 단일 `index.html` + 바닐라 JS, WebSocket 클라이언트, Allow/Block 버튼 | `src/agentbox/ui/templates/index.html` |

---

## 3. 기술 스택 및 의존성

### 3.1. 검증된 오픈소스 사용 (직접 작성 금지)
| 영역 | 라이브러리 | 버전 | 사용 이유 |
|---|---|---|---|
| TLS MITM 프록시 | `mitmproxy` | ≥10.2 | 업계 표준, 동적 leaf cert + addon API 제공 |
| 웹 프레임워크 | `fastapi` | ≥0.110 | WebSocket + ASGI 통합, 타입 안전 |
| ASGI 서버 | `uvicorn[standard]` | ≥0.27 | websockets 의존 포함 |
| 데이터 검증 | `pydantic` ≥2 + `pydantic-settings` | ≥2.6 | 타입 모델 |
| DB | `aiosqlite` | ≥0.20 | asyncio 친화 SQLite 드라이버 |
| 인증서 | `cryptography` | ≥42 | X.509 발급 (mitmproxy 내장 CA 재사용 가능하나 명시적 관리 위해 wrap) |
| 로깅 | `loguru` | ≥0.7 | rotation + 구조화 로깅 1줄 설정 |
| 템플릿 | `jinja2` | ≥3.1 | FastAPI 템플릿 |
| HTTP 클라이언트(테스트용) | `httpx` | ≥0.27 | FastAPI TestClient + 비동기 호출 |
| 테스트 러너 | `pytest`, `pytest-asyncio`, `pytest-cov` | 최신 | 단위/통합 테스트 자동화 |
| WS 테스트 | `websockets` | ≥12 | 통합 테스트에서 WebSocket 클라이언트 |
| 외부 서버 mocking | `respx` | ≥0.21 | httpx 기반 HTTP mocking (Anthropic API 호출 시뮬레이션) |

### 3.2. 직접 작성하는 부분 (오픈소스 부재 또는 본 프로젝트 고유 로직)
- HITL 큐 (asyncio.Future 기반) — 매우 단순하므로 직접 구현 (`api/hitl.py`)
- mitmproxy addon (프로젝트 고유 로직)
- Web UI (HTML+JS) — 외부 프레임워크 없이 작성 (50~150줄)

---

## 4. 프로젝트 디렉터리 구조

```
proj_AgentBox/
├── Task-1.md                          # (this)
├── Task-2.md                          # 후속 전체 범위
├── rough-plan.md                      # 원본 기획
├── README.md                          # 사용자 가이드 (Phase G에서 작성)
├── pyproject.toml                     # 패키징, 의존성, console_scripts
├── requirements.txt                   # 핀 고정 의존성 (CI 재현용)
├── requirements-dev.txt               # pytest 등 개발용
├── .gitignore                         # certs/, data/, logs/, __pycache__ 제외
├── .env.example                       # 환경변수 템플릿 (포트 등)
├── certs/                             # 런타임 생성, gitignored
│   └── .gitkeep
├── data/                              # 런타임 SQLite, gitignored
│   └── .gitkeep
├── logs/                              # 런타임 로그, gitignored
│   └── .gitkeep
├── scripts/
│   ├── install_ca.sh                  # WSL2 시스템 trust store 등록
│   └── run.sh                         # `python -m agentbox run` 래퍼
├── src/
│   └── agentbox/
│       ├── __init__.py
│       ├── __main__.py
│       ├── config.py
│       ├── logging_setup.py
│       ├── models.py
│       ├── storage.py
│       ├── proxy/
│       │   ├── __init__.py
│       │   ├── ca.py
│       │   ├── addon.py
│       │   └── master.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── server.py
│       │   ├── routes.py
│       │   ├── ws.py
│       │   └── hitl.py
│       └── ui/
│           ├── templates/
│           │   └── index.html
│           └── static/
│               └── app.js
└── tests/
    ├── __init__.py
    ├── conftest.py                    # 공통 fixture (tmp DB, 큐 인스턴스)
    ├── unit/
    │   ├── __init__.py
    │   ├── test_models.py
    │   ├── test_storage.py
    │   ├── test_hitl_queue.py
    │   ├── test_ca.py
    │   └── test_addon_unit.py
    └── integration/
        ├── __init__.py
        ├── test_api_routes.py
        ├── test_ws_stream.py
        ├── test_proxy_flow.py         # mitmproxy flow mock + addon 통합
        └── test_e2e_block.py          # 진짜 mitmproxy + 진짜 FastAPI + httpx 클라이언트
```

---

## 5. 데이터 모델

### 5.1. SQLite 스키마 (`events` 단일 테이블)
```sql
CREATE TABLE IF NOT EXISTS events (
  id            TEXT PRIMARY KEY,           -- uuid4 hex
  created_at    TEXT NOT NULL,              -- ISO8601 UTC
  resolved_at   TEXT,
  source        TEXT NOT NULL,              -- 'claude_code' | 'unknown'
  method        TEXT NOT NULL,
  url           TEXT NOT NULL,
  request_headers_json  TEXT NOT NULL,
  request_body  TEXT,                       -- 평문 (UTF-8)
  prompt_excerpt TEXT,                      -- 첫 N자 (UI 표시용, 기본 500)
  status        TEXT NOT NULL,              -- 'pending' | 'allowed' | 'blocked' | 'failed'
  verdict_by    TEXT,                       -- 'user' | 'auto' (Task-1은 항상 user)
  upstream_status_code INTEGER,             -- ALLOW 후 forwarded 응답 코드
  error         TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_status_created ON events(status, created_at DESC);
```

### 5.2. Pydantic 모델 (요약)
```python
class PromptEvent(BaseModel):
    id: str
    created_at: datetime
    method: Literal["GET","POST","PUT","DELETE","PATCH"]
    url: HttpUrl
    request_headers: dict[str, str]
    request_body: str | None
    prompt_excerpt: str
    status: Literal["pending","allowed","blocked","failed"]

class Verdict(BaseModel):
    decision: Literal["allow","block"]
    reason: str | None = None

class WSMessage(BaseModel):
    type: Literal["event_created","verdict_set","event_completed"]
    event: PromptEvent
```

---

## 6. 상세 구현 계획 (TODO 체크리스트)

> 각 항목은 **자체 완결적**이며 진입 조건/완료 조건을 명시한다. 중간에 멈춰도 다음 미체크 항목부터 재개한다.
> 진행 상태는 본 파일의 체크박스를 직접 갱신한다(`- [ ]` → `- [x]`).
> 각 Phase 끝에 **Phase Gate** 검증을 통과해야 다음 Phase 진입.

### Phase A — 환경 부트스트랩
- [x] **A1.** WSL2 Ubuntu 22.04 정상 동작 확인
  - 명령: `wsl -d Ubuntu-22.04 -- lsb_release -a`
  - 완료 조건: `Description: Ubuntu 22.04` 출력
  - 재개 키: 본 항목 미체크 시 WSL 미설치/잘못된 배포판 의심
- [x] **A2.** Python 3.11+ 및 venv 준비
  - 명령: `python3.11 -m venv .venv && source .venv/bin/activate && python -V`
  - 완료 조건: `Python 3.11.x` 이상
  - 비고: WSL 홈(~/agentbox-venv)에 venv 생성 (OneDrive 경로 권한 제한으로 인해)
- [x] **A3.** `pyproject.toml` 작성 (패키지명 `agentbox`, console_scripts `agentbox = agentbox.__main__:main`)
  - 검증: `pip install -e .` 성공, `which agentbox` 결과 존재
- [x] **A4.** `requirements.txt` 및 `requirements-dev.txt` 핀 고정 후 설치
  - 검증: `pip check` 충돌 없음, `python -c "import mitmproxy, fastapi, aiosqlite, cryptography, loguru"` 무에러
- [x] **A5.** 디렉터리 골격 생성 (`src/agentbox/...`, `tests/...`, `certs/`, `data/`, `logs/`, `.gitignore`)
  - 검증: `tree -L 3 src tests` 결과가 §4 구조와 일치
- [x] **A6.** `logging_setup.py` 작성 — 콘솔 + `logs/agentbox.log` (10MB rotation, 5 backup)
  - 검증: `python -c "from agentbox.logging_setup import setup; setup(); from loguru import logger; logger.info('boot')"` 후 `logs/agentbox.log` 생성 및 한 줄 기록
- [x] **A7.** `config.py` 작성 — Pydantic Settings (`PROXY_PORT=8080`, `API_PORT=8000`, `DB_PATH=data/agentbox.db`, `CA_DIR=certs`)
  - 검증: 단위 테스트 `test_config_defaults` 통과

**Phase A Gate:** A1~A7 모두 체크. `agentbox --help` 가 에러 없이 종료.

---

### Phase B — 데이터 모델 & 영속 계층
- [x] **B1.** `models.py` 작성 (PromptEvent, Verdict, WSMessage)
  - 검증: `tests/unit/test_models.py` — 정상 입력 직렬화/역직렬화, 잘못된 status enum 거부
- [x] **B2.** `storage.py` 작성 (aiosqlite, `init_db()`, `insert_event()`, `update_verdict()`, `list_events(limit, status)`)
  - 검증: `tests/unit/test_storage.py` — 임시 DB에 insert→list→update→list, 결과 일치 (≥6 케이스)

**Phase B Gate:** `pytest tests/unit/test_models.py tests/unit/test_storage.py -v` 전부 통과.

---

### Phase C — Custom CA & mitmproxy Addon

> 주의: mitmproxy는 자체적으로 `~/.mitmproxy/mitmproxy-ca.pem`을 발급한다. 본 프로젝트에서는 명시적 관리를 위해 `certs/` 하위에 강제 배치하고, 시스템 trust store 설치 스크립트를 별도 제공한다.

- [x] **C1.** `proxy/ca.py` — 다음 함수 구현:
  - `ensure_ca(ca_dir: Path) -> tuple[Path, Path]`: 없으면 RSA 4096 + SHA256 self-signed CA 생성, `agentbox-ca.crt` / `agentbox-ca.key` 반환. `mitmproxy`가 인식할 수 있도록 `mitmproxy-ca.pem` 결합 형식(KEY + CERT)도 함께 출력.
  - 검증: `tests/unit/test_ca.py` — 생성된 cert가 `cryptography.x509.load_pem_x509_certificate`로 파싱되고, `subject == issuer` (self-signed)이며 `key_usage.digital_signature == True`.
- [x] **C2.** `scripts/install_ca.sh` — WSL2 시스템 trust store에 등록
  ```sh
  sudo cp certs/agentbox-ca.crt /usr/local/share/ca-certificates/agentbox-ca.crt
  sudo update-ca-certificates
  ```
  - 검증: 수동. `openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt certs/agentbox-ca.crt` 가 OK.
- [x] **C3.** `proxy/addon.py` — `AgentBoxAddon` 클래스 구현
  - `request(self, flow: http.HTTPFlow)` 후킹
  - 필터: `flow.request.pretty_host` ∈ `{"api.anthropic.com"}` 만 처리, 그 외 pass-through
  - 평문 prompt 추출: `flow.request.get_text()` (mitmproxy가 자동 디코딩)
  - `event = PromptEvent(...)` 생성, `await storage.insert_event(event)`, `await ws_hub.broadcast(event_created)`
  - `verdict = await hitl_queue.wait(event.id, timeout=cfg.HITL_TIMEOUT)` (기본 300초)
  - `verdict == "block"` → `flow.response = http.Response.make(403, b"Blocked by AgentBox", {"content-type":"text/plain"})`
  - `verdict == "allow"` → return (mitmproxy가 upstream으로 forward)
  - timeout/예외 → 안전 차단 (block) + status="failed"
- [x] **C4.** `proxy/master.py` — `start_master(addon, listen_port)` async 함수: `DumpMaster(opts)` 인스턴스화 + `addon` 등록 + `master.run_loop()` 호출
  - 옵션: `confdir=str(ca_dir)`, `listen_port=8080`, `ssl_insecure=False`

**Phase C Gate:** `tests/unit/test_addon_unit.py` 통과 — addon에 mock flow를 주입했을 때 PENDING 이벤트 발행, verdict=allow면 flow 변경 없음, verdict=block이면 `flow.response.status_code == 403`.

---

### Phase D — HITL 큐 & FastAPI

- [x] **D1.** `api/hitl.py` — `HITLQueue`
  ```python
  class HITLQueue:
      def __init__(self) -> None:
          self._futures: dict[str, asyncio.Future[str]] = {}
      def enqueue(self, event_id: str) -> asyncio.Future[str]:
          fut = asyncio.get_event_loop().create_future()
          self._futures[event_id] = fut
          return fut
      def resolve(self, event_id: str, verdict: str) -> bool:
          fut = self._futures.pop(event_id, None)
          if fut and not fut.done(): fut.set_result(verdict); return True
          return False
      async def wait(self, event_id: str, timeout: float) -> str:
          fut = self.enqueue(event_id)
          return await asyncio.wait_for(fut, timeout=timeout)
  ```
  - 검증: `tests/unit/test_hitl_queue.py` — wait+resolve 정상, 미존재 id resolve=False, timeout 발생 시 `asyncio.TimeoutError`
- [x] **D2.** `api/ws.py` — `WSHub` (connection set + broadcast(json) async). 연결 끊김 처리.
  - 검증: 통합 테스트에서 다룸 (D7)
- [x] **D3.** `api/routes.py`
  - `GET /` → Jinja `index.html`
  - `GET /events?status=&limit=50` → SQLite 조회
  - `GET /events/{id}` → 단일 이벤트
  - `POST /verdict/{id}` body `{"decision":"allow|block","reason":...}` → `hitl_queue.resolve()` + `storage.update_verdict()` + WS 브로드캐스트(`verdict_set`)
- [x] **D4.** `api/server.py` — FastAPI 앱 팩토리, lifespan에서 `init_db()`, 의존성 주입(storage, queue, ws_hub)
- [x] **D5.** `__main__.py` — `agentbox run` 명령:
  - asyncio 이벤트 루프 단일 인스턴스에서 `asyncio.gather(start_master(...), uvicorn.Server(uvicorn.Config(app, port=8000)).serve())` 실행
- [x] **D6.** 단위 테스트 `tests/integration/test_api_routes.py` — FastAPI TestClient로 GET/POST 엔드포인트 검증 (≥8 케이스)
- [x] **D7.** 통합 테스트 `tests/integration/test_ws_stream.py` — 클라이언트 WS 연결 → 가짜 이벤트 푸시 → 수신 메시지가 `WSMessage` 스키마와 일치 검증

**Phase D Gate:** `pytest tests/integration/test_api_routes.py tests/integration/test_ws_stream.py -v` 통과.

---

### Phase E — Web UI

- [x] **E1.** `templates/index.html` 작성 — 좌측 이벤트 테이블(시간/메서드/URL/excerpt/status), 우측 상세 패널(헤더/본문/Allow/Block 버튼)
- [x] **E2.** `static/app.js` — 바닐라 JS:
  - `new WebSocket("ws://" + location.host + "/ws")` 연결, `event_created`/`verdict_set` 처리하여 DOM 갱신
  - Allow/Block 버튼: `fetch("/verdict/" + id, {method:"POST", body: JSON.stringify({decision})})`
- [ ] **E3.** 수동 검증: `agentbox run` 후 `http://localhost:8000` 접속, 가짜 POST `/dev/seed` (개발 빌드에서만 노출)로 샘플 이벤트 주입 → 화면에 즉시 표시 → Allow/Block 클릭 시 status 변경

> 주의: `/dev/seed` 라우터는 `config.DEBUG=True` 일 때만 라우팅에 등록한다 (운영 시 미노출).

**Phase E Gate:** 브라우저에서 시드 → Allow → 상태 `allowed`로 갱신; Block → `blocked`. (스크린샷/로그로 증빙)

---

### Phase F — End-to-End 통합 & 자동 테스트

- [x] **F1.** `tests/integration/test_proxy_flow.py` — mitmproxy `HTTPFlow` 객체를 직접 만들어 addon에 주입, asyncio.gather로 verdict resolve를 병렬 호출하여 ALLOW/BLOCK 케이스 각각 검증
- [x] **F2.** `tests/integration/test_e2e_block.py` — **진짜 통합**:
  1. `pytest` fixture로 `agentbox.api.server.create_app()` + 임시 mitmproxy `DumpMaster` 동시 기동 (랜덤 포트)
  2. 백그라운드 태스크: `httpx.AsyncClient(proxy="http://127.0.0.1:<proxy_port>", verify="<ca>")` 로 `https://api.anthropic.com/v1/messages` 호출 시뮬레이션 — 단, upstream은 `respx`로 가로채 200 OK mock 응답을 부여
  3. 테스트 본문: 별도 태스크가 `POST /verdict/{id}` 로 BLOCK 결정
  4. 검증: 클라이언트는 403 수신, DB status=blocked, upstream mock 호출 횟수=0
  5. 동일 시나리오 ALLOW 버전: 클라이언트 200 수신, mock 호출=1, DB status=allowed
- [x] **F3.** 전체 테스트 + 커버리지: `pytest --cov=agentbox --cov-report=term-missing tests/`
  - 완료 조건: 모든 테스트 통과, line coverage ≥ 80%
- [ ] **F4.** **수동 E2E (실제 Claude Code)**:
  1. `agentbox run`
  2. 별도 터미널: `export HTTPS_PROXY=http://127.0.0.1:8080; export NODE_EXTRA_CA_CERTS=$(pwd)/certs/agentbox-ca.crt`
  3. `claude --print "테스트 프롬프트입니다"` 실행 (응답 받지 못하고 hang)
  4. 브라우저에서 PENDING 항목 확인 → **Block** 클릭
  5. claude CLI가 4xx 오류로 종료, `data/agentbox.db` events 테이블에 status=blocked 한 행
  6. 동일 시나리오 ALLOW: claude 정상 응답 출력, status=allowed
  - **사전 확인 필수**: Claude Code 버전이 `HTTPS_PROXY`와 `NODE_EXTRA_CA_CERTS`를 모두 honor하는지 확인. honor하지 않으면 즉시 사용자에게 보고 후 대안 협의(예: `claude --proxy` 플래그 존재 여부, 혹은 cgroup 기반 라우팅으로 우회). **이 사전 확인은 F4 시작 직후 가장 먼저 수행.**

**Phase F Gate:** F1~F3 자동 통과 + F4 수동 시나리오 6단계 모두 OK (스크린샷 또는 콘솔 출력 캡처를 `docs/e2e-evidence.md`에 기록).

---

### Phase G — 문서 및 마무리

- [x] **G1.** `README.md` 작성: 설치, CA 등록, HTTPS_PROXY 설정, Claude Code 사용 예시, 트러블슈팅(인증서 신뢰 실패, 포트 충돌, hang)
- [x] **G2.** 감사 로그 위치 명시 (`logs/agentbox.log`, `data/agentbox.db`) 및 SQL 조회 예시 포함
- [ ] **G3.** `Task-1.md` 본 문서의 모든 체크박스가 `[x]`인지 최종 점검 후 사용자에게 완료 보고

**Phase G Gate:** README의 "Quick Start" 단계대로 따라 했을 때 외부인이 SC-1~SC-6를 재현 가능.

---

## 7. 테스트 전략 상세

### 7.1. 단위 테스트 (`tests/unit/`)
| 파일 | 대상 | 케이스 수(최소) |
|---|---|---|
| `test_models.py` | Pydantic 모델 정상/이상 | 6 |
| `test_storage.py` | SQLite CRUD, idempotent init | 8 |
| `test_hitl_queue.py` | enqueue/resolve/wait/timeout/double-resolve | 6 |
| `test_ca.py` | CA 생성, 영속성, key_usage | 4 |
| `test_addon_unit.py` | mock HTTPFlow + mock queue + mock storage 로 addon 분기 검증 | 6 |

각 단위 테스트는 외부 네트워크/디스크 의존을 최소화한다(SQLite는 `tempfile`).

### 7.2. 통합 테스트 (`tests/integration/`)
| 파일 | 대상 |
|---|---|
| `test_api_routes.py` | FastAPI TestClient — GET/POST/JSON 스키마 검증 |
| `test_ws_stream.py` | WebSocket 연결 + 브로드캐스트 |
| `test_proxy_flow.py` | addon ↔ HITL 큐 ↔ storage 결합 (실제 mitmproxy 객체 사용, 외부 네트워크 없음) |
| `test_e2e_block.py` | DumpMaster + FastAPI 동시 기동, httpx 클라이언트로 실제 프록시 경유 + respx upstream mock |

### 7.3. 수동 E2E
- §6 Phase F4 참조. 수동이지만 단계별 결과 캡처를 의무화하여 회귀 시 비교 가능.

### 7.4. 테스트 자동화 실행
```sh
# 전체
pytest -v --cov=agentbox --cov-report=term-missing
# 단위만
pytest -v tests/unit
# 통합만
pytest -v tests/integration
```

---

## 8. 로깅 & 감사 (CLAUDE.md §5 준수)

- **구조화 로깅**: 모든 이벤트는 (`event_id`, `phase`, `verdict`, `latency_ms`)을 포함한 JSON 라인으로 `logs/agentbox.log`에 기록.
- **DB 감사 로그**: SQLite `events` 테이블이 1차 audit log. (Phase B에서 구축)
- **에러 분기**: addon에서 예기치 않은 예외 발생 시 `logger.exception()` + status="failed" 기록 + 안전 측 차단.
- **로그 뷰어**: Phase G에서 README에 다음 한 줄 가이드를 둔다.
  ```
  sqlite3 data/agentbox.db "SELECT created_at, status, substr(prompt_excerpt,1,80) FROM events ORDER BY created_at DESC LIMIT 20;"
  ```

---

## 9. 위험 & 미해결 가정 (작업 시작 전 사용자 확인 권장)

| ID | 가정/위험 | 대응 |
|---|---|---|
| R1 | Claude Code(Node 기반)가 `HTTPS_PROXY` + `NODE_EXTRA_CA_CERTS`를 모두 존중 | Phase F4 첫 단계에서 **사전 확인**. 불일치 시 즉시 사용자 보고 후 협의 (코드 수정 금지) |
| R2 | mitmproxy 10.x API가 본 문서 작성 시점과 호환 | Phase A4 후 `python -c "from mitmproxy import http; from mitmproxy.tools.dump import DumpMaster"` 으로 import 검증 |
| R3 | WSL2의 `localhost` 가 호스트(Windows)에서 접근 가능해야 브라우저 UI 사용 가능 | WSL2 기본 동작상 가능. 미작동 시 `wsl --version` 확인 후 윈도우 호스트에서 `http://localhost:8000` 검증 |
| R4 | HITL hang으로 Claude Code 클라이언트 측 timeout 발생 | `HITL_TIMEOUT=300` 기본, README에 명시. Claude Code 자체 timeout이 더 짧을 수 있어 운영 시 조정 필요 |
| R5 | Streaming(SSE) 응답을 사용하는 Anthropic API 호출 — request body는 차단 시점에 확인 가능하나 응답 스트리밍은 본 Task 범위 외 | 차단은 request 단계에서 종결되므로 영향 없음. ALLOW 케이스의 스트리밍 응답은 mitmproxy가 자동 처리 |
| R6 | 단일 사용자 가정 — 동시성/RBAC 없음 | 명시적으로 Out of scope (Task-2) |

---

## 10. 재개 프로토콜 (중간 중단 시)

1. 본 파일 §6의 가장 최근 미체크(`- [ ]`) 항목으로 이동.
2. 직전 Phase Gate 검증을 다시 한 번 수행해 회귀가 없는지 확인.
3. `git status`로 의도치 않은 변경 점검.
4. `pytest tests/unit -q` (빠른 회귀 체크) 후 미체크 항목부터 진행.

---

## 11. 코드 수정 금지 — 시작 조건

- 본 문서를 사용자가 검토 후 명시적으로 **"Task-1 시작"** 이라고 지시하기 전까지, 본 디렉터리 내 **어떠한 파일(코드/스크립트/설정)도 생성·수정하지 않는다.**
- 단, 본 `Task-1.md` 자체와 `Task-2.md` 작성 또는 본 문서 수정 요청은 예외.

---

## 12. 부록 A — 의존성 요약 (`requirements.txt` 초안)

```
mitmproxy>=10.2,<11
fastapi>=0.110,<1.0
uvicorn[standard]>=0.27
pydantic>=2.6
pydantic-settings>=2.2
aiosqlite>=0.20
cryptography>=42
loguru>=0.7
jinja2>=3.1
httpx>=0.27
```

`requirements-dev.txt`:
```
-r requirements.txt
pytest>=8
pytest-asyncio>=0.23
pytest-cov>=5
respx>=0.21
websockets>=12
```

---

## 13. 부록 B — Phase Gate 빠른 점검표

| Gate | 명령 | 기대 |
|---|---|---|
| A | `agentbox --help` | 도움말 출력 |
| B | `pytest tests/unit/test_models.py tests/unit/test_storage.py -q` | OK |
| C | `pytest tests/unit/test_ca.py tests/unit/test_addon_unit.py -q` | OK |
| D | `pytest tests/integration/test_api_routes.py tests/integration/test_ws_stream.py -q` | OK |
| E | 수동: 브라우저에서 시드→Allow/Block | 상태 갱신 |
| F | `pytest --cov=agentbox -q` + 수동 E2E | 모두 OK, cov ≥ 80% |
| G | README Quick Start 따라하기 | 외부인 재현 가능 |
