"""2A-2: Lambda MCP Bridge - Bedrock Action Group handler.
Receives Bedrock Agent action group event -> calls EC2 MCP Server decrypt_and_stage.
"""
import json
import os
import urllib.request


def handler(event, ctx):
    params = {p["name"]: p["value"] for p in event.get("parameters", [])}
    project_id = params.get("project_id", "default")
    session_id = event.get("sessionId", "unknown")

    mcp_url = os.environ["MCP_SERVER_URL"]
    body = json.dumps({"project_id": project_id, "session_id": session_id}).encode()

    req = urllib.request.Request(
        f"{mcp_url}/mcp/decrypt_and_stage",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('MCP_ADMIN_TOKEN', '')}",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())

    return {
        "response": {
            "actionGroup": event["actionGroup"],
            "function": event["function"],
            "functionResponse": {
                "responseBody": {"TEXT": {"body": json.dumps(data)}}
            },
        }
    }
