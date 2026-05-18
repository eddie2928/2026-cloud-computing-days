data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ec2_bedrock_role" {
  name               = "qna-diary-ec2-bedrock-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json

  tags = {
    Name    = "qna-diary-ec2-bedrock-role"
    Project = "qna-diary"
  }
}

locals {
  # Strip regional prefix (e.g. "us.") to get the base foundation model ID
  # e.g. "us.anthropic.claude-sonnet-4-6" -> "anthropic.claude-sonnet-4-6"
  base_model_id = replace(var.bedrock_model_id, "/^[a-z]+\\./", "")
}

data "aws_iam_policy_document" "bedrock_access" {
  statement {
    sid    = "BedrockInvokeModel"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
    ]
    resources = [
      # Cross-region inference profile (e.g. us.anthropic.claude-sonnet-4-6)
      "arn:aws:bedrock:${var.aws_region}:*:inference-profile/${var.bedrock_model_id}",
      # Base foundation model in all regions (required when using cross-region profiles)
      "arn:aws:bedrock:*::foundation-model/${local.base_model_id}",
    ]
  }

  statement {
    sid    = "BedrockListModels"
    effect = "Allow"
    actions = [
      "bedrock:ListFoundationModels",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "bedrock_access" {
  name        = "qna-diary-bedrock-access"
  description = "Allow EC2 to invoke Bedrock models"
  policy      = data.aws_iam_policy_document.bedrock_access.json

  tags = {
    Name    = "qna-diary-bedrock-access"
    Project = "qna-diary"
  }
}

resource "aws_iam_role_policy_attachment" "ec2_bedrock" {
  role       = aws_iam_role.ec2_bedrock_role.name
  policy_arn = aws_iam_policy.bedrock_access.arn
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "qna-diary-ec2-profile"
  role = aws_iam_role.ec2_bedrock_role.name

  tags = {
    Name    = "qna-diary-ec2-profile"
    Project = "qna-diary"
  }
} 