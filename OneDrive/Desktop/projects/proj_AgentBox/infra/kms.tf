# 1D-1: KMS CMK for SOPS encryption/decryption

data "aws_caller_identity" "current" {}

resource "aws_kms_key" "sops" {
  description             = "AgentBox SOPS encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # Full admin access for root account
        Sid    = "RootAdmin"
        Effect = "Allow"
        Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root" }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        # Local developer can encrypt
        Sid    = "DeveloperEncrypt"
        Effect = "Allow"
        Principal = { AWS = data.aws_caller_identity.current.arn }
        Action   = ["kms:Encrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
        Resource = "*"
      },
      {
        # EC2 instance role can decrypt
        Sid    = "EC2Decrypt"
        Effect = "Allow"
        Principal = { AWS = aws_iam_role.ec2.arn }
        Action   = ["kms:Decrypt", "kms:GenerateDataKey"]
        Resource = "*"
      },
    ]
  })

  tags = { Name = "${var.project}-sops-key" }
}

resource "aws_kms_alias" "sops" {
  name          = "alias/${var.project}-sops-key"
  target_key_id = aws_kms_key.sops.key_id
}

output "kms_key_arn" {
  value = aws_kms_key.sops.arn
}
