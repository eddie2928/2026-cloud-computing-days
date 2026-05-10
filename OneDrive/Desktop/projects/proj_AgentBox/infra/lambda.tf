# 2A-2: Lambda function for Bedrock Action Group MCP bridge

resource "aws_iam_role" "lambda_mcp" {
  name = "${var.project}-lambda-mcp-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_mcp.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda_mcp.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy" "lambda_mcp" {
  name = "${var.project}-lambda-mcp-policy"
  role = aws_iam_role.lambda_mcp.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "S3KBRead"
      Effect = "Allow"
      Action = ["s3:GetObject"]
      Resource = ["${aws_s3_bucket.kb_staging.arn}/*"]
    }]
  })
}

data "archive_file" "lambda_mcp" {
  type        = "zip"
  source_file = "${path.module}/../lambda/mcp_bridge.py"
  output_path = "${path.module}/../lambda/mcp_bridge.zip"
}

resource "aws_lambda_function" "mcp_bridge" {
  function_name    = "${var.project}-mcp-bridge"
  role             = aws_iam_role.lambda_mcp.arn
  runtime          = "python3.11"
  handler          = "mcp_bridge.handler"
  filename         = data.archive_file.lambda_mcp.output_path
  source_code_hash = data.archive_file.lambda_mcp.output_base64sha256
  timeout          = 60

  vpc_config {
    subnet_ids         = [aws_subnet.private.id]
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      MCP_SERVER_URL  = "http://${aws_instance.mcp.private_ip}:8080"
      KB_STAGING_BUCKET = aws_s3_bucket.kb_staging.id
      MCP_ADMIN_TOKEN = var.admin_token
    }
  }

  tags = { Name = "${var.project}-mcp-bridge" }
}

# Allow Bedrock Agent to invoke this Lambda
resource "aws_lambda_permission" "bedrock" {
  statement_id  = "AllowBedrockAgent"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.mcp_bridge.function_name
  principal     = "bedrock.amazonaws.com"
}

output "lambda_function_arn" {
  value = aws_lambda_function.mcp_bridge.arn
}
