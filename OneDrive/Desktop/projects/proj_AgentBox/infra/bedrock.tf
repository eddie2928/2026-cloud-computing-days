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

# 3A-7: Bedrock Agent + Action Group + Alias (activated)
resource "aws_bedrockagent_agent" "inspector" {
  agent_name              = "${var.project}-inspector"
  agent_resource_role_arn = aws_iam_role.bedrock_agent.arn
  foundation_model        = "anthropic.claude-haiku-20240307-v1:0"
  instruction             = file("${path.module}/bedrock_system_prompt.txt")
  prepare_agent           = true
}

resource "aws_bedrockagent_agent_action_group" "decrypt_and_stage" {
  agent_id          = aws_bedrockagent_agent.inspector.id
  agent_version     = "DRAFT"
  action_group_name = "decrypt_and_stage"

  action_group_executor {
    lambda = aws_lambda_function.mcp_bridge.arn
  }

  function_schema {
    member_functions {
      functions {
        name        = "decrypt_and_stage"
        description = "Decrypt and stage encrypted code for Bedrock inspection"
        parameters {
          map_block_key = "project_id"
          type          = "string"
          required      = true
          description   = "Project ID to decrypt and stage"
        }
      }
    }
  }
}

resource "aws_bedrockagent_agent_alias" "live" {
  agent_id         = aws_bedrockagent_agent.inspector.id
  agent_alias_name = "live"
}

output "bedrock_agent_id" {
  value = aws_bedrockagent_agent.inspector.id
}

output "bedrock_agent_alias_id" {
  value = aws_bedrockagent_agent_alias.live.agent_alias_id
}
