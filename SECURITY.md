# Security Policy

## Reporting a vulnerability

This is an educational portfolio project. If you find a security issue, please
open a private discussion or contact the maintainers rather than filing a public
issue with exploit details.

## Supported versions

Only the latest `main` branch is maintained as a reference implementation.

## Security controls in this project

- **Least-privilege IAM** for EventBridge and Lambda (scoped to exact ARNs).
- **Secrets Manager** references — secrets are created without versions so values
  are never stored in Terraform state. Set values out-of-band.
- **SSM Parameter Store** for non-secret Jira configuration.
- **Webhook authentication** via a shared-secret header (`X-Tines-Shared-Secret`).
- **Input validation** and **payload-size limits** on the local emulator.
- **Request timeouts** and **retry limits** with exponential backoff.
- **Dead-letter queue** for undeliverable events.
- **Logging without sensitive information** — recursive secret masking and URL
  sanitization; no tokens, passwords, or full webhook URLs are logged.
- **Jira API token protection** — tokens live in Secrets Manager / Tines
  credentials, never in code, tfvars, or Git.
- **Terraform state security** — use a remote backend with encryption and locking;
  do not store secrets in state (this project avoids secret versions).
- **Branch protection, dependency scanning, secret scanning, and static analysis**
  are recommended (CI/quality phase).

## Secret rotation guidance

- Rotate the Jira API token periodically and on personnel changes.
- Rotate the Tines shared secret and update both Tines and the EventBridge
  connection / Lambda secret.
- Rotate GuardDuty/Tines/Jira credentials via Secrets Manager and re-deploy.

## Threat model

See [docs/threat-model.md](docs/threat-model.md) for the STRIDE-based analysis.

## Limitations

- Automated destructive containment is intentionally disabled.
- The API Destination path stores the Tines webhook URL in EventBridge config;
  use the Lambda path with Secrets Manager to avoid this.
- This project is educational; review and harden before production use.
