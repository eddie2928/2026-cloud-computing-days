# 1D-1: S3 buckets - encrypted-code and kb-staging

# Encrypted code bucket (SOPS-encrypted source files)
resource "aws_s3_bucket" "encrypted_code" {
  bucket        = "${var.project}-encrypted-code"
  force_destroy = false
  tags          = { Name = "${var.project}-encrypted-code" }
}

resource "aws_s3_bucket_versioning" "encrypted_code" {
  bucket = aws_s3_bucket.encrypted_code.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "encrypted_code" {
  bucket = aws_s3_bucket.encrypted_code.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.sops.arn
    }
  }
}

resource "aws_s3_bucket_public_access_block" "encrypted_code" {
  bucket                  = aws_s3_bucket.encrypted_code.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# KB staging bucket (temporary plaintext for Bedrock Agent)
resource "aws_s3_bucket" "kb_staging" {
  bucket        = "${var.project}-kb-staging"
  force_destroy = true
  tags          = { Name = "${var.project}-kb-staging" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "kb_staging" {
  bucket = aws_s3_bucket.kb_staging.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.sops.arn
    }
  }
}

resource "aws_s3_bucket_public_access_block" "kb_staging" {
  bucket                  = aws_s3_bucket.kb_staging.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# 1D-1: KB bucket policy - only Bedrock Agent IAM role can read
resource "aws_s3_bucket_policy" "kb_staging" {
  bucket = aws_s3_bucket.kb_staging.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BedrockAgentReadOnly"
        Effect = "Allow"
        Principal = { AWS = aws_iam_role.bedrock_agent.arn }
        Action   = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.kb_staging.arn,
          "${aws_s3_bucket.kb_staging.arn}/*",
        ]
      },
    ]
  })
}

output "encrypted_code_bucket" {
  value = aws_s3_bucket.encrypted_code.id
}

output "kb_staging_bucket" {
  value = aws_s3_bucket.kb_staging.id
}
