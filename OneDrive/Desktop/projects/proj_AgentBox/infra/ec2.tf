# 1C-1: EC2 instance, Elastic IP, security group, IAM role

# Security Group
resource "aws_security_group" "ec2" {
  name        = "${var.project}-ec2-sg"
  description = "AgentBox EC2 security group"
  vpc_id      = aws_vpc.main.id

  # gRPC from Endpoint only
  ingress {
    from_port   = 50051
    to_port     = 50051
    protocol    = "tcp"
    cidr_blocks = [var.endpoint_cidr]
    description = "gRPC mTLS from Endpoint"
  }

  # MCP server from Lambda (VPC CIDR covers Lambda ENI)
  ingress {
    from_port   = 8443
    to_port     = 8443
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
    description = "MCP from Lambda (same VPC)"
  }

  # SaaS dashboard from admin
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = [var.admin_cidr]
    description = "SaaS dashboard admin access"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound (Bedrock, S3, DynamoDB via IGW)"
  }

  tags = { Name = "${var.project}-ec2-sg" }
}

# IAM Role
resource "aws_iam_role" "ec2" {
  name = "${var.project}-ec2-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "ec2" {
  name = "${var.project}-ec2-policy"
  role = aws_iam_role.ec2.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "KMSDecrypt"
        Effect = "Allow"
        Action = ["kms:Decrypt", "kms:GenerateDataKey"]
        Resource = [aws_kms_key.sops.arn]
      },
      {
        Sid    = "S3EncryptedCode"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.encrypted_code.arn,
          "${aws_s3_bucket.encrypted_code.arn}/*",
        ]
      },
      {
        Sid    = "S3KBStaging"
        Effect = "Allow"
        Action = ["s3:PutObject", "s3:DeleteObject", "s3:GetObject"]
        Resource = ["${aws_s3_bucket.kb_staging.arn}/*"]
      },
      {
        Sid    = "BedrockInvokeAgent"
        Effect = "Allow"
        Action = ["bedrock:InvokeAgent", "bedrock-agent-runtime:InvokeAgent"]
        Resource = ["*"]
      },
      {
        Sid    = "DynamoDB"
        Effect = "Allow"
        Action = ["dynamodb:PutItem", "dynamodb:Query", "dynamodb:GetItem", "dynamodb:UpdateItem"]
        Resource = [
          aws_dynamodb_table.events.arn,
          "${aws_dynamodb_table.events.arn}/index/*",
          aws_dynamodb_table.settings.arn,
        ]
      },
    ]
  })
}

resource "aws_iam_instance_profile" "ec2" {
  name = "${var.project}-ec2-profile"
  role = aws_iam_role.ec2.name
}

# EC2 Instance
resource "aws_instance" "main" {
  ami                    = var.ec2_ami
  instance_type          = var.ec2_instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.ec2.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2.name

  user_data = templatefile("${path.module}/userdata.sh.tpl", {
    project      = var.project
    region       = var.aws_region
    admin_token  = var.admin_token
  })

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }

  tags = { Name = "${var.project}-ec2" }
}

# Elastic IP
resource "aws_eip" "main" {
  instance = aws_instance.main.id
  domain   = "vpc"
  tags     = { Name = "${var.project}-eip" }
}

output "ec2_public_ip" {
  value = aws_eip.main.public_ip
}

output "saas_url" {
  value = "http://${aws_eip.main.public_ip}:8000"
}
