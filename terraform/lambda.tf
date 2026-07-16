# Optional Lambda forwarder target.
#
# Deployed only when var.enable_lambda_forwarder is true. Packages the Python
# source under var.lambda_source_dir (src/ by default), which contains both the
# lambda_forwarder package and the shared incident_response package.

data "archive_file" "forwarder" {
  count       = var.enable_lambda_forwarder ? 1 : 0
  type        = "zip"
  source_dir  = var.lambda_source_dir
  output_path = "${path.module}/builds/forwarder.zip"
}

resource "aws_lambda_function" "forwarder" {
  count         = var.enable_lambda_forwarder ? 1 : 0
  function_name = "${local.name_prefix}-forwarder"
  description   = "Forwards normalized Amazon GuardDuty findings to the Tines webhook."
  role          = aws_iam_role.lambda_forwarder[0].arn
  handler       = var.lambda_handler
  runtime       = var.lambda_runtime
  timeout       = var.lambda_timeout_seconds
  memory_size   = var.lambda_memory_mb

  filename         = data.archive_file.forwarder[0].output_path
  source_code_hash = data.archive_file.forwarder[0].output_base64sha256

  environment {
    variables = {
      TINES_WEBHOOK_URL          = var.tines_webhook_url
      TINES_SHARED_SECRET        = var.tines_shared_secret
      TINES_SHARED_SECRET_HEADER = var.tines_auth_header_name
      TINES_TIMEOUT_SECONDS      = tostring(var.lambda_timeout_seconds)
      TINES_MAX_RETRIES          = "3"
      GUARDDUTY_MIN_SEVERITY     = tostring(var.guardduty_min_severity)
      ENVIRONMENT                = var.environment
      PROJECT_NAME               = var.project_name
      # Secret ARNs for run-time resolution (IAM already grants read access).
      TINES_WEBHOOK_URL_SECRET_ARN   = aws_secretsmanager_secret.tines_webhook_url.arn
      TINES_SHARED_SECRET_SECRET_ARN = aws_secretsmanager_secret.tines_shared_secret.arn
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.forwarder,
    aws_iam_role_policy.lambda_logging,
    aws_iam_role_policy.lambda_secrets,
  ]

  tags = {
    Name = "${local.name_prefix}-forwarder"
  }
}
