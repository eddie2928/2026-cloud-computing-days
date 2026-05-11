"""Lambda MCP Bridge - Bedrock Action Group handler.
Routes list_project_files -> GET /mcp/list_files/{pid}
Routes decrypt_and_stage  -> POST /mcp/decrypt_and_stage
"""
import json
import os
import urllib.request


def handler(event, ctx):
    fn_name = event.get("function", "")
    params = {p["name"]: p["value"] for p in event.get("parameters", [])}
    project_id = params.get("project_id", "default")
    mcp = os.environ["MCP_SERVER_URL"]
    headers = {"Authorization": f"Bearer {os.environ.get('MCP_ADMIN_TOKEN', '')}"}

    if fn_name == "list_project_files":
        url = f"{mcp}/mcp/list_files/{project_id}"
        req = urllib.request.Request(url, method="GET", headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")

    elif fn_name == "decrypt_and_stage":
        files_csv = params.get("files", "")
        files = [f.strip() for f in files_csv.split(",") if f.strip()]
        start_byte = int(params.get("start_byte", "0"))
        max_bytes = int(params.get("max_bytes", "20480"))
        payload = json.dumps({
            "project_id": project_id,
            "files": files,
            "start_byte": start_byte,
            "max_bytes": max_bytes,
        }).encode()
        req = urllib.request.Request(
            f"{mcp}/mcp/decrypt_and_stage",
            data=payload,
            method="POST",
            headers={**headers, "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")

    else:
        body = json.dumps({"error": f"unknown function: {fn_name}"})

    return {
        "response": {
            "actionGroup": event["actionGroup"],
            "function": fn_name,
            "functionResponse": {"responseBody": {"TEXT": {"body": body}}},
        }
    }
