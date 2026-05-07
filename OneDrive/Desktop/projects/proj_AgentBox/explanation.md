# AgentBox — 동작 원리, 데이터 흐름, 기술 용어

## 1. 한 줄 요약

AgentBox는 Claude Code CLI와 Anthropic 서버 사이에 끼어들어, 모든 AI 요청을 **사람이 Allow/Block할 때까지 실시간으로 멈추는** 로컬 HITL(Human-In-The-Loop) 프록시다.

---

## 2. 전체 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│  WSL2 Ubuntu                                                    │
│                                                                 │
│  ┌──────────────┐                                               │
│  │  claude CLI  │  (Node.js 프로세스)                            │
│  └──────┬───────┘                                               │
│         │ HTTPS 요청                                             │
│         │ (env: HTTPS_PROXY=http://127.0.0.1:8080)              │
│         │ (env: NODE_EXTRA_CA_CERTS=certs/agentbox-ca.crt)      │
│         ▼                                                       │
│  ┌──────────────────────────────────────┐                       │
│  │  mitmproxy :8080  (AgentBoxAddon)   │                       │
│  │                                      │                       │
│  │  1. TLS 복호화 (동적 leaf cert 발급) │                       │
│  │  2. request 후킹                     │                       │
│  │  3. api.anthropic.com + /v1/messages │                       │
│  │     만 필터링                         │                       │
│  │  4. HITLQueue.wait(event_id) ──────► PENDING (asyncio.Future)│
│  │     ↑ 여기서 요청이 멈춤              │                       │
│  └──────┬───────────────────────────────┘                       │
│         │ 공유 메모리 (같은 asyncio 루프)                        │
│         ▼                                                       │
│  ┌────────────────────────────────────┐                         │
│  │  FastAPI + uvicorn :8000           │                         │
│  │                                    │                         │
│  │  ┌─────────┐   ┌────────────────┐  │                         │
│  │  │ SQLite  │   │ WebSocket /ws  │  │                         │
│  │  │(events) │   │ (WSHub)        │──┼──► Browser UI           │
│  │  └────┬────┘   └───────┬────────┘  │    (실시간 tailing)     │
│  │       │                │            │         │               │
│  │  ┌────▼────────────────▼────────┐  │         │               │
│  │  │ HITLQueue (asyncio.Future)   │  │         │ Allow / Block  │
│  │  │  .wait()  ←→  .resolve()    │◄─┼─────────┘               │
│  │  └─────────────────────────────┘  │   POST /verdict/{id}     │
│  └────────────────────────────────────┘                         │
│         │ verdict == allow                                       │
│         ▼                                                       │
│  mitmproxy가 요청을 upstream으로 forward                         │
│         │                                                       │
└─────────┼───────────────────────────────────────────────────────┘
          │ TLS (실제 인터넷)
          ▼
   api.anthropic.com
```

### 단계별 설명

| 단계 | 무슨 일이 일어나는가 |
|------|----------------------|
| **①** | `claude --print "..."` 실행 → Node.js가 `HTTPS_PROXY` 환경변수를 읽어 `127.0.0.1:8080`으로 CONNECT 터널 연결 |
| **②** | mitmproxy가 CONNECT 요청을 받아 클라이언트에게 **agentbox-ca.crt로 서명된 가짜 leaf 인증서** 제시 → TLS 핸드셰이크 성공 (Node.js는 `NODE_EXTRA_CA_CERTS`로 이 CA를 신뢰) |
| **③** | mitmproxy가 클라이언트 요청을 평문으로 복호화 → `AgentBoxAddon.request()` 훅 호출 |
| **④** | Addon이 `api.anthropic.com/v1/messages`인지 확인 → 해당하면 `PromptEvent` 생성, SQLite 저장, WebSocket 브로드캐스트 |
| **⑤** | `HITLQueue.wait(event_id, timeout=300s)` 호출 → asyncio.Future가 완료될 때까지 요청을 블로킹 (mitmproxy는 이 코루틴이 끝날 때까지 upstream으로 forward하지 않음) |
| **⑥** | Browser UI가 WebSocket으로 PENDING 이벤트 수신 → 사용자에게 표시 |
| **⑦** | 사용자가 Allow/Block 클릭 → `POST /verdict/{id}` → `HITLQueue.resolve(event_id, verdict)` |
| **⑧** | asyncio.Future가 완료됨 → `wait()` 반환 → verdict에 따라 분기: `allow`이면 return(forward), `block`이면 `flow.response = 403` |

---

## 3. 컴포넌트 맵

```
proj_AgentBox/
├── src/agentbox/
│   ├── __main__.py        ← CLI 진입점 (agentbox run / ca / setup)
│   ├── config.py          ← 환경변수 설정 (포트, 경로)
│   ├── models.py          ← Pydantic 데이터 모델
│   ├── storage.py         ← SQLite CRUD (aiosqlite)
│   ├── logging_setup.py   ← loguru 구조화 로깅
│   ├── proxy/
│   │   ├── ca.py          ← Root CA 생성/관리
│   │   ├── addon.py       ← mitmproxy 훅 (핵심 로직)
│   │   └── master.py      ← DumpMaster 부팅
│   ├── api/
│   │   ├── server.py      ← FastAPI 앱 팩토리
│   │   ├── routes.py      ← REST 엔드포인트
│   │   ├── ws.py          ← WebSocket 브로드캐스터
│   │   └── hitl.py        ← asyncio.Future 기반 HITL 큐
│   └── ui/
│       └── templates/
│           └── index.html ← 바닐라 JS 대시보드
└── scripts/
    ├── activate.sh        ← source하면 프록시 시작 + env var 설정
    └── deactivate.sh      ← source하면 프록시 종료 + env var 해제
```

---

## 4. 사용된 기술과 역할

### mitmproxy
Python 기반 오픈소스 TLS MITM(Man-in-the-Middle) 프록시. 클라이언트와 서버 사이에서 HTTPS 트래픽을 복호화하고 Python 코드(addon)로 조작할 수 있다.

- **DumpMaster**: mitmproxy의 실행 엔진. 비대화형(headless)으로 동작.
- **Addon**: `request()`, `response()` 등 훅을 구현하는 Python 클래스. `async def request()` 형태로 asyncio와 통합.
- **동적 leaf 인증서**: mitmproxy가 접속 도메인별로 즉석에서 서버 인증서를 위조. Root CA가 이를 서명하므로, CA를 신뢰하는 클라이언트는 검증 통과.

### asyncio (Python 표준 라이브러리)
Python의 단일 스레드 비동기 I/O 프레임워크. AgentBox는 하나의 asyncio 이벤트 루프에서 mitmproxy와 uvicorn을 `asyncio.gather()`로 동시 실행한다.

- **Future**: 나중에 완료될 값의 자리표시자. `HITLQueue`는 이를 이용해 verdict 대기를 구현한다.
- **gather()**: 여러 코루틴을 병렬로 실행하되 모두 같은 이벤트 루프에서 돌림.

### FastAPI + uvicorn
FastAPI: Python 타입 힌트 기반 웹 프레임워크. REST API와 WebSocket을 모두 지원.  
uvicorn: ASGI 서버. FastAPI 앱을 asyncio 위에서 구동.

### WebSocket
HTTP를 업그레이드해 만드는 양방향 지속 연결. 브라우저가 `/ws`에 연결한 채로 있으면, 서버(WSHub)가 새 이벤트 발생 시 즉시 push할 수 있다. 폴링(polling) 없이 실시간 tailing을 구현하는 핵심.

### SQLite + aiosqlite
SQLite: 파일 하나가 DB인 경량 관계형 DB. 별도 서버 불필요.  
aiosqlite: SQLite를 asyncio 코루틴으로 감싼 비동기 드라이버.

### Pydantic v2
Python 타입 힌트로 데이터 검증과 직렬화를 처리하는 라이브러리. `PromptEvent`, `Verdict`, `WSMessage`가 모두 Pydantic 모델이다.

### loguru
Python 로깅 라이브러리. `logger.info("event_created", event_id=..., url=...)` 형태로 구조화된 JSON 로그를 `logs/agentbox.log`에 기록한다.

### X.509 / TLS
HTTPS의 인증서 표준. AgentBox는 Root CA 인증서를 생성하고, 각 도메인별로 이 CA가 서명한 leaf 인증서를 동적으로 발급한다. 클라이언트가 이 CA를 신뢰하면 위조된 인증서를 진짜로 받아들인다.

---

## 5. 핵심 용어 정리

| 용어 | 의미 |
|------|------|
| **MITM (Man-in-the-Middle)** | 두 통신 주체 사이에 끼어 트래픽을 투명하게 감청/조작하는 기법. 여기서는 보안 연구/감사 목적으로 로컬에서만 사용. |
| **HITL (Human-In-The-Loop)** | 자동화된 흐름에 사람의 판단을 삽입하는 패턴. 요청이 AI를 거치기 전에 사람이 최종 승인/거부. |
| **HTTPS_PROXY** | HTTP/HTTPS 클라이언트가 프록시 서버를 경유하도록 지정하는 환경변수. Node.js, curl, Python requests 등 대부분의 HTTP 클라이언트가 이를 인식. |
| **NODE_EXTRA_CA_CERTS** | Node.js 전용 환경변수. 시스템 trust store에 없는 추가 CA 인증서를 지정. Claude Code(Node 기반)가 agentbox-ca.crt를 신뢰하게 만드는 핵심. |
| **Root CA** | 다른 인증서를 서명할 수 있는 최상위 인증 기관 인증서. 한 번 trust store에 등록하면, 이 CA가 서명한 모든 인증서를 자동 신뢰. |
| **Leaf Certificate** | 특정 도메인(예: api.anthropic.com)에 대해 발급된 최종 서버 인증서. Root CA가 서명. |
| **asyncio.Future** | 아직 완료되지 않은 비동기 연산의 자리표시자. `fut.set_result(verdict)`로 완료, `await fut`으로 대기. HITLQueue의 핵심 메커니즘. |
| **ASGI** | Asynchronous Server Gateway Interface. Python 비동기 웹 앱의 표준 인터페이스. FastAPI는 ASGI 프레임워크, uvicorn은 ASGI 서버. |
| **Addon (mitmproxy)** | mitmproxy에 등록되는 Python 클래스. 훅 메서드(`request`, `response`, `tls_start` 등)를 구현해 트래픽을 조작. |
| **DumpMaster** | mitmproxy의 비대화형 실행 모드. 터미널 UI 없이 addon만으로 동작하며 asyncio와 통합 가능. |
| **WebSocket Broadcast** | 서버가 연결된 모든 WebSocket 클라이언트에게 동시에 메시지를 전송. WSHub가 연결 집합을 관리하고 이벤트 발생 시 일괄 송신. |
| **aiosqlite** | SQLite를 asyncio로 감싼 드라이버. `await db.execute()`처럼 non-blocking으로 DB 쿼리 가능. |
| **Verdict** | 사람이 내린 판정: `allow`(허용, forward) 또는 `block`(차단, 403 반환). |
| **Pending** | HITL 큐에 들어갔으나 아직 verdict를 받지 못한 상태. 이 동안 요청은 upstream으로 가지 않고 멈춰 있음. |
| **CONNECT 터널** | HTTPS 프록시의 동작 방식. 클라이언트가 `CONNECT api.anthropic.com:443`을 프록시에 보내면, 프록시가 TCP 터널을 생성하고 그 위에서 TLS 핸드셰이크가 진행됨. |

---

## 6. 프로세스 토폴로지

```
단일 Python 프로세스
└── asyncio.run(_main())
    └── asyncio.gather(
            start_master(addon, port=8080),   ← mitmproxy DumpMaster
            uvicorn.Server(...).serve()        ← FastAPI :8000
        )

공유 객체 (같은 메모리, 같은 이벤트 루프):
  HITLQueue  ← addon.hitl_queue == app.state.hitl_queue (동일 인스턴스)
  WSHub      ← addon.ws_hub    == app.state.ws_hub      (동일 인스턴스)
```

mitmproxy와 uvicorn이 **같은 asyncio 이벤트 루프**에서 돌기 때문에 IPC(프로세스 간 통신) 없이 메모리 공유만으로 HITLQueue를 통해 결합된다.

---

## 7. 활성화/비활성화 흐름

```
agentbox on  (shell 함수, ~/.bashrc에 등록됨)
  └── source scripts/activate.sh
        ├── CA 없으면 agentbox ca 실행 → certs/ 생성
        ├── trust store에 CA 없으면 install_ca.sh 실행 (sudo)
        ├── port 8080 미사용이면 nohup agentbox run & → .agentbox.pid 저장
        ├── export HTTPS_PROXY=http://127.0.0.1:8080
        └── export NODE_EXTRA_CA_CERTS=certs/agentbox-ca.crt

agentbox off  (shell 함수)
  └── source scripts/deactivate.sh
        ├── .agentbox.pid 읽어서 kill
        ├── unset HTTPS_PROXY
        └── unset NODE_EXTRA_CA_CERTS
```

> **왜 shell 함수인가?**  
> 자식 프로세스(`agentbox` 실행 파일)는 부모 shell의 환경변수를 변경할 수 없다.  
> `source`는 현재 shell에서 직접 실행되므로 `export`가 부모 환경에 반영된다.  
> `agentbox setup` 명령이 `~/.bashrc`에 이 shell 함수를 주입하는 이유가 이것이다.
