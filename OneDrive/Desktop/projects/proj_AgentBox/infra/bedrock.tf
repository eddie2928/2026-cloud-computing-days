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
  agent_name                 = "${var.project}-inspector"
  agent_resource_role_arn    = aws_iam_role.bedrock_agent.arn
  foundation_model           = "us.anthropic.claude-sonnet-4-6"
  instruction = join("\n", [
    file("${path.module}/bedrock_system_prompt.txt"),
    file("${path.module}/bedrock_tools_addendum.txt"),
  ])
  prepare_agent              = true
  skip_resource_in_use_check = true
}

resource "aws_bedrockagent_agent_action_group" "decrypt_and_stage" {
  agent_id          = aws_bedrockagent_agent.inspector.id
  agent_version     = "DRAFT"
  action_group_name = "decrypt_and_stage"

  # list_project_files must finish (including its PrepareAgent call) before
  # decrypt_and_stage starts, to avoid concurrent PrepareAgent conflict.
  depends_on = [aws_bedrockagent_agent_action_group.list_project_files]

  action_group_executor {
    lambda = aws_lambda_function.mcp_bridge.arn
  }

  function_schema {
    member_functions {
      functions {
        name        = "decrypt_and_stage"
        description = "Decrypt specified files and return plaintext content. See system instruction for usage."
        parameters {
          map_block_key = "project_id"
          type          = "string"
          required      = true
        }
        parameters {
          map_block_key = "files"
          type          = "string"
          required      = true
          description   = "comma-separated relative paths"
        }
        parameters {
          map_block_key = "start_byte"
          type          = "integer"
          required      = false
        }
        parameters {
          map_block_key = "max_bytes"
          type          = "integer"
          required      = false
        }
      }
    }
  }
}

resource "aws_bedrockagent_agent_action_group" "list_project_files" {
  agent_id          = aws_bedrockagent_agent.inspector.id
  agent_version     = "DRAFT"
  action_group_name = "list_project_files"

  action_group_executor {
    lambda = aws_lambda_function.mcp_bridge.arn
  }

  function_schema {
    member_functions {
      functions {
        name        = "list_project_files"
        description = "List all files (with size, is_binary, modified) of an encrypted project. Returns Markdown."
        parameters {
          map_block_key = "project_id"
          type          = "string"
          required      = true
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
