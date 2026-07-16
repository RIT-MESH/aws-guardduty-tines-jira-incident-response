variable "aws_region" {
  description = "AWS region to deploy resources into."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment name (e.g. dev, staging, prod)."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "project_name" {
  description = "Short project name used as a name prefix."
  type        = string
  default     = "gd-ir"
}

variable "tines_webhook_url" {
  description = "Tines webhook URL that receives forwarded GuardDuty findings. Use a secret reference when possible."
  type        = string
  default     = ""
}

variable "tines_shared_secret" {
  description = "Optional shared secret sent to Tines via an auth header. Store in Secrets Manager; leave empty here."
  type        = string
  default     = ""
  sensitive   = true
}

variable "tines_auth_header_name" {
  description = "Name of the HTTP header that carries the Tines shared secret."
  type        = string
  default     = "X-Tines-Shared-Secret"
}

variable "guardduty_min_severity" {
  description = "Minimum GuardDuty severity score (0.0-10.0) to forward. Findings below this are not routed."
  type        = number
  default     = 0.0

  validation {
    condition     = var.guardduty_min_severity >= 0.0 && var.guardduty_min_severity <= 10.0
    error_message = "guardduty_min_severity must be between 0.0 and 10.0."
  }
}

variable "enable_lambda_forwarder" {
  description = "When true, deploy the optional Lambda forwarder as the EventBridge target instead of the API Destination."
  type        = bool
  default     = false
}

variable "lambda_source_dir" {
  description = "Local directory containing the Lambda forwarder source to package."
  type        = string
  default     = "../src"
}

variable "lambda_handler" {
  description = "Lambda handler entrypoint (module.function)."
  type        = string
  default     = "lambda_forwarder.handler.lambda_handler"
}

variable "lambda_runtime" {
  description = "Lambda runtime."
  type        = string
  default     = "python3.12"
}

variable "lambda_timeout_seconds" {
  description = "Lambda function timeout in seconds."
  type        = number
  default     = 15
}

variable "lambda_memory_mb" {
  description = "Lambda function memory in MB."
  type        = number
  default     = 256
}

variable "tines_webhook_url_secret_arn" {
  description = "Optional Secrets Manager secret ARN whose value is the Tines webhook URL. Takes precedence over var.tines_webhook_url."
  type        = string
  default     = ""
}

variable "tines_shared_secret_secret_arn" {
  description = "Optional Secrets Manager secret ARN whose value is the Tines shared secret. Takes precedence over var.tines_shared_secret."
  type        = string
  default     = ""
}

variable "jira_project_key" {
  description = "Jira project key (informational; used by the Lambda/Tines layer, stored as a non-secret SSM parameter)."
  type        = string
  default     = "SEC"
}

variable "jira_issue_type" {
  description = "Jira issue type name (informational; stored as a non-secret SSM parameter)."
  type        = string
  default     = "Incident"
}

variable "log_retention_days" {
  description = "CloudWatch log group retention in days."
  type        = number
  default     = 30
}

variable "dlq_message_retention_seconds" {
  description = "SQS dead-letter queue message retention in seconds."
  type        = number
  default     = 1209600 # 14 days
}

variable "tags" {
  description = "Additional resource tags merged onto all resources."
  type        = map(string)
  default     = {}
}
