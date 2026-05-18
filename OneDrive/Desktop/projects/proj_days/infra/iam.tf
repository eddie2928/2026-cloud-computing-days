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

data "aws_iam_policy_document" "bedrock_access" {
  statement {
    sid    = "BedrockInvokeModel"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
    ]
    resources = [
      "arn:aws:bedrock:${var.aws_region}::foundation-model/${var.bedrock_model_id}",
      "arn:aws:bedrock:${var.aws_region}:*:inference-profile/${var.bedrock_model_id}",
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
