# Demo Guide

A safe demo that uses **sanitized sample findings**, the **local emulator**, and
**mock Jira** — no AWS account, Tines tenant, or Jira site required, and no real
malicious traffic is generated.

## 0. Install

```powershell
python -m pip install -e ".[dev]"
```

## 1. CLI dry-run (no network)

Show how a GuardDuty finding normalizes into a Jira payload:

```powershell
python -m tools.simulate_finding --input examples/guardduty-high-severity.json --dry-run
```

Try other severities/types:

```powershell
python -m tools.simulate_finding --input examples/guardduty-critical-severity.json --dry-run
python -m tools.simulate_finding --input examples/guardduty-s3.json --dry-run
python -m tools.simulate_finding --input examples/guardduty-missing-optional-fields.json --dry-run
```

A malformed event exits non-zero:

```powershell
python -m tools.simulate_finding --input examples/guardduty-malformed.json --dry-run
```

## 2. Local emulator (mock Jira)

Start the emulator:

```powershell
python -m local_emulator.server
```

Health check:

```powershell
curl http://127.0.0.1:8080/health
```

Send a sanitized finding:

```powershell
curl -X POST http://127.0.0.1:8080/webhook `
  -H "Content-Type: application/json" `
  --data @examples/guardduty-high-severity.json
```

Expected: a mock Jira issue response with `"mock": true`:

```json
{ "id": "10001", "key": "SEC-2", "self": "https://example.atlassian.net/rest/api/3/issue/10001", "mock": true }
```

Send the same finding again to see **deduplication** (`"duplicate": true`,
incremented `occurrence_count`).

## 3. Tests

```powershell
python -m pytest
```

## 4. Terraform validation (no AWS credentials needed)

```powershell
cd terraform
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
```

## Safety notes

- All sample events use account `111122223333` and documentation IP ranges only.
- No real malicious traffic is generated.
- `--send` is required to transmit anything; dry-run is the default.
- The emulator makes no real Jira API calls unless explicitly enabled.
