import os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")


def test_dns_rebinding_protection_disabled():
    from mcp_server.main import mcp
    ts = mcp.settings.transport_security
    assert ts is not None
    assert ts.enable_dns_rebinding_protection is False
