locals {
  db_url = "postgresql+asyncpg://appuser:${var.db_password}@qna-diary-postgres.cby4uwwoo3ds.ap-northeast-2.rds.amazonaws.com/qnadiary"
}

data "aws_security_group" "mcp_sg" {
  name   = "qna-diary-mcp-sg"
  vpc_id = data.aws_vpc.main.id
}

resource "aws_instance" "mcp" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = "t3.small"
  subnet_id              = data.aws_subnet.public.id
  vpc_security_group_ids = [data.aws_security_group.mcp_sg.id]
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
