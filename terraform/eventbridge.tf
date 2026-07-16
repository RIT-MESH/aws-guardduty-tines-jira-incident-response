# Amazon EventBridge rule, API Destination and Connection.
#
# The rule matches GuardDuty finding events and (by default) routes them to a
# Tines webhook through an EventBridge API Destination. When
# var.enable_lambda_forwarder is true, the Lambda forwarder is used as the
# target instead, which can pull the webhook URL / shared secret from Secrets
# Manager at runtime (avoiding placing secrets in EventBridge config).

# ----------------------------------------------------------------------------
# Event pattern + rule
# ----------------------------------------------------------------------------
resource "aws_cloudwatch_event_rule" "guardduty_findings" {
  name        = "${local.name_prefix}-guardduty-findings"
  description = "Routes Amazon GuardDuty findings at or above the configured minimum severity."

  # GuardDuty severity is a number in the finding detail. We use numeric
  # matching so the minimum severity is enforced by EventBridge before delivery.
  event_pattern = jsonencode({
    source        = ["aws.guardduty"]
    "detail-type" = ["GuardDuty Finding"]
    detail = {
      severity = [
        { numeric = [">=", local.severity_min] }
      ]
    }
  })

  tags = {
    Name = "${local.name_prefix}-guardduty-findings-rule"
  }
}

# ----------------------------------------------------------------------------
# Connection + API Destination (preferred target when Lambda is disabled)
# ----------------------------------------------------------------------------
resource "aws_cloudwatch_event_connection" "tines" {
  count       = var.enable_lambda_forwarder ? 0 : 1
  name        = "${local.name_prefix}-tines-connection"
  description = "Auth header used when forwarding GuardDuty findings to Tines."

  authorization_type = "API_KEY"

  auth_parameters {
    api_key {
      key   = var.tines_auth_header_name
      value = var.tines_shared_secret
    }
  }
}

resource "aws_cloudwatch_event_api_destination" "tines" {
  count                            = var.enable_lambda_forwarder ? 0 : 1
  name                             = "${local.name_prefix}-tines-destination"
  description                      = "Forwards GuardDuty findings to the Tines webhook."
  connection_arn                   = aws_cloudwatch_event_connection.tines[0].arn
  invocation_endpoint              = var.tines_webhook_url
  http_method                      = "POST"
  invocation_rate_limit_per_second = 10
}

# API Destination target (used when Lambda is disabled).
resource "aws_cloudwatch_event_target" "tines_api_destination" {
  count     = var.enable_lambda_forwarder ? 0 : 1
  rule      = aws_cloudwatch_event_rule.guardduty_findings.name
  target_id = "SendToTinesApiDestination"
  arn       = aws_cloudwatch_event_api_destination.tines[0].arn
  role_arn  = aws_iam_role.eventbridge_to_api_destination[0].arn
  dead_letter_config {
    arn = aws_sqs_queue.dlq.arn
  }

  # Send the full GuardDuty event as the request body.
  input_transformer {
    input_template = jsonencode({
      source        = "<source>"
      "detail-type" = "<detail-type>"
      time          = "<time>"
      region        = "<region>"
      account       = "<account>"
      detail        = "<detail>"
    })
  }
}

# ----------------------------------------------------------------------------
# Lambda target (used when Lambda is enabled)
# ----------------------------------------------------------------------------
resource "aws_cloudwatch_event_target" "lambda_forwarder" {
  count     = var.enable_lambda_forwarder ? 1 : 0
  rule      = aws_cloudwatch_event_rule.guardduty_findings.name
  arn       = aws_lambda_function.forwarder[0].arn
  role_arn  = aws_iam_role.eventbridge_to_lambda[0].arn
  target_id = "InvokeLambdaForwarder"
  dead_letter_config {
    arn = aws_sqs_queue.dlq.arn
  }
}



