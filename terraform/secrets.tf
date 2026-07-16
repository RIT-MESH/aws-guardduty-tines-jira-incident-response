# Secret and parameter references.
#
# Secrets are created WITHOUT a secret_version so their values are never stored
# in Terraform state. Set the values out-of-band (console / CLI / migration):
#
#   aws secretsmanager put-secret-value \
#     --secret-id <tines_webhook_url_secret_name> --secret-string "https://..."
#
# The IAM role for the Lambda grants read access to these secrets so the
# forwarder can be extended to fetch them at runtime instead of using env vars.

resource "aws_secretsmanager_secret" "tines_webhook_url" {
  name                    = "${local.name_prefix}/tines-webhook-url"
  description             = "Tines webhook URL for GuardDuty finding forwarding."
  recovery_window_in_days = 30
  tags = {
    Name = "${local.name_prefix}/tines-webhook-url"
  }
}

resource "aws_secretsmanager_secret" "tines_shared_secret" {
  name                    = "${local.name_prefix}/tines-shared-secret"
  description             = "Shared secret sent to Tines via an auth header."
  recovery_window_in_days = 30
  tags = {
    Name = "${local.name_prefix}/tines-shared-secret"
  }
}

# Non-secret configuration stored in SSM Parameter Store.
resource "aws_ssm_parameter" "jira_project_key" {
  name        = "/${local.name_prefix}/jira/project-key"
  description = "Jira project key used by the incident-response workflow."
  type        = "String"
  value       = var.jira_project_key
  tags = {
    Name = "/${local.name_prefix}/jira/project-key"
  }
}

resource "aws_ssm_parameter" "jira_issue_type" {
  name        = "/${local.name_prefix}/jira/issue-type"
  description = "Jira issue type used by the incident-response workflow."
  type        = "String"
  value       = var.jira_issue_type
  tags = {
    Name = "/${local.name_prefix}/jira/issue-type"
  }
}
