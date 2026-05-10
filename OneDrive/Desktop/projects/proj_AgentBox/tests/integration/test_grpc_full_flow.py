"""Integration test: full gRPC Inspect flow with mocked MCP + Bedrock."""
import os
import pytest
import responses as resp_lib
from unittest.mock import patch, MagicMock
from moto import mock_aws
import boto3
from datetime import datetime, timezone


PROJECT = "agentbox"
REGION = "us-east-1"
MCP_URL = "http://mcp-int:8080"
ADMIN_TOKEN = "grpc-int-token"


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("PROJECT_NAME", PROJECT)
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    monkeypatch.setenv("MCP_SERVER_URL", MCP_URL)
    monkeypatch.setenv("ADMIN_TOKEN", ADMIN_TOKEN)
    monkeypatch.setenv("BEDROCK_AGENT_ID", "test-agent")
    monkeypatch.setenv("BEDROCK_AGENT_ALIAS_ID", "test-alias")


@mock_aws
@resp_lib.activate
def test_grpc_full_flow_allow(monkeypatch):
    """ALLOW verdict -> cleanup called -> token counter incremented."""
    import importlib
    import ec2.grpc_server.server as srv
    importlib.reload(srv)

    dynamo = boto3.resource("dynamodb", region_name=REGION)
    dynamo.create_table(
        TableName=f"{PROJECT}-settings",
        KeySchema=[{"AttributeName": "key", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "key", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    dynamo.create_table(
        TableName=f"{PROJECT}-events",
        KeySchema=[{"AttributeName": "event_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "event_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    importlib.reload(srv)

    resp_lib.add(
        resp_lib.DELETE,
        f"{MCP_URL}/mcp/cleanup/",
        match_querystring=False,
        status=200,
        json={"deleted": 1},
    )

    fake_chunks = ["verdict: ALLOW context analysis shows no issues"]

    def fake_bedrock(*args, **kwargs):
        return {
            "completion": [{"chunk": {"bytes": c.encode()}} for c in fake_chunks]
        }

    with patch.object(srv._bedrock_runtime, "invoke_agent", side_effect=fake_bedrock):
        servicer = srv.InspectorServicer()
        request = MagicMock()
        request.prompt = "def safe_function(): return True"
        request.user_id = "int-test-user"
        result = servicer.Inspect(request, MagicMock())

    # Cleanup was called
    delete_calls = [c for c in resp_lib.calls if c.request.method == "DELETE"]
    assert len(delete_calls) == 1, "MCP cleanup should be called once"

    # Token counter was incremented
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    table = dynamo.Table(f"{PROJECT}-settings")
    item = table.get_item(Key={"key": f"bedrock_tokens_{today}"})
    assert "Item" in item
    assert int(item["Item"]["value"]) > 0

    # Event was recorded
    events_table = dynamo.Table(f"{PROJECT}-events")
    scan = events_table.scan()
    assert len(scan["Items"]) == 1
