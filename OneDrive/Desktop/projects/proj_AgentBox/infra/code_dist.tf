# 3A-6: Package local code and upload to S3 for EC2 bootstrap

data "archive_file" "code" {
  type        = "zip"
  source_dir  = "${path.module}/.."
  output_path = "${path.module}/agentbox-code.zip"
  excludes = [
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "tests",
    "infra",
    "scripts",
    "encrypted",
    "sample_project",
    "lambda/mcp_bridge.zip",
    "lambda/metrics_publisher.zip",
  ]
}

resource "aws_s3_object" "code" {
  bucket = aws_s3_bucket.encrypted_code.id
  key    = "_dist/code-${data.archive_file.code.output_base64sha256}.zip"
  source = data.archive_file.code.output_path
  etag   = filemd5(data.archive_file.code.output_path)
}

output "code_zip_s3_uri" {
  value = "s3://${aws_s3_bucket.encrypted_code.id}/${aws_s3_object.code.key}"
}
