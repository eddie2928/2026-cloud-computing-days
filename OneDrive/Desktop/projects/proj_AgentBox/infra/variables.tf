variable "aws_region" {
  default = "us-east-1"
}

variable "project" {
  description = "Project name prefix for all resources"
  default     = "agentbox"
}

variable "ec2_ami" {
  description = "Ubuntu 22.04 LTS AMI (us-east-1)"
  default     = "ami-0c7217cdde317cfec"
}

variable "ec2_instance_type" {
  default = "t3.micro"
}

variable "endpoint_cidr" {
  description = "Endpoint IP CIDR allowed to connect to gRPC :50051"
  type        = string
}

variable "admin_cidr" {
  description = "Admin IP CIDR allowed to access SaaS :8000"
  type        = string
}

variable "admin_token" {
  description = "Admin API token for SaaS dashboard"
  sensitive   = true
}

variable "alert_email" {
  description = "Email address for SNS alarm notifications"
  type        = string
  default     = ""
}

variable "existing_kms_key_arn" {
  description = "ARN of pre-existing CMK to reuse (empty = create new key on first apply)"
  type        = string
  default     = ""
}
