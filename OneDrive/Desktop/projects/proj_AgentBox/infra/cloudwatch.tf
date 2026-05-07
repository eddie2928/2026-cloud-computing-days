# Phase 2C: CloudWatch Logs, Metrics, SNS alerts, retention policies

# 2C-1: CloudWatch Log Groups for EC2 systemd services
resource "aws_cloudwatch_log_group" "grpc" {
  name              = "/agentbox/ec2/grpc"
  retention_in_days = 90
  tags              = { Name = "${var.project}-grpc-logs" }
}

resource "aws_cloudwatch_log_group" "mcp" {
  name              = "/agentbox/ec2/mcp"
  retention_in_days = 90
  tags              = { Name = "${var.project}-mcp-logs" }
}

resource "aws_cloudwatch_log_group" "saas" {
  name              = "/agentbox/ec2/saas"
  retention_in_days = 90
  tags              = { Name = "${var.project}-saas-logs" }
}

# CloudWatch agent config on EC2 (sent via SSM or baked into userdata)
# This resource creates the SSM parameter that the CloudWatch agent reads.
resource "aws_ssm_parameter" "cw_agent_config" {
  name  = "/agentbox/cloudwatch-agent-config"
  type  = "String"
  value = jsonencode({
    logs = {
      logs_collected = {
        files = {
          collect_list = [
            {
              file_path        = "/opt/agentbox/logs/grpc-server.log"
              log_group_name   = "/agentbox/ec2/grpc"
              log_stream_name  = "{instance_id}"
              retention_in_days = 90
            },
            {
              file_path        = "/opt/agentbox/logs/mcp-server.log"
              log_group_name   = "/agentbox/ec2/mcp"
              log_stream_name  = "{instance_id}"
              retention_in_days = 90
            },
            {
              file_path        = "/opt/agentbox/logs/saas.log"
              log_group_name   = "/agentbox/ec2/saas"
              log_stream_name  = "{instance_id}"
              retention_in_days = 90
            },
          ]
        }
      }
    }
  })
}

# 2C-2: Lambda for DynamoDB Streams -> Custom Metrics (BlockRate, EventCount)
resource "aws_iam_role" "lambda_metrics" {
  name = "${var.project}-lambda-metrics-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_metrics_basic" {
  role       = aws_iam_role.lambda_metrics.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_metrics" {
  name = "${var.project}-lambda-metrics-policy"
  role = aws_iam_role.lambda_metrics.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["cloudwatch:PutMetricData"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["dynamodb:GetRecords", "dynamodb:GetShardIterator", "dynamodb:DescribeStream", "dynamodb:ListStreams"]
        Resource = [aws_dynamodb_table.events.stream_arn]
      },
    ]
  })
}

resource "aws_lambda_function" "metrics_publisher" {
  function_name    = "${var.project}-metrics-publisher"
  role             = aws_iam_role.lambda_metrics.arn
  runtime          = "python3.11"
  handler          = "index.handler"
  filename         = "${path.module}/../lambda/metrics_publisher.zip"
  source_code_hash = filebase64sha256("${path.module}/../lambda/metrics_publisher.zip")
  timeout          = 60

  environment {
    variables = {
      PROJECT = var.project
      REGION  = var.aws_region
    }
  }
}

resource "aws_lambda_event_source_mapping" "dynamo_stream" {
  event_source_arn  = aws_dynamodb_table.events.stream_arn
  function_name     = aws_lambda_function.metrics_publisher.arn
  starting_position = "LATEST"
  batch_size        = 100
}

# Enable DynamoDB Streams on events table (update existing resource)
# NOTE: Requires adding stream_enabled=true to the dynamodb table resource.

# 2C-3: SNS topic + email subscription for alerts
resource "aws_sns_topic" "alerts" {
  name = "${var.project}-alerts"
  tags = { Name = "${var.project}-alerts" }
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# BlockRate > 10% (10-min average) alarm
resource "aws_cloudwatch_metric_alarm" "block_rate" {
  alarm_name          = "${var.project}-high-block-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "BlockRate"
  namespace           = "AgentBox"
  period              = 600
  statistic           = "Average"
  threshold           = 10
  alarm_description   = "Block rate exceeded 10% over 10 minutes"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
}

# ErrorRate > 5% alarm
resource "aws_cloudwatch_metric_alarm" "error_rate" {
  alarm_name          = "${var.project}-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ErrorRate"
  namespace           = "AgentBox"
  period              = 600
  statistic           = "Average"
  threshold           = 5
  alarm_description   = "Error rate exceeded 5% over 10 minutes"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
}
