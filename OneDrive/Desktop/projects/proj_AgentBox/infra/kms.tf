# 1D-1: KMS CMK for SOPS encryption/decryption

data "aws_caller_identity" "current" {}

# count=1 on first apply (no existing key), count=0 on re-apply (existing key passed via var)
resource "aws_kms_key" "sops" {
  count                   = var.existing_kms_key_arn == "" ? 1 : 0
  description             = "AgentBox SOPS encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "RootAdmin"
        Effect = "Allow"
        Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root" }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "DeveloperEncrypt"
        Effect = "Allow"
        Principal = { AWS = data.aws_caller_identity.current.arn }
        Action   = ["kms:Encrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
        Resource = "*"
      },
      {
        Sid    = "EC2Decrypt"
        Effect = "Allow"
        Principal = { AWS = aws_iam_role.mcp.arn }
        Action   = ["kms:Decrypt", "kms:GenerateDataKey"]
        Resource = "*"
      },
    ]
  })

  tags = { Name = "${var.project}-sops-key" }
}

# Alias only managed when we own the key (count follows key)
resource "aws_kms_alias" "sops" {
  count         = var.existing_kms_key_arn == "" ? 1 : 0
  name          = "alias/${var.project}-sops-key"
  target_key_id = aws_kms_key.sops[0].key_id
}

locals {
  kms_key_arn = var.existing_kms_key_arn != "" ? var.existing_kms_key_arn : aws_kms_key.sops[0].arn
}

output "kms_key_arn" {
  value = local.kms_key_arn
}
