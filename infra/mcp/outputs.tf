output "mcp_public_ip" {
  description = "MCP EC2 public IP"
  value       = aws_instance.mcp.public_ip
}

output "mcp_ssh_command" {
  description = "SSH command to connect to MCP EC2"
  value       = "ssh -i ../qna-diary.pem ec2-user@${aws_instance.mcp.public_ip}"
}

output "mcp_private_url" {
  description = "MCP server URL (call from app EC2)"
  value       = "http://${aws_instance.mcp.private_ip}:8080/mcp"
}
