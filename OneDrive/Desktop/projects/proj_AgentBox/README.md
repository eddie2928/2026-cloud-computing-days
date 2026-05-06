# AgentBox — Local HITL Sandbox for Claude Code

Local TLS-intercept proxy that sits between Claude Code and `api.anthropic.com`.
Every API request is held **PENDING** until you click **Allow** or **Block** in the web UI.

---

## Quick Start

### 1. Prerequisites

- WSL2 Ubuntu 22.04
- Python 3.11+ inside WSL2

### 2. Install

```bash
# Inside WSL2
cd ~/agentbox          # or wherever you cloned this repo
python3.11 -m venv ~/agentbox-venv
source ~/agentbox-venv/bin/activate
pip install -e ".[dev]"   # or: pip install -e . && pip install pytest pytest-asyncio pytest-cov
```

### 3. Generate CA Certificate

```bash
agentbox ca
# Output: CA certificate ready: certs/agentbox-ca.crt
```

### 4. Register CA in WSL2 System Trust Store

```bash
bash scripts/install_ca.sh
# Verify:
openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt certs/agentbox-ca.crt
```

### 5. Start AgentBox

```bash
agentbox run
# Proxy  →  http://127.0.0.1:8080
# Web UI →  http://localhost:8000
```

Verify both ports are listening:

```bash
ss -ltnp | grep -E ':(8080|8000)'
```

### 6. Configure Claude Code

Open a second terminal in WSL2:

```bash
export HTTPS_PROXY=http://127.0.0.1:8080
export NODE_EXTRA_CA_CERTS=$(pwd)/certs/agentbox-ca.crt
claude --print "테스트 프롬프트입니다"
```

The CLI will **hang** — this is correct. Open `http://localhost:8000` in your browser.
You will see a new **PENDING** entry in the table.

- Click **Allow** → Claude resumes and prints the response.
- Click **Block** → Claude receives a 403 error and exits.

---

## Architecture

```
[claude CLI]
    │  HTTPS_PROXY=http://127.0.0.1:8080
    ▼
[mitmproxy :8080]  ──(AgentBoxAddon)──►  [HITLQueue]  ◄──  POST /verdict/{id}
                                              │                      │
                                         asyncio.Future       FastAPI :8000
                                              │                      │
                                         aiosqlite DB          WebSocket /ws
                                                                     │
                                                               Browser UI
```

All components run in a **single Python process** sharing one asyncio event loop — no IPC.

---

## Running Tests

```bash
# All tests
pytest -v --cov=agentbox --cov-report=term-missing

# Unit tests only
pytest -v tests/unit

# Integration tests only
pytest -v tests/integration
```

Expected: **51 tests pass**, line coverage ≥ 80 %.

---

## Audit Logs

### File log

Structured JSON log with rotation (10 MB / 5 backups):

```
logs/agentbox.log
```

### SQLite database

```
data/agentbox.db
```

Quick queries:

```bash
# Last 20 events
sqlite3 data/agentbox.db \
  "SELECT created_at, status, substr(prompt_excerpt,1,80) FROM events ORDER BY created_at DESC LIMIT 20;"

# Count by status
sqlite3 data/agentbox.db \
  "SELECT status, count(*) FROM events GROUP BY status;"

# Show blocked events
sqlite3 data/agentbox.db \
  "SELECT id, created_at, url FROM events WHERE status='blocked';"
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PROXY_PORT` | `8080` | mitmproxy listen port |
| `API_PORT` | `8000` | FastAPI / Web UI port |
| `DB_PATH` | `data/agentbox.db` | SQLite database path |
| `CA_DIR` | `certs` | CA certificate directory |
| `HITL_TIMEOUT` | `300.0` | Seconds before auto-block on no decision |
| `DEBUG` | `false` | Enables `/dev/seed` endpoint |

Copy `.env.example` to `.env` and edit as needed.

---

## Troubleshooting

### Certificate not trusted (`SSL: CERTIFICATE_VERIFY_FAILED`)

1. Confirm CA was generated: `ls certs/agentbox-ca.crt`
2. Re-run `bash scripts/install_ca.sh`
3. Verify: `openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt certs/agentbox-ca.crt`
4. Set `NODE_EXTRA_CA_CERTS` to the **absolute** path: `export NODE_EXTRA_CA_CERTS=$(realpath certs/agentbox-ca.crt)`

### Port already in use

```bash
# Check what is using port 8080
ss -ltnp | grep 8080
# Kill the process
kill -9 <pid>
```

Or change `PROXY_PORT` / `API_PORT` in `.env`.

### Claude CLI hangs forever (no PENDING in UI)

- Confirm `HTTPS_PROXY` is exported in the same shell where `claude` runs.
- Check `logs/agentbox.log` for `event_created` entries.
- If no entries appear, the proxy is not intercepting — verify `ss -ltnp | grep 8080`.

### HITL timeout (auto-blocked after 5 minutes)

The request is automatically blocked and logged with `status=failed` after `HITL_TIMEOUT` seconds.
Increase it: `export HITL_TIMEOUT=600` or edit `.env`.

### `agentbox run` crashes at startup

Check for import errors:

```bash
python -c "from agentbox.proxy.master import start_master; print('OK')"
python -c "from agentbox.api.server import create_app; print('OK')"
```

---

## Project Structure

```
src/agentbox/
├── __main__.py          # CLI entry point (agentbox run / agentbox ca)
├── config.py            # Pydantic Settings
├── logging_setup.py     # loguru console + file rotation
├── models.py            # PromptEvent, Verdict, WSMessage
├── storage.py           # aiosqlite CRUD
├── proxy/
│   ├── ca.py            # RSA-4096 self-signed CA generation
│   ├── addon.py         # mitmproxy request hook + HITL bridge
│   └── master.py        # DumpMaster boot
├── api/
│   ├── server.py        # FastAPI app factory + lifespan
│   ├── routes.py        # REST + WebSocket endpoints
│   ├── hitl.py          # HITLQueue (asyncio.Future)
│   └── ws.py            # WSHub broadcast
└── ui/
    └── templates/
        └── index.html   # Single-page HITL UI
```
