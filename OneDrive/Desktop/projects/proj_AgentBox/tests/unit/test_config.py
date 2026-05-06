from agentbox.config import Settings


def test_config_defaults():
    s = Settings()
    assert s.PROXY_PORT == 8080
    assert s.API_PORT == 8000
    assert s.DB_PATH == "data/agentbox.db"
    assert s.CA_DIR == "certs"
    assert s.HITL_TIMEOUT == 300.0
    assert s.DEBUG is False


def test_config_env_override(monkeypatch):
    monkeypatch.setenv("PROXY_PORT", "9090")
    monkeypatch.setenv("API_PORT", "9000")
    s = Settings()
    assert s.PROXY_PORT == 9090
    assert s.API_PORT == 9000
