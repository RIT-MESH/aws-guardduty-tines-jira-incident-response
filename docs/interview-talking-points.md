# Interview Talking Points

Use these to discuss the project in interviews.

## Architecture

- Why EventBridge between GuardDuty and Tines: GuardDuty publishes to EventBridge,
  not arbitrary URLs. EventBridge provides matching, delivery, retries and DLQ.
- API Destination (default) vs Lambda (optional): API Destination is simpler and
  serverless; Lambda is for custom signing, transformation, retry logic, or
  pulling secrets from Secrets Manager at runtime to avoid secrets in EventBridge config.

## Event-driven design

- Decoupled producers (GuardDuty) and consumers (Tines/Jira) via EventBridge.
- Severity filtering happens in the event pattern before delivery, reducing cost and noise.
- DLQ + alarms make failures observable and recoverable.

## SOAR automation

- 19-action Tines Story: receive → verify → validate → normalize → map severity →
  dedup → search Jira → create/comment → transition → success/failure handling.
- Credential placeholders only; no secrets in the export.

## Jira integration

- REST API v3 with Atlassian Document Format (ADF) for rich text.
- Configurable priority mapping (sites differ).
- Deduplication via a stable SHA-256 label + JQL search-before-create.

## Infrastructure as Code

- Terraform, least-privilege IAM, Secrets Manager (no values in state), SSM params.
- `terraform fmt -check`, `init -backend=false`, `validate` all green.

## Python engineering

- Typed, modular, stdlib-only; no unnecessary runtime deps.
- Defensive normalization across EC2/S3/IAM/EKS/K8s/malware with missing-field safety.
- 106 tests, 87.9% coverage; ruff/black/mypy clean.
- Testable HTTP client with injectable opener/sleeper (no real network in tests).

## Security

- Recursive secret masking; webhook URL sanitization; structured logs without secrets.
- Webhook shared-secret auth; payload-size limits; input validation.
- STRIDE threat model; automated destructive containment intentionally disabled.

## Resilience

- Retries with exponential backoff and `Retry-After` on 429/5xx; no retry on other 4xx.
- DLQ preserves undeliverable events; CloudWatch alarms on DLQ depth and failed invocations.

## Trade-offs to discuss

- Simplicity over over-engineering (stdlib-only, template Tines Story).
- API Destination places the webhook URL in EventBridge config; Lambda path mitigates.
- `terraform plan`/`apply` need live AWS credentials (not run in repo validation).

## Questions you can answer

- "How would you scale this across many accounts?" — GuardDuty aggregator + multi-account EventBridge.
- "How do you prevent alert fatigue?" — dedup + severity filter + recurrence comments.
- "How do you handle a Tines outage?" — retries + DLQ + alarms; events preserved.
- "How do you rotate the Jira token?" — Secrets Manager rotation; update Tines credential.
