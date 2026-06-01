variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "ap-northeast-2"
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
  default     = ["ap-northeast-2a", "ap-northeast-2c"]
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
  default     = "global.anthropic.claude-sonnet-4-6"
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

variable "vapid_public_key" {
  description = "VAPID public key (base64url uncompressed) for Web Push"
  type        = string
  default     = ""
}

variable "vapid_private_key" {
  description = "VAPID private key (base64-encoded PEM) for Web Push"
  type        = string
  sensitive   = true
  default     = ""
}

variable "vapid_subject" {
  description = "VAPID subject claim (mailto: or https:)"
  type        = string
  default     = "mailto:admin@example.com"
}

variable "cookie_secure" {
  description = "Set Secure flag on session cookie (true in prod, false for HTTP-only local)"
  type        = bool
  default     = false
}

variable "mcp_ec2_instance_type" {
  description = "EC2 instance type for MCP server"
  type        = string
  default     = "t3.micro"
}
