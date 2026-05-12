"""Encrypt project files with SOPS+KMS and upload to S3."""
import os
import subprocess
import tempfile
from pathlib import Path

import boto3


def encrypt_and_upload(
    src_dir: Path,
    s3_bucket: str,
    project_id: str,
    sops_yaml: Path | None = None,
) -> None:
    """Encrypt all files in src_dir with SOPS and upload to S3.

    Raises:
        FileNotFoundError: sops.yaml not found.
        ValueError: sops.yaml has placeholder KMS ARN.
        subprocess.CalledProcessError: sops returned non-zero exit.
        botocore.exceptions.ClientError: S3/KMS AWS error.
    """
    import boto3

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

    with tempfile.TemporaryDirectory() as tmpdir:
        enc_dir = Path(tmpdir) / "encrypted"
        enc_dir.mkdir()

        files = [f for f in src_dir.rglob("*") if f.is_file()]
        for f in files:
            rel = f.relative_to(src_dir)
            out_path = enc_dir / (str(rel) + ".enc")
            out_path.parent.mkdir(parents=True, exist_ok=True)

            result = subprocess.run(
                ["sops", "--encrypt", "--input-type", "binary",
                 "--output-type", "binary", str(f)],
                capture_output=True,
                cwd=str(sops_yaml.parent),  # so sops picks up .sops.yaml / sops.yaml
            )
            if result.returncode != 0:
                raise subprocess.CalledProcessError(
                    result.returncode, "sops",
                    stderr=result.stderr.decode(errors="replace"),
                )
            out_path.write_bytes(result.stdout)

        s3 = boto3.client("s3", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
        prefix = f"encrypted_code/{project_id}/"
        for enc_file in sorted(enc_dir.rglob("*.enc")):
            key = prefix + str(enc_file.relative_to(enc_dir)).replace("\\", "/")
            s3.put_object(Bucket=s3_bucket, Key=key, Body=enc_file.read_bytes())
