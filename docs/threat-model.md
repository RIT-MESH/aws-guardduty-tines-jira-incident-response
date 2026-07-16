# Threat Model (STRIDE)

A lightweight STRIDE-based threat model for the workflow. Assumptions: AWS
account is trusted infrastructure; Tines and Jira are managed SaaS; the inbound
webhook is internet-reachable.

## Assumptions

- GuardDuty/EventBridge are trusted AWS services.
- The Tines webhook URL may be discovered by an attacker.
- Jira API tokens are long-lived and high-value.
- Operators may misconfigure IAM or commit secrets.

## STRIDE table

| Threat (STRIDE) | Scenario | Impact | Mitigation |
|---|---|---|---|
| Spoofing | Fake webhook submission to Tines | False tickets / alert fatigue | Shared-secret header (`X-Tines-Shared-Secret`); `Verify authentication` action rejects missing/incorrect secret. |
| Tampering | Event tampering in transit | Wrong ticket data | HTTPS endpoints; EventBridge signed delivery; payload validation rejects malformed events. |
| Repudiation | Attacker denies triggering actions | Audit gap | Structured JSON logs with request ids; Jira comment/audit trail records automation metadata. |
| Information disclosure | Jira API token leakage | Account compromise | Token stored in Secrets Manager / Tines credentials; never logged; recursive masking; least-privilege IAM. |
| Information disclosure | Terraform state leakage | Secret exposure | Secrets created without versions (not in state); remote state with encryption/locking; no secrets in tfvars. |
| Information disclosure | Sensitive data in logs | PII/secret exposure | Recursive secret masking; webhook URL sanitization; structured logging. |
| Denial of service | Duplicate-ticket flooding | SOC fatigue | Stable dedup key + Jira search-before-create; severity filter reduces volume. |
| Denial of service | Alert suppression / noise | Missed incidents | Dedup does not suppress — it comments and updates severity; DLQ + alarms catch delivery failures. |
| Denial of service | Tines or Jira outage | Stuck workflow | Retries/backoff; DLQ preserves events; alarms alert operators. |
| Elevation of privilege | Excessive IAM permissions | Blast radius | Least-privilege IAM scoped to exact ARNs; no wildcard secrets access. |
| Tampering | Replay of old findings | Duplicate processing | Dedup by stable finding id; recurrence comment instead of new ticket. |

## Notes

- Automated destructive remediation is intentionally disabled, removing a class
  of "elevation via automation" risks.
- The API Destination path places the webhook URL in EventBridge config; the
  Lambda + Secrets Manager path avoids this.
