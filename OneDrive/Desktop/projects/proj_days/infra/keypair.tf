resource "tls_private_key" "app" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "app" {
  key_name   = "qna-diary-key"
  public_key = tls_private_key.app.public_key_openssh

  tags = {
    Name    = "qna-diary-key"
    Project = "qna-diary"
  }
}

resource "local_sensitive_file" "private_key" {
  content         = tls_private_key.app.private_key_pem
  filename        = "${path.module}/qna-diary.pem"
  file_permission = "0600"
}
