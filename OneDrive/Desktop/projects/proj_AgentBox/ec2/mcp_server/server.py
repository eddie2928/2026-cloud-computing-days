"""1C-4: EC2 MCP Server - decrypt_and_stage + cleanup endpoints."""
import os
import subprocess
import tempfile
from pathlib import Path

import boto3
import uvicorn
from fastapi import FastAPI, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger
from pydantic import BaseModel

_REGION = os.environ.get("AWS_REGION", "us-east-1")
_PROJECT = os.environ.get("PROJECT_NAME", "agentbox")
_ENCRYPTED_CODE_BUCKET = f"{_PROJECT}-encrypted-code"
_KB_STAGING_BUCKET = f"{_PROJECT}-kb-staging"
_ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")

_s3 = boto3.client("s3", region_name=_REGION)
_security = HTTPBearer()


def _verify_token(credentials: HTTPAuthorizationCredentials = Security(_security)) -> str:
    if _ADMIN_TOKEN and credentials.credentials != _ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials.credentials


app = FastAPI(title="AgentBox MCP Server")


class DecryptRequest(BaseModel):
    project_id: str
    session_id: str


class DecryptResponse(BaseModel):
    kb_bucket: str
    prefix: str


@app.post("/mcp/decrypt_and_stage", response_model=DecryptResponse)
async def decrypt_and_stage(req: DecryptRequest, token: str = Security(_verify_token)):
    """1C-4: S3 encrypted-code -> KMS decrypt (via sops) -> KB staging bucket."""
    session_id = req.session_id
    project_id = req.project_id
    prefix = f"staging/{session_id}/"

    logger.info("decrypt_start", session_id=session_id, project_id=project_id)

    # List encrypted files for this project
    list_resp = _s3.list_objects_v2(
        Bucket=_ENCRYPTED_CODE_BUCKET,
        Prefix=f"encrypted_code/{project_id}/",
    )
    objects = list_resp.get("Contents", [])
    if not objects:
        raise HTTPException(status_code=404,
                            detail=f"No encrypted files found for project: {project_id}")

    for obj in objects:
        key = obj["Key"]
        logger.info("decrypt_file", key=key)

        # Download to temp buffer
        with tempfile.NamedTemporaryFile(suffix=".enc", delete=False) as tmp_enc:
            _s3.download_fileobj(_ENCRYPTED_CODE_BUCKET, key, tmp_enc)
            enc_path = tmp_enc.name

        try:
            # sops --decrypt -> plaintext bytes
            result = subprocess.run(
                ["sops", "--decrypt", "--output-type", "binary", enc_path],
                capture_output=True,
                timeout=30,
            )
            if result.returncode != 0:
                err = result.stderr.decode()
                logger.error("sops_decrypt_error", key=key, stderr=err)
                raise HTTPException(status_code=500, detail=f"Decrypt failed: {err[:200]}")

            buf = bytearray(result.stdout)

            # Upload to KB staging
            rel_name = Path(key).stem  # remove .enc suffix
            kb_key = f"{prefix}{rel_name}"
            _s3.put_object(
                Bucket=_KB_STAGING_BUCKET,
                Key=kb_key,
                Body=bytes(buf),
            )
            logger.info("kb_upload_done", kb_key=kb_key)
        finally:
            # Zero-fill plaintext buffer, remove temp file
            if "buf" in dir():
                buf[:] = b"\x00" * len(buf)
            Path(enc_path).unlink(missing_ok=True)

    logger.info("decrypt_done", session_id=session_id, files=len(objects))
    return DecryptResponse(kb_bucket=_KB_STAGING_BUCKET, prefix=prefix)


@app.delete("/mcp/cleanup/{session_id}")
async def cleanup(session_id: str, token: str = Security(_verify_token)):
    """1C-4: Delete all KB staging objects for a session."""
    prefix = f"staging/{session_id}/"
    list_resp = _s3.list_objects_v2(Bucket=_KB_STAGING_BUCKET, Prefix=prefix)
    objects = list_resp.get("Contents", [])

    if objects:
        _s3.delete_objects(
            Bucket=_KB_STAGING_BUCKET,
            Delete={"Objects": [{"Key": o["Key"]} for o in objects]},
        )
        logger.info("kb_cleanup_done", session_id=session_id, deleted=len(objects))

    return {"deleted": len(objects)}


if __name__ == "__main__":
    from loguru import logger as _log
    _log.add("/opt/agentbox/logs/mcp-server.log", rotation="50 MB")
    port = int(os.environ.get("MCP_PORT", "8443"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
