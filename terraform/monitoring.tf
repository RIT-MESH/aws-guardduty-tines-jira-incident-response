# CloudWatch logs and alarms for observability and delivery-failure alerting.

resource "aws_cloudwatch_log_group" "forwarder" {
  name              = "/aws/lambda/${local.name_prefix}-forwarder"
  retention_in_days = var.log_retention_days
  tags = {
    Name = "/aws/lambda/${local.name_prefix}-forwarder"
  }
}

# DLQ depth alarm: messages visible in the dead-letter queue indicate failed
# deliveries that need operator attention.
resource "aws_cloudwatch_metric_alarm" "dlq_depth" {
  alarm_name        = "${local.name_prefix}-dlq-depth"
  alarm_description = "Alerts when the GuardDuty forwarding dead-letter queue has undelivered messages."
  namespace         = "AWS/SQS"
  metric_name       = "ApproximateNumberOfMessagesVisible"
  dimensions = {
    QueueName = aws_sqs_queue.dlq.name
  }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  tags = {
    Name = "${local.name_prefix}-dlq-depth"
  }
}

# EventBridge failed invocations alarm (API Destination path).
resource "aws_cloudwatch_metric_alarm" "eb_failed_invocations" {
  count             = var.enable_lambda_forwarder ? 0 : 1
  alarm_name        = "${local.name_prefix}-eb-failed-invocations"
  alarm_description = "Alerts when EventBridge fails to deliver GuardDuty findings to the Tines API Destination."
  namespace         = "AWS/Events"
  metric_name       = "FailedInvocations"
  dimensions = {
    RuleName = aws_cloudwatch_event_rule.guardduty_findings.name
  }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  tags = {
    Name = "${local.name_prefix}-eb-failed-invocations"
  }
}

# Lambda errors alarm (Lambda path).
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  count             = var.enable_lambda_forwarder ? 1 : 0
  alarm_name        = "${local.name_prefix}-lambda-errors"
  alarm_description = "Alerts when the GuardDuty Lambda forwarder reports errors."
  namespace         = "AWS/Lambda"
  metric_name       = "Errors"
  dimensions = {
    FunctionName = aws_lambda_function.forwarder[0].function_name
  }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  tags = {
    Name = "${local.name_prefix}-lambda-errors"
  }
}
