# Dead-letter SQS queue for events that cannot be delivered.
resource "aws_sqs_queue" "dlq" {
  name                      = "${local.name_prefix}-dlq"
  message_retention_seconds = var.dlq_message_retention_seconds
  sqs_managed_sse_enabled   = true
  tags = {
    Name = "${local.name_prefix}-dlq"
  }
}
