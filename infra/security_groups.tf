resource "aws_security_group" "ec2_sg" {
  name        = "qna-diary-ec2-sg"
  description = "Security group for EC2 web server"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH from anywhere"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "qna-diary-ec2-sg"
    Project = "qna-diary"
  }
}

resource "aws_security_group" "rds_sg" {
  name        = "qna-diary-rds-sg"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from EC2"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2_sg.id]
  }

  ingress {
    description     = "PostgreSQL from MCP EC2"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.mcp_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "qna-diary-rds-sg"
    Project = "qna-diary"
  }
}

resource "aws_security_group" "mcp_sg" {
  name        = "qna-diary-mcp-sg"
  description = "Security group for MCP server EC2"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "MCP Streamable HTTP from app EC2 only"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2_sg.id]
  }

  ingress {
    description = "SSH from anywhere"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "qna-diary-mcp-sg"
    Project = "qna-diary"
  }
}
