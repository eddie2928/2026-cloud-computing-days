resource "aws_db_subnet_group" "main" {
  name       = "qna-diary-db-subnet-group"
  subnet_ids = aws_subnet.public[*].id

  tags = {
    Name    = "qna-diary-db-subnet-group"
    Project = "qna-diary"
  }
}

resource "aws_db_instance" "main" {
  identifier        = "qna-diary-postgres"
  engine            = "postgres"
  engine_version    = "16"
  instance_class    = var.db_instance_class
  allocated_storage = 20

  db_name  = "qnadiary"
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]

  publicly_accessible = false
  multi_az            = false
  storage_encrypted   = false

  skip_final_snapshot = true
  deletion_protection = false

  enabled_cloudwatch_logs_exports = []

  tags = {
    Name    = "qna-diary-postgres"
    Project = "qna-diary"
  }
}
