locals {
  db_url = "postgresql+asyncpg://appuser:${var.db_password}@qna-diary-postgres.cby4uwwoo3ds.ap-northeast-2.rds.amazonaws.com/qnadiary"
}

# ── MCP 전용 보안 그룹 ────────────────────────────────────────────────────────

resource "aws_security_group" "mcp_sg" {
  name        = "qna-diary-mcp-sg"
  description = "Security group for MCP server EC2"
  vpc_id      = data.aws_vpc.main.id

  ingress {
    description     = "MCP Streamable HTTP from app EC2 only"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [data.aws_security_group.ec2_sg.id]
  }

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "qna-diary-mcp-sg"
    Project = "qna-diary"
  }

  lifecycle {
    ignore_changes = [egress]
  }
}

# ── RDS SG에 MCP 접근 룰 추가 ────────────────────────────────────────────────

resource "aws_security_group_rule" "rds_from_mcp" {
  type                     = "ingress"
  description              = "PostgreSQL from MCP EC2"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.mcp_sg.id
  security_group_id        = data.aws_security_group.rds_sg.id
}

# ── MCP EC2 ──────────────────────────────────────────────────────────────────

resource "aws_instance" "mcp" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = "t3.small"
  subnet_id              = data.aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.mcp_sg.id]
  iam_instance_profile   = "SafeInstanceProfile-2026-inha-cc-06"
  key_name               = data.aws_key_pair.app.key_name

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }

  user_data_replace_on_change = true

  user_data = templatefile("${path.module}/../user_data_mcp.sh.tftpl", {
    git_repo_url = "https://github.com/55002ghals/2026-cloud-computing-days.git"
    git_branch   = var.git_branch
    db_url       = local.db_url
  })

  tags = {
    Name    = "qna-diary-mcp"
    Project = "qna-diary"
  }
}
