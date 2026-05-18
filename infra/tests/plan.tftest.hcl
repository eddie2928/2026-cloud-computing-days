variables {
  db_password    = "test-password-123"
  session_secret = "test-session-secret-at-least-32-chars-long"
  my_ip_cidr     = "10.0.0.1/32"
  git_repo_url   = "https://github.com/test/repo.git"
}

run "plan_resources_count" {
  command = plan

  # (a) EC2 instance count = 1
  assert {
    condition     = length([aws_instance.app]) == 1
    error_message = "Expected exactly 1 EC2 instance"
  }

  # (b) RDS instance count = 1
  assert {
    condition     = length([aws_db_instance.main]) == 1
    error_message = "Expected exactly 1 RDS instance"
  }

  # (c) Public Subnet count = 2
  assert {
    condition     = length(aws_subnet.public) == 2
    error_message = "Expected exactly 2 public subnets"
  }

  # (d) EC2 SG has port 80 ingress
  assert {
    condition = anytrue([
      for rule in aws_security_group.ec2_sg.ingress : rule.from_port == 80
    ])
    error_message = "EC2 security group must have port 80 ingress"
  }
}
