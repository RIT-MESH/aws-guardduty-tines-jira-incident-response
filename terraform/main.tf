# Entry point. Resource definitions live in focused files:
#   guardduty.tf, eventbridge.tf, iam.tf, sqs.tf, monitoring.tf,
#   lambda.tf, secrets.tf
#
# This file holds shared data sources used by outputs and policies.

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}
