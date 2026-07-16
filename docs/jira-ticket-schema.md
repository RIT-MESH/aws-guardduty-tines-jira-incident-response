# Jira Ticket Schema

Describes the Jira Cloud incident ticket produced by the workflow, including the
issue fields, labels, priority, optional custom field, and the ADF description
structure.

## 1. Create issue request body

`POST /rest/api/3/issue` accepts:

```json
{
  "fields": {
    "project":     { "key": "SEC" },
    "summary":     "[GuardDuty][High][111122223333][us-east-1] Trojan Dropper detected on EC2 instance.",
    "description": { ... ADF document ... },
    "issuetype":   { "name": "Incident" },
    "priority":    { "name": "High" },
    "labels":      ["guardduty","aws-security","automated-incident","severity-high","environment-dev","gd-<16hex>"]
  }
}
```

When a dedicated custom field is configured (`JiraConfig.finding_id_custom_field`,
e.g. `customfield_10001`), the GuardDuty finding id is also written there:

```json
"customfield_10001": "<finding id>"
```

## 2. Fields

| Field | Required | Value |
|---|---|---|
| `project.key` | yes | Jira project key (default `SEC`, configurable). |
| `summary` | yes | `[GuardDuty][<priority>][<account>][<region>] <title>` |
| `description` | yes | ADF document (see below). |
| `issuetype.name` | yes | Issue type (default `Incident`, configurable). |
| `priority.name` | yes | Mapped from GuardDuty severity (configurable). |
| `labels` | yes | Standard labels + severity + environment + dedup key. |
| `<custom field>` | optional | GuardDuty finding id, when a custom field is configured. |

## 3. Labels

- `guardduty`
- `aws-security`
- `automated-incident`
- `severity-low` / `severity-medium` / `severity-high` / `severity-critical`
- `environment-<env>` (when an environment is provided)
- deduplication key, e.g. `gd-24257196fd7ee4a3`

## 4. Priority

| GuardDuty severity | Label | Default Jira priority |
|---|---|---|
| 0.0–1.99 | Low | Low |
| 2.0–5.99 | Medium | Medium |
| 6.0–7.99 | High | High |
| 8.0–10.0 | Critical | Highest |

Configurable via `JiraPriorityMapping`.

## 5. ADF description structure

A valid Atlassian Document Format document:

```json
{
  "type": "doc",
  "version": 1,
  "content": [
    { "type": "heading", "attrs": { "level": 2 }, "content": [ { "type": "text", "text": "Executive summary" } ] },
    { "type": "paragraph", "content": [ { "type": "text", "text": "<description>" } ] },
    { "type": "heading", "attrs": { "level": 2 }, "content": [ { "type": "text", "text": "Finding details" } ] },
    { "type": "paragraph", "content": [ { "type": "text", "text": "GuardDuty finding ID: <id>" } ] },
    { "type": "paragraph", "content": [ { "type": "text", "text": "Severity: High" } ] },
    { "type": "heading", "attrs": { "level": 2 }, "content": [ { "type": "text", "text": "Affected resources" } ] },
    { "type": "bulletList", "content": [ { "type": "listItem", "content": [ { "type": "paragraph", "content": [ { "type": "text", "text": "EC2 Instance - i-xxx" } ] } ] } ] },
    { "type": "heading", "attrs": { "level": 3 }, "content": [ { "type": "text", "text": "GuardDuty console link" } ] },
    { "type": "paragraph", "content": [ { "type": "text", "text": "https://console.aws.amazon.com/guardduty/home#/findings?search=id%3D<id>" } ] }
  ]
}
```

Sections included: Executive summary, Finding details, Affected resources,
Resource identifiers (when present), Remote actor details (when present),
Recommended investigation steps, Recommended containment steps, Evidence &
automation metadata, and a GuardDuty console link.

## 6. Example created issue response

```json
{
  "id": "10001",
  "key": "SEC-101",
  "self": "https://example.atlassian.net/rest/api/3/issue/10001"
}
```

The local emulator returns a mock equivalent with `"mock": true` (see
`local_emulator/jira_mock.py`).

## 7. Duplicate comment body (ADF)

When a finding recurs, a comment is added instead of a new ticket:

```json
{
  "body": {
    "type": "doc",
    "version": 1,
    "content": [
      { "type": "heading", "attrs": { "level": 3 }, "content": [ { "type": "text", "text": "GuardDuty finding recurrence" } ] },
      { "type": "paragraph", "content": [ { "type": "text", "text": "Finding ID: <id>" } ] },
      { "type": "paragraph", "content": [ { "type": "text", "text": "Last observed: <ts>" } ] }
    ]
  }
}
```
