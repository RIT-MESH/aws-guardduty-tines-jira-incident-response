# Jira Setup Guide

This guide explains how to configure Jira Cloud REST API v3 for the incident-response
workflow: creating an API token, building the issue payload with Atlassian Document
Format (ADF), mapping severity to priority, and searching for duplicate tickets.

## 1. Prerequisites

- A Jira Cloud site, e.g. `https://your-domain.atlassian.net`.
- A project (e.g. key `SEC`) with an issue type named `Incident` (or your configured type).
- An Atlassian account that can create API tokens.

## 2. Create a Jira API token

1. Sign in to https://id.atlassian.com/manage-profile/security/api-tokens.
2. Click **Create API token**, label it (e.g. `guardduty-tines-ir`), and copy the value.
3. Store the value in Tines as the `JIRA_API_TOKEN` credential (see `setup-tines.md`)
   or in AWS Secrets Manager (referenced by the Lambda/Terraform layer).
4. Never commit the token to Git or place it in Terraform variables files.

Jira Cloud REST API v3 uses **HTTP Basic authentication** with the email and API
token: `Authorization: Basic base64(<email>:<api_token>)`. The Tines Story builds
this header from the `JIRA_USER_EMAIL` and `JIRA_API_TOKEN` credentials.

## 3. REST API endpoints used

| Operation | Method & path |
|---|---|
| Create issue | `POST /rest/api/3/issue` |
| Search issues (JQL) | `GET /rest/api/3/search` |
| Add comment | `POST /rest/api/3/issue/{issueIdOrKey}/comment` |
| Transitions | `GET` / `POST /rest/api/3/issue/{issueIdOrKey}/transitions` |

Reference: https://developer.atlassian.com/cloud/jira/platform/rest/v3/

## 4. Issue summary format

```
[GuardDuty][<Priority>][<AWS account>][<Region>] <Finding title>
```

Example: `[GuardDuty][High][111122223333][us-east-1] Trojan Dropper detected on EC2 instance.`

## 5. Atlassian Document Format (ADF) description

Jira REST API v3 requires rich-text fields (description and comments) as ADF
documents, not plain HTML. The Python layer (`src/incident_response/jira.py`
`build_description`) and the Tines Story both produce a valid ADF document:

```json
{
  "type": "doc",
  "version": 1,
  "content": [
    { "type": "heading", "attrs": { "level": 2 }, "content": [ { "type": "text", "text": "Executive summary" } ] },
    { "type": "paragraph", "content": [ { "type": "text", "text": "<finding description>" } ] },
    { "type": "paragraph", "content": [ { "type": "text", "text": "GuardDuty finding ID: <id>" } ] },
    { "type": "paragraph", "content": [ { "type": "text", "text": "Severity: High" } ] }
  ]
}
```

The description includes: executive summary, finding ID, type, severity, AWS
account, AWS region, first/last observed, affected resources, remote actor
details, recommended investigation steps, recommended containment steps, evidence
& automation metadata, and a GuardDuty console link.

## 6. Priority mapping

GuardDuty severity scores map to Jira priorities. The default mapping is
configurable via `JiraPriorityMapping` (Python) or the Tines severity-mapping
action:

| GuardDuty score | Severity label | Default Jira priority |
|---|---|---|
| 0.0 – 1.99 | Low | Low |
| 2.0 – 5.99 | Medium | Medium |
| 6.0 – 7.99 | High | High |
| 8.0 – 10.0 | Critical | Highest |

> Jira sites use different priority names or IDs. Configure the mapping to match
> your project's priorities (e.g. some projects use numeric IDs `1`–`4`).

## 7. Labels

Each issue is labelled with:

- `guardduty`
- `aws-security`
- `automated-incident`
- `severity-<low|medium|high|critical>`
- `environment-<env>`
- the deduplication key (see `deduplication.md`)

## 8. Deduplication

Before creating a ticket, the workflow searches Jira using the deduplication key.
If a ticket exists, it adds a recurrence comment and updates last-seen/severity
instead of creating a duplicate. See `deduplication.md` for details and sample JQL.

## 9. Incident lifecycle transitions

Suggested lifecycle: `New → Triage → Investigating → Contained → Remediated → Closed`.
The Tines Story transitions new issues to **Investigating** by default. Transition
IDs differ per project; retrieve them with
`GET /rest/api/3/issue/{key}/transitions` and update the **Transition issue to
Investigating** action's `transition.id` to match your project.

## 10. Rate limits and error handling

- Jira enforces rate limits; the Python HTTP client retries on 429 (honouring
  `Retry-After`) and 5xx, and does not retry other 4xx errors.
- The Tines Story emits a **Jira failure event** and records an automation error
  (without secrets) when a Jira API call fails.

## 11. Limitations

- ADF support varies by field; some custom fields accept plain text only.
- Transition IDs are project-specific and are not portable across Jira sites.
- Priority names/IDs are site-specific.
- Jira Cloud API tokens are per-user; rotate them and scope the Atlassian account.
