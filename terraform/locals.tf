locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Component   = "guardduty-incident-response"
    },
    var.tags
  )

  # GuardDuty severity bands documented by AWS:
  #   0.0 - 1.99 Low | 2.0 - 5.99 Medium | 6.0 - 7.99 High | 8.0 - 10.0 Critical
  # EventBridge numeric matching uses the finding severity as a number.
  severity_min = var.guardduty_min_severity
}
