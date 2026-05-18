"""Encrypt project files with SOPS+KMS and upload via EC2 upload-proxy or S3."""
import io
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

import boto3
import requests


def encrypt_local(src_dir: Path, sops_yaml: Path | None = None) -> Path:
    """Encrypt all files in src_dir with SOPS. Returns path to encrypted directory.

    Caller is responsible for removing the returned directory when done.
    """
    src_dir = Path(src_dir).resolve()
    if not src_dir.is_dir():
        raise ValueError(f"Not a directory: {src_dir}")

    if sops_yaml is None:
        from agentbox.dotagentbox import _global_home
        sops_yaml = _global_home() / "sops.yaml"

    if not sops_yaml.exists():
        raise FileNotFoundError(f"sops.yaml not found: {sops_yaml}")

    content = sops_yaml.read_text(encoding="utf-8")
    if "{region}" in content:
        raise ValueError("sops.yaml has placeholder KMS ARN. Run terraform apply first.")

    enc_dir = Path(tempfile.mkdtemp())

    files = [f for f in src_dir.rglob("*") if f.is_file()]
    for f in files:
        rel = f.relative_to(src_dir)
        out_path = enc_dir / (str(rel) + ".enc")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["sops", "--encrypt", "--input-type", "binary",
             "--output-type", "binary", str(f)],
            capture_output=True,
            cwd=str(sops_yaml.parent),
        )
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, "sops",
                stderr=result.stderr.decode(errors="replace"),
            )
        out_path.write_bytes(result.stdout)

    return enc_dir


def upload_via_ec2(
    enc_dir: Path,
    project_id: str,
    ec2_url: str,
    client_cert: str,
    client_key: str,
    ca: str,
) -> None:
    """Zip the encrypted directory and POST to EC2 upload-proxy via mTLS HTTPS."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(Path(enc_dir).rglob("*")):
            if f.is_file():
                zf.write(f, f.relative_to(enc_dir))
    buf.seek(0)

    resp = requests.post(
        f"{ec2_url}/upload",
        data={"project_id": project_id},
        files={"file": ("project.zip", buf, "application/zip")},
        cert=(client_cert, client_key),
        verify=ca,
        timeout=60,
    )
    resp.raise_for_status()


def encrypt_and_upload(
    src_dir: Path,
    s3_bucket: str,
    project_id: str,
    sops_yaml: Path | None = None,
) -> None:
    """Encrypt all files in src_dir with SOPS and upload to S3 (legacy direct path).

    Raises:
        FileNotFoundError: sops.yaml not found.
        ValueError: sops.yaml has placeholder KMS ARN.
        subprocess.CalledProcessError: sops returned non-zero exit.
        botocore.exceptions.ClientError: S3/KMS AWS error.
    """
    enc_dir = encrypt_local(Path(src_dir), sops_yaml)
    try:
        s3 = boto3.client("s3", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
        prefix = f"encrypted_code/{project_id}/"
        for enc_file in sorted(enc_dir.rglob("*.enc")):
            key = prefix + str(enc_file.relative_to(enc_dir)).replace("\\", "/")
            s3.put_object(Bucket=s3_bucket, Key=key, Body=enc_file.read_bytes())
    finally:
        shutil.rmtree(enc_dir, ignore_errors=True)
