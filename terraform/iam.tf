# IAM roles and least-privilege policies.

# ----------------------------------------------------------------------------
# EventBridge -> API Destination (preferred path)
# ----------------------------------------------------------------------------
data "aws_iam_policy_document" "eventbridge_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "eventbridge_to_api_destination" {
  count              = var.enable_lambda_forwarder ? 0 : 1
  name               = "${local.name_prefix}-eb-to-tines"
  assume_role_policy = data.aws_iam_policy_document.eventbridge_assume.json
  tags               = { Name = "${local.name_prefix}-eb-to-tines" }
}

resource "aws_iam_role_policy" "eventbridge_to_api_destination" {
  count = var.enable_lambda_forwarder ? 0 : 1
  name  = "invoke-tines-destination"
  role  = aws_iam_role.eventbridge_to_api_destination[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["events:InvokeApiDestination"]
        Resource = [aws_cloudwatch_event_api_destination.tines[0].arn]
      },
      {
        Effect   = "Allow"
        Action   = ["sqs:SendMessage"]
        Resource = [aws_sqs_queue.dlq.arn]
      }
    ]
  })
}

# ----------------------------------------------------------------------------
# EventBridge -> Lambda (optional path)
# ----------------------------------------------------------------------------
resource "aws_iam_role" "eventbridge_to_lambda" {
  count              = var.enable_lambda_forwarder ? 1 : 0
  name               = "${local.name_prefix}-eb-to-lambda"
  assume_role_policy = data.aws_iam_policy_document.eventbridge_assume.json
  tags               = { Name = "${local.name_prefix}-eb-to-lambda" }
}

resource "aws_iam_role_policy" "eventbridge_to_lambda" {
  count = var.enable_lambda_forwarder ? 1 : 0
  name  = "invoke-forwarder"
  role  = aws_iam_role.eventbridge_to_lambda[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["lambda:InvokeFunction"]
        Resource = [aws_lambda_function.forwarder[0].arn]
      },
      {
        Effect   = "Allow"
        Action   = ["sqs:SendMessage"]
        Resource = [aws_sqs_queue.dlq.arn]
      }
    ]
  })
}

# ----------------------------------------------------------------------------
# Lambda execution role
# ----------------------------------------------------------------------------
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_forwarder" {
  count              = var.enable_lambda_forwarder ? 1 : 0
  name               = "${local.name_prefix}-lambda-forwarder"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = { Name = "${local.name_prefix}-lambda-forwarder" }
}

# Least-privilege: write logs only.
data "aws_iam_policy_document" "lambda_logging" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.forwarder.arn}:*"]
  }

  statement {
    effect    = "Allow"
    actions   = ["logs:CreateLogGroup"]
    resources = ["arn:aws:logs:${var.aws_region}:*:*"]
  }
}

resource "aws_iam_role_policy" "lambda_logging" {
  count  = var.enable_lambda_forwarder ? 1 : 0
  name   = "logging"
  role   = aws_iam_role.lambda_forwarder[0].id
  policy = data.aws_iam_policy_document.lambda_logging.json
}

# Least-privilege: read only the configured secrets and SSM parameters.
data "aws_iam_policy_document" "lambda_secrets" {
  statement {
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret",
    ]
    resources = compact([
      aws_secretsmanager_secret.tines_webhook_url.arn,
      aws_secretsmanager_secret.tines_shared_secret.arn,
    ])
  }

  statement {
    effect = "Allow"
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
    ]
    resources = [
      aws_ssm_parameter.jira_project_key.arn,
      aws_ssm_parameter.jira_issue_type.arn,
    ]
  }
}

resource "aws_iam_role_policy" "lambda_secrets" {
  count  = var.enable_lambda_forwarder ? 1 : 0
  name   = "secrets"
  role   = aws_iam_role.lambda_forwarder[0].id
  policy = data.aws_iam_policy_document.lambda_secrets.json
}
