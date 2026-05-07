# Phase 1D/2A: Bedrock Agent IAM role + Agent + Action Group

resource "aws_iam_role" "bedrock_agent" {
  name = "${var.project}-bedrock-agent-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "bedrock.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "bedrock_agent" {
  name = "${var.project}-bedrock-agent-policy"
  role = aws_iam_role.bedrock_agent.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3KBRead"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.kb_staging.arn,
          "${aws_s3_bucket.kb_staging.arn}/*",
        ]
      },
      {
        Sid    = "LambdaInvoke"
        Effect = "Allow"
        Action = ["lambda:InvokeFunction"]
        Resource = ["arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${var.project}-mcp-bridge"]
      },
      {
        Sid    = "BedrockModel"
        Effect = "Allow"
        Action = ["bedrock:InvokeModel"]
        Resource = ["*"]
      },
    ]
  })
}

# 2A-3: Bedrock Agent (populated in Phase 2A - placeholder IAM role created here)
# Full Bedrock Agent resource requires AWS Console model access approval first (2A-1).
# After terraform apply, create the agent via AWS Console or uncomment below:
#
# resource "aws_bedrockagent_agent" "inspector" {
#   agent_name              = "${var.project}-inspector"
#   agent_resource_role_arn = aws_iam_role.bedrock_agent.arn
#   foundation_model        = "anthropic.claude-haiku-20240307-v1:0"
#   instruction             = file("${path.module}/bedrock_system_prompt.txt")
# }
