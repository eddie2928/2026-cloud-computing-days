variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.20.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.20.1.0/24", "10.20.2.0/24"]
}

variable "azs" {
  description = "Availability zones for subnets"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "ec2_instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.small"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_username" {
  description = "RDS master username"
  type        = string
  default     = "appuser"
}

variable "db_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
}

variable "app_password" {
  description = "Application shared password for login"
  type        = string
  sensitive   = true
  default     = "inha-nxt"
}

variable "session_secret" {
  description = "Secret key for session cookie signing"
  type        = string
  sensitive   = true
}

variable "bedrock_model_id" {
  description = "AWS Bedrock model ID to use for AI generation"
  type        = string
  default     = "us.anthropic.claude-sonnet-4-6"
}

variable "my_ip_cidr" {
  description = "Your public IP CIDR for SSH access to EC2 (e.g. 1.2.3.4/32)"
  type        = string
}

variable "git_repo_url" {
  description = "Git repository URL to clone onto EC2"
  type        = string
}

variable "git_branch" {
  description = "Git branch to checkout on EC2"
  type        = string
  default     = "main"
}
