# Event Schema

The schema of the Amazon GuardDuty findings this workflow consumes.

## EventBridge envelope

GuardDuty publishes findings to the default EventBridge bus with this envelope:

```json
{
  "version": "0",
  "id": "1a2b3c4d-...",
  "detail-type": "GuardDuty Finding",
  "source": "aws.guardduty",
  "account": "111122223333",
  "time": "2026-07-17T12:00:00Z",
  "region": "us-east-1",
  "resources": [],
  "detail": { ... }
}
```

The EventBridge rule matches `source = aws.guardduty` and
`detail-type = GuardDuty Finding`, with a numeric severity filter.

## detail object (key fields)

| Field | Required | Description |
|---|---|---|
| `id` | yes | Stable finding id (87-char hex). Used for dedup. |
| `type` | yes | Finding type, e.g. `Trojan:EC2/TrojanDropper`. |
| `title` | no | Human-readable title. |
| `description` | no | Description. |
| `severity` | no | Numeric score 0.0–10.0. |
| `accountId` | no | AWS account id. |
| `region` | no | AWS region. |
| `createdAt` / `updatedAt` | no | Timestamps. |
| `resource` | no | Affected resources (varies by type). |
| `service.action` | no | Service action details (varies by type). |
| `service.eventFirstSeen` / `eventLastSeen` | no | Observation window. |
| `service.eventCount` | no | Occurrence count. |
| `service.additionalInfo` | no | Extra info (may be a JSON string). |

## Severity bands

| Score | Label |
|---|---|
| 0.0 – 1.99 | Low |
| 2.0 – 5.99 | Medium |
| 6.0 – 7.99 | High |
| 8.0 – 10.0 | Critical |

Reference: https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_findings-summary.html

## Resource structures (vary by finding type)

GuardDuty does not use identical resource structures across finding types. The
normalizer defensively extracts the common ones:

- `resource.instanceDetails` — EC2 instances (list or object).
- `resource.s3BucketDetails` — S3 buckets (list).
- `resource.accessKeyDetails` — IAM access keys.
- `resource.eksClusterDetails` — EKS clusters.
- `resource.kubernetesDetails` — Kubernetes API.
- `resource.malwareScanDetails` — Malware Protection scans.
- `resource.containerDetails` — Containers.
- `resource.resourceDetails` — Other resources.

All optional fields are handled safely (missing → `None`/empty).

## Service action structures

- `service.action.networkConnectionAction` — includes `remoteIpDetails`, `remotePortDetails`, `protocol`.
- `service.action.awsApiCallAction` — includes `remoteIpDetails`, `api`, `service`.
- `service.action.portProbeAction` / `dnsRequestsAction` — may include `remoteIpDetails`.
- `service.action.kubernetesApiCallAction` — Kubernetes API calls.
- `service.action.malwareScanAction` — malware scan results.

## Sanitized examples

See `examples/` (account `111122223333`, documentation IP ranges
`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`, fake ARNs, no real secrets).
