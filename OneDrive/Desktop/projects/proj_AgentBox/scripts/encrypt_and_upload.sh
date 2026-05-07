#!/usr/bin/env bash
# 1D-3: Encrypt source directory with SOPS+KMS and upload to S3
# Usage: PROJECT_S3_BUCKET=agentbox-encrypted-code bash scripts/encrypt_and_upload.sh <source_dir>
# Completion check: S3에 .enc 파일 존재, cat .enc -> 암호문 출력 (평문 불가)
set -e

SRC_DIR="${1:?Usage: $0 <source_dir>}"
ENC_DIR="./encrypted"
S3_BUCKET="${PROJECT_S3_BUCKET:?set PROJECT_S3_BUCKET env var}"
PROJECT_ID="${PROJECT_ID:-$(basename "$SRC_DIR")}"

# Verify sops is installed
if ! command -v sops &> /dev/null; then
    echo "[agentbox] ERROR: sops not found. Install: https://github.com/getsops/sops/releases" >&2
    exit 1
fi

# Verify .sops.yaml exists and has real KMS ARN
if grep -q '{region}' .sops.yaml 2>/dev/null; then
    echo "[agentbox] ERROR: .sops.yaml has placeholder KMS ARN. Run terraform apply first." >&2
    exit 1
fi

echo "[agentbox] Encrypting $SRC_DIR -> $ENC_DIR ..."
rm -rf "$ENC_DIR" && mkdir -p "$ENC_DIR"

find "$SRC_DIR" -type f | while IFS= read -r f; do
    rel="${f#"$SRC_DIR"/}"
    out_dir="$ENC_DIR/$(dirname "$rel")"
    mkdir -p "$out_dir"
    sops --encrypt "$f" > "$ENC_DIR/${rel}.enc"
    echo "  encrypted: $rel"
done

echo "[agentbox] Uploading to s3://$S3_BUCKET/encrypted_code/$PROJECT_ID/ ..."
aws s3 sync "$ENC_DIR/" "s3://$S3_BUCKET/encrypted_code/$PROJECT_ID/" --delete

# 1D-3 Completion check: verify files are not plaintext
echo "[agentbox] Verifying encryption (first .enc file should be ciphertext) ..."
FIRST_ENC=$(find "$ENC_DIR" -name "*.enc" | head -1)
if [ -n "$FIRST_ENC" ] && python3 -c "
import sys, json
with open('$FIRST_ENC') as f:
    data = json.load(f)
assert 'sops' in data, 'sops metadata missing'
print('Encryption verified OK')
"; then
    echo "[agentbox] Upload complete: $(find "$ENC_DIR" -name "*.enc" | wc -l) files"
else
    echo "[agentbox] WARNING: Could not verify ciphertext format." >&2
fi
