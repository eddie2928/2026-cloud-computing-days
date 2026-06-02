variable "db_password" {
  description = "RDS master password (appuser)"
  type        = string
  sensitive   = true
}

variable "git_branch" {
  description = "Git branch to deploy"
  type        = string
  default     = "master"
}
