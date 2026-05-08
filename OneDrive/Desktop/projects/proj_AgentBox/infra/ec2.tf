# 3A-2: Split into app-EC2 and mcp-EC2 with separate SG/IAM

# ─── App Security Group ────────────────────────────────────────────────────────
resource "aws_security_group" "app" {
  name        = "${var.project}-app-sg"
  description = "AgentBox app-EC2 security group"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 50051
    to_port     = 50051
    protocol    = "tcp"
    cidr_blocks = [var.endpoint_cidr]
    description = "gRPC mTLS from Endpoint"
  }

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

  tags = { Name = "${var.project}-app-sg" }
}

# ─── MCP Security Group ────────────────────────────────────────────────────────
resource "aws_security_group" "mcp" {
  name        = "${var.project}-mcp-sg"
  description = "AgentBox mcp-EC2 security group"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port                = 8080
    to_port                  = 8080
    protocol                 = "tcp"
    source_security_group_id = aws_security_group.lambda.id
    description              = "MCP from Lambda (SG-as-source)"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound (KMS, S3 via IGW)"
  }

  tags = { Name = "${var.project}-mcp-sg" }
}

# ─── App IAM Role ─────────────────────────────────────────────────────────────
resource "aws_iam_role" "app" {
  name = "${var.project}-app-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "app" {
  name = "${var.project}-app-policy"
  role = aws_iam_role.app.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BedrockInvokeAgent"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock-agent-runtime:InvokeAgent",
          "bedrock-agent:UpdateAgent",
        ]
        Resource = ["*"]
      },
      {
        Sid    = "DynamoDB"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
        ]
        Resource = [
          aws_dynamodb_table.events.arn,
          "${aws_dynamodb_table.events.arn}/index/*",
          aws_dynamodb_table.settings.arn,
        ]
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "app_ssm" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "app_cw" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_instance_profile" "app" {
  name = "${var.project}-app-profile"
  role = aws_iam_role.app.name
}

# ─── MCP IAM Role ─────────────────────────────────────────────────────────────
resource "aws_iam_role" "mcp" {
  name = "${var.project}-mcp-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "mcp" {
  name = "${var.project}-mcp-policy"
  role = aws_iam_role.mcp.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "KMSDecrypt"
        Effect = "Allow"
        Action = ["kms:Decrypt", "kms:GenerateDataKey"]
        Resource = [local.kms_key_arn]
      },
      {
        Sid    = "S3EncryptedCodeRead"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.encrypted_code.arn,
          "${aws_s3_bucket.encrypted_code.arn}/*",
        ]
      },
      {
        Sid    = "S3KBStagingRW"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:GetObject",
          "s3:ListBucket",
        ]
        Resource = [
          aws_s3_bucket.kb_staging.arn,
          "${aws_s3_bucket.kb_staging.arn}/*",
        ]
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "mcp_ssm" {
  role       = aws_iam_role.mcp.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "mcp_cw" {
  role       = aws_iam_role.mcp.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_instance_profile" "mcp" {
  name = "${var.project}-mcp-profile"
  role = aws_iam_role.mcp.name
}

# ─── App EC2 Instance ─────────────────────────────────────────────────────────
resource "aws_instance" "app" {
  ami                         = var.ec2_ami
  instance_type               = "t3.micro"
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.app.id]
  iam_instance_profile        = aws_iam_instance_profile.app.name
  user_data_replace_on_change = true

  user_data = templatefile("${path.module}/userdata-app.sh.tpl", {
    project               = var.project
    region                = var.aws_region
    admin_token           = var.admin_token
    code_s3_uri           = "s3://${aws_s3_bucket.encrypted_code.id}/${aws_s3_object.code.key}"
    bedrock_agent_id      = aws_bedrockagent_agent.inspector.id
    bedrock_agent_alias_id = aws_bedrockagent_agent_alias.live.agent_alias_id
    mcp_private_ip        = aws_instance.mcp.private_ip
  })

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }

  tags = { Name = "${var.project}-app" }
}

# ─── MCP EC2 Instance ─────────────────────────────────────────────────────────
resource "aws_instance" "mcp" {
  ami                         = var.ec2_ami
  instance_type               = "t3.small"
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.mcp.id]
  iam_instance_profile        = aws_iam_instance_profile.mcp.name
  user_data_replace_on_change = true

  user_data = templatefile("${path.module}/userdata-mcp.sh.tpl", {
    project     = var.project
    region      = var.aws_region
    admin_token = var.admin_token
    code_s3_uri = "s3://${aws_s3_bucket.encrypted_code.id}/${aws_s3_object.code.key}"
  })

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }

  tags = { Name = "${var.project}-mcp" }
}

# ─── Outputs ──────────────────────────────────────────────────────────────────
output "app_public_ip" {
  value = aws_instance.app.public_ip
}

output "mcp_public_ip" {
  value = aws_instance.mcp.public_ip
}

output "mcp_private_ip" {
  value = aws_instance.mcp.private_ip
}

output "app_instance_id" {
  value = aws_instance.app.id
}

output "mcp_instance_id" {
  value = aws_instance.mcp.id
}

output "saas_url" {
  value = "http://${aws_instance.app.public_ip}:8000"
}
