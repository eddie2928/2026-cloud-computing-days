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
  # CloudFront 적용 후 https://<cloudfront_domain> 사용
  description = "Application URL (EC2 direct — use cloudfront_domain_name for prod)"
  value       = "http://${aws_instance.app.public_ip}"
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name (HTTPS endpoint)"
  value       = aws_cloudfront_distribution.app.domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.app.id
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

output "mcp_public_ip" {
  description = "Public IP of the MCP server EC2 (SSH only)"
  value       = aws_instance.mcp.public_ip
}

output "mcp_ssh_command" {
  description = "SSH command to connect to MCP EC2"
  value       = "ssh -i ${local_sensitive_file.private_key.filename} ec2-user@${aws_instance.mcp.public_ip}"
}

output "mcp_private_url" {
  description = "MCP server Streamable HTTP endpoint (VPC-internal, accessible from app EC2 only)"
  value       = "http://${aws_instance.mcp.private_ip}:8080/mcp"
}
