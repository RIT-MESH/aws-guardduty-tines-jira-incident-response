output "guardduty_detector_id" {
  description = "ID of the provisioned GuardDuty detector."
  value       = aws_guardduty_detector.this.id
}

output "eventbridge_rule_arn" {
  description = "ARN of the EventBridge rule matching GuardDuty findings."
  value       = aws_cloudwatch_event_rule.guardduty_findings.arn
}

output "eventbridge_rule_name" {
  description = "Name of the EventBridge rule matching GuardDuty findings."
  value       = aws_cloudwatch_event_rule.guardduty_findings.name
}

output "tines_api_destination_arn" {
  description = "ARN of the EventBridge API Destination to Tines (empty if Lambda forwarder is enabled)."
  value       = join("", aws_cloudwatch_event_api_destination.tines[*].arn)
}

output "tines_connection_arn" {
  description = "ARN of the EventBridge connection to Tines (empty if Lambda forwarder is enabled)."
  value       = join("", aws_cloudwatch_event_connection.tines[*].arn)
}

output "lambda_forwarder_function_name" {
  description = "Name of the Lambda forwarder function (empty if disabled)."
  value       = join("", aws_lambda_function.forwarder[*].function_name)
}

output "lambda_forwarder_function_arn" {
  description = "ARN of the Lambda forwarder function (empty if disabled)."
  value       = join("", aws_lambda_function.forwarder[*].arn)
}

output "lambda_forwarder_role_arn" {
  description = "ARN of the Lambda execution role (empty if disabled)."
  value       = join("", aws_iam_role.lambda_forwarder[*].arn)
}

output "dead_letter_queue_url" {
  description = "URL of the SQS dead-letter queue."
  value       = aws_sqs_queue.dlq.url
}

output "dead_letter_queue_arn" {
  description = "ARN of the SQS dead-letter queue."
  value       = aws_sqs_queue.dlq.arn
}

output "forwarder_log_group_name" {
  description = "CloudWatch log group name for the forwarder."
  value       = aws_cloudwatch_log_group.forwarder.name
}

output "tines_webhook_url_secret_arn" {
  description = "ARN of the Secrets Manager secret holding the Tines webhook URL (set value out-of-band)."
  value       = aws_secretsmanager_secret.tines_webhook_url.arn
}

output "tines_shared_secret_secret_arn" {
  description = "ARN of the Secrets Manager secret holding the Tines shared secret (set value out-of-band)."
  value       = aws_secretsmanager_secret.tines_shared_secret.arn
  sensitive   = true
}

output "jira_project_key_parameter_name" {
  description = "SSM parameter name holding the Jira project key."
  value       = aws_ssm_parameter.jira_project_key.name
}

output "jira_issue_type_parameter_name" {
  description = "SSM parameter name holding the Jira issue type."
  value       = aws_ssm_parameter.jira_issue_type.name
}

output "aws_account_id" {
  description = "Current AWS account id (from caller identity)."
  value       = data.aws_caller_identity.current.account_id
}

output "dlq_depth_alarm_name" {
  description = "Name of the CloudWatch alarm monitoring DLQ depth."
  value       = aws_cloudwatch_metric_alarm.dlq_depth.alarm_name
}
