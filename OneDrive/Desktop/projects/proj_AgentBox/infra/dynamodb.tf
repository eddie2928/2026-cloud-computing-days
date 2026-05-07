# 1C-6: DynamoDB tables

resource "aws_dynamodb_table" "events" {
  name         = "${var.project}-events"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "event_id"
  range_key    = "ts"

  attribute {
    name = "event_id"
    type = "S"
  }
  attribute {
    name = "ts"
    type = "S"
  }
  attribute {
    name = "user_id"
    type = "S"
  }

  global_secondary_index {
    name            = "user_id-ts-index"
    hash_key        = "user_id"
    range_key       = "ts"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  # 2C-2: Enable DynamoDB Streams for metrics Lambda
  stream_enabled   = true
  stream_view_type = "NEW_IMAGE"

  tags = { Name = "${var.project}-events" }
}

resource "aws_dynamodb_table" "settings" {
  name         = "${var.project}-settings"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "key"

  attribute {
    name = "key"
    type = "S"
  }

  tags = { Name = "${var.project}-settings" }
}
