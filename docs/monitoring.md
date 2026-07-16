# Monitoring

Observability and alerting for the workflow.

## CloudWatch Logs

- Log group `/aws/lambda/<project>-<env>-forwarder` (retention configurable via
  `log_retention_days`). Structured JSON logs with secret masking.

## Alarms

| Alarm | Metric | Trigger |
|---|---|---|
| `<prefix>-dlq-depth` | `AWS/SQS ApproximateNumberOfMessagesVisible` | >= 1 message in the DLQ |
| `<prefix>-eb-failed-invocations` | `AWS/Events FailedInvocations` | >= 1 failed EventBridge delivery (API Destination path) |
| `<prefix>-lambda-errors` | `AWS/Lambda Errors` | >= 1 Lambda error (Lambda path) |

All alarms use `treat_missing_data = notBreaching`.

## Dead-letter queue

- SQS DLQ with SSE and configurable message retention (default 14 days).
- Undeliverable EventBridge targets and Lambda failures route here.
- DLQ depth is the primary "something needs operator attention" signal.

## Resilience

- HTTP client retries on timeout / 408 / 429 (honouring `Retry-After`) / 5xx.
- No retry on other 4xx (permanent).
- Retry exhaustion surfaces as a transient error and the event can be dead-lettered.

## What to do when an alarm fires

1. Check the DLQ for the failed event payload.
2. Inspect CloudWatch Logs for the forwarder (no secrets are logged).
3. Verify Tines/Jira reachability and credentials.
4. Re-drive or reprocess the event after fixing the root cause.
