data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

locals {
  db_url = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${aws_db_instance.main.address}/${aws_db_instance.main.db_name}"
}

resource "aws_instance" "app" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = var.ec2_instance_type
  subnet_id              = aws_subnet.public[0].id
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name

  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    git_repo_url     = var.git_repo_url
    git_branch       = var.git_branch
    db_url           = local.db_url
    app_password     = var.app_password
    session_secret   = var.session_secret
    bedrock_model_id = var.bedrock_model_id
    aws_region       = var.aws_region
  })

  tags = {
    Name    = "qna-diary-app"
    Project = "qna-diary"
  }
}
