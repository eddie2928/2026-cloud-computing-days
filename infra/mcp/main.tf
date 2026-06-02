terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-northeast-2"
}

# ── 기존 리소스 참조 (생성 안 함) ────────────────────────────────────────────

data "aws_vpc" "main" {
  id = "vpc-025b3aff747544b5f"
}

data "aws_subnet" "public" {
  id = "subnet-060cf4d51b935ce02"
}

data "aws_security_group" "ec2_sg" {
  name   = "qna-diary-ec2-sg"
  vpc_id = data.aws_vpc.main.id
}

data "aws_key_pair" "app" {
  key_name = "qna-diary-key"
}

data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}
