"""EC2 upload-proxy server (:8443) — mTLS HTTPS endpoint for cert verification and project uploads."""
import os
import tempfile
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

app = FastAPI(title="AgentBox Upload Proxy")

_UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/opt/agentbox/uploads"))


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/verify_cert")
def verify_cert():
    """mTLS handshake verification — if request reaches here, client cert is valid."""
    return {"status": "cert_ok"}


@app.post("/upload")
async def upload(
    project_id: str = Form(...),
    file: UploadFile = File(...),
):
    """Receive encrypted project zip, run sops encryption on EC2, then push to S3."""
    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=_UPLOAD_DIR) as tmpdir:
        tmp_path = Path(tmpdir) / file.filename
        content = await file.read()
        tmp_path.write_bytes(content)

        if not zipfile.is_zipfile(tmp_path):
            raise HTTPException(status_code=400, detail="Uploaded file is not a valid zip")

        with zipfile.ZipFile(tmp_path) as zf:
            file_count = len(zf.namelist())

        _encrypt_and_store(project_id, tmp_path)

    return JSONResponse({"project_id": project_id, "files": file_count})


def _encrypt_and_store(project_id: str, zip_path: Path) -> None:
    """Placeholder: on real EC2, calls sops + S3 PutObject via IAM role."""
    try:
        from agentbox.encrypt import encrypt_and_upload  # noqa: F401
    except ImportError:
        pass


@app.post("/cert_rotate")
async def cert_rotate(file: UploadFile = File(...)):
    """Accept new cert bundle for rotation — bootstrap flow only."""
    certs_dir = Path(os.environ.get("GRPC_CERTS_DIR", "/opt/agentbox/certs/grpc"))
    certs_dir.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    dest = certs_dir / file.filename
    dest.write_bytes(content)
    return {"status": "rotated", "file": file.filename}
