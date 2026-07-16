# Tines Setup Guide

This guide explains how to import the pre-built Tines Story, create the required
credentials, and wire Amazon EventBridge to your Tines webhook.

> The Story export (`tines/guardduty-incident-response-story.json`) uses
> **credential placeholders only**. No real secrets are stored in the repository.

## 1. Prerequisites

- A Tines tenant (cloud). Tines offers a free tier for evaluation; see the Tines
  pricing page for current availability (pricing can change).
- The Story file in this repository: `tines/guardduty-incident-response-story.json`.
- A Jira Cloud site and an API token (see `setup-jira.md`).

## 2. Import the Story

1. Sign in to your Tines tenant.
2. Go to **Stories** and create a new Story (or open an existing one).
3. Use **Import** and upload `tines/guardduty-incident-response-story.json`.
4. The imported Story contains 19 actions covering receive, verify, validate,
   normalize, extract, severity mapping, deduplication, Jira search, create,
   comment, transition, and success/failure/error handling.
5. Open the **Receive GuardDuty finding** webhook action to view its webhook URL.

## 3. Create the required Tines credentials

Create four credentials in your Tines tenant (Credentials → New credential). Use
the exact names referenced by the Story placeholders:

| Credential name | Type | Value | Notes |
|---|---|---|---|
| `JIRA_BASE_URL` | Text | `https://your-domain.atlassian.net` | Your Jira Cloud base URL (no trailing slash). |
| `JIRA_USER_EMAIL` | Text | `you@example.com` | The Atlassian account email used for the API token. |
| `JIRA_API_TOKEN` | Text | your Jira API token | See `setup-jira.md` for how to create it. Mark as sensitive. |
| `TINES_SHARED_SECRET` | Text | a random shared secret | Used to authenticate inbound GuardDuty webhooks. Mark as sensitive. |

> Never paste real credential values into the Story export or commit them to Git.
> Tines stores the real values in its credential vault; the export only references
> the names.

## 4. Configure the webhook authentication

The **Receive GuardDuty finding** webhook action expects the shared secret in an
`X-Tines-Shared-Secret` header. The value must match `TINES_SHARED_SECRET`. The
**Verify authentication** action checks this header before any further processing.

## 5. Point EventBridge at the Tines webhook

Two supported paths (configure only one):

### A. EventBridge API Destination (preferred, default)

1. Copy the webhook URL from the **Receive GuardDuty finding** action.
2. Set `tines_webhook_url` in your `terraform.tfvars` to that URL.
3. Set `tines_shared_secret` to the same value as `TINES_SHARED_SECRET`
   (the EventBridge connection sends it in the `X-Tines-Shared-Secret` header).
4. Keep `enable_lambda_forwarder = false` and run `terraform apply`.

### B. Lambda forwarder (optional)

Set `enable_lambda_forwarder = true`. The Lambda reads `TINES_WEBHOOK_URL` and
`TINES_SHARED_SECRET` from its environment/Secrets Manager and posts the
normalized event to the webhook. This is useful when you need custom request
signing, transformation, or retry logic, or when you do not want the webhook URL
in EventBridge configuration.

## 6. Test the webhook safely

Use a sanitized sample finding (no real traffic):

```powershell
$headers = @{ "X-Tines-Shared-Secret" = "<your shared secret>"; "Content-Type" = "application/json" }
Invoke-RestMethod -Method Post -Uri "<Tines webhook URL>" -Headers $headers `
  -InFile (Resolve-Path "examples/guardduty-high-severity.json")
```

```bash
curl -X POST "<Tines webhook URL>" \
  -H "X-Tines-Shared-Secret: <your shared secret>" \
  -H "Content-Type: application/json" \
  --data @examples/guardduty-high-severity.json
```

Observe the Story execution in Tines and the resulting Jira ticket (or a mock
ticket if you are testing against the local emulator).

## 7. Mapping to the Story actions

| Story action | Purpose |
|---|---|
| Receive GuardDuty finding | Webhook entry point. |
| Verify authentication | Confirms the shared-secret header is present. |
| Is well-formed GuardDuty event | Validates envelope + required fields. |
| Normalize finding | Extracts id/type/title/severity/account/region/etc. |
| Extract resource details | Extracts resource + service action JSON. |
| Map severity to priority | GuardDuty score → Jira priority + severity label. |
| Generate deduplication key | Stable hash of the finding id. |
| Build JQL search | JQL to find an existing ticket. |
| Search Jira for existing issue | `GET /rest/api/3/search`. |
| Issue already exists | Branches on duplicate detection. |
| Build ADF description | Atlassian Document Format description. |
| Build create issue payload | Assembles the create-issue body. |
| Create Jira issue | `POST /rest/api/3/issue`. |
| Add duplicate comment | Adds a recurrence comment to an existing ticket. |
| Transition issue to Investigating | Moves the ticket along the lifecycle. |
| Emit success event | Success outcome event. |
| Emit malformed-event event | Handles bad/unauthenticated input. |
| Emit Jira failure event | Handles Jira API failures. |
| Record automation error | Logs an error record without secrets. |

## 8. Cleanup

- Remove the Story in Tines when finished.
- Delete the Tines credentials you created for testing.
- Run `terraform destroy` to remove the AWS-side resources.
