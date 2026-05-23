output "ec2_public_ip" {
  description = "Public IP of the EC2 app server"
  value       = aws_instance.app.public_ip
}

output "ec2_public_dns" {
  description = "Public DNS of the EC2 app server"
  value       = aws_instance.app.public_dns
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.main.address
}

output "app_url" {
  description = "Application URL"
  value       = "http://${aws_instance.app.public_ip}"
}

output "ssh_command" {
  description = "SSH command to connect to EC2"
  value       = "ssh -i ${local_sensitive_file.private_key.filename} ec2-user@${aws_instance.app.public_ip}"
}

output "ssh_private_key_path" {
  description = "Path to the generated SSH private key PEM file"
  value       = local_sensitive_file.private_key.filename
}

output "ssh_private_key_pem" {
  description = "EC2 SSH access private key in PEM format"
  value       = tls_private_key.app.private_key_pem
  sensitive   = true
}
