import time
import pytest
from agentbox.api.server import create_app
from agentbox.config import cfg
from agentbox.models import WSMessage


@pytest.fixture
def sync_app(tmp_path):
    cfg.DB_PATH = str(tmp_path / "test.db")
    cfg.CA_DIR = str(tmp_path / "certs")
    return create_app()


def test_ws_event_created(sync_app):
    from starlette.testclient import TestClient
    msgs = []

    with TestClient(sync_app) as tc:
        with tc.websocket_connect("/ws") as ws:
            tc.post("/dev/seed")
            time.sleep(0.1)
            try:
                msgs.append(ws.receive_json())
            except Exception:
                pass

    assert len(msgs) >= 1
    assert WSMessage.model_validate(msgs[0]).type == "event_created"


def test_ws_verdict_set(sync_app):
    from starlette.testclient import TestClient
    msgs = []

    with TestClient(sync_app) as tc:
        with tc.websocket_connect("/ws") as ws:
            ev_id = tc.post("/dev/seed").json()["id"]
            time.sleep(0.1)
            tc.post("/verdict/{}".format(ev_id), json={"decision": "block"})
            time.sleep(0.1)

            for _ in range(2):
                try:
                    msgs.append(ws.receive_json())
                except Exception:
                    break

    types = [m.get("type") for m in msgs]
    assert "event_created" in types
    assert "verdict_set" in types
