# AWS Setup Guide

How to deploy the AWS-side resources with Terraform.

## Prerequisites

- An AWS account and credentials (`aws configure` or env vars).
- Terraform >= 1.5.
- A Tines webhook URL (from the imported Story) for the API Destination path, or
  nothing extra for the Lambda path (it can resolve the URL from Secrets Manager).

## What gets deployed

- Amazon GuardDuty detector (S3, Kubernetes audit, Malware Protection EBS).
- EventBridge rule matching `aws.guardduty` / `GuardDuty Finding` with severity >= min.
- EventBridge Connection + API Destination to Tines (default) **or** a Lambda target.
- Least-privilege IAM roles.
- SQS dead-letter queue.
- CloudWatch log group + alarms.
- Secrets Manager secrets (empty) + SSM parameters for Jira config.

## Deploy

```powershell
cd terraform
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars (region, environment, tines_webhook_url, guardduty_min_severity, ...)
terraform init
terraform plan
terraform apply
```

## Set secret values out-of-band

Secrets are created empty so values are never in Terraform state:

```bash
aws secretsmanager put-secret-value \
  --secret-id "<project>-<env>/tines-webhook-url" --secret-string "https://..."

aws secretsmanager put-secret-value \
  --secret-id "<project>-<env>/tines-shared-secret" --secret-string "..."
```

## Choose the delivery path

- Default (`enable_lambda_forwarder = false`): EventBridge API Destination → Tines.
- Optional (`enable_lambda_forwarder = true`): EventBridge → Lambda → Tines.

## Costs

GuardDuty is priced per monitored resource; EventBridge/SQS/CloudWatch/Secrets
Manager incur small per-call/GB fees. A few dollars/day is realistic for a
non-trivial account. Use `guardduty_min_severity` to reduce volume.

## Cleanup

```powershell
cd terraform
terraform destroy
```
