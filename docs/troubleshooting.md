# Troubleshooting

Common issues and fixes.

## Python / tests

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: incident_response` | Run `python -m pip install -e ".[dev]"`. |
| `tomllib.TOMLDecodeError` on install | Ensure `pyproject.toml` has no UTF-8 BOM (re-save as UTF-8 without BOM). |
| Coverage below 85% | Add/fix tests; run `pytest --cov=...`. |
| ruff/black/mypy errors | Run `ruff check . --fix`, `black .`, then re-check. |

## Terraform

| Problem | Fix |
|---|---|
| `Unsupported argument "tags"` on API Destination | The AWS provider does not support tags on `aws_cloudwatch_event_api_destination`; remove it (tags apply via `default_tags`). |
| `terraform init` needs network | Provider download requires internet; use `-backend=false` for local validation. |
| `terraform plan` auth error | Configure AWS credentials; plan is not required for fmt/init/validate. |

## Tines

| Problem | Fix |
|---|---|
| Story import fails | Validate `tines/guardduty-incident-response-story.json` with `python -m json.tool`; re-import. |
| Auth verification rejects events | Ensure the `X-Tines-Shared-Secret` header matches `TINES_SHARED_SECRET`. |
| Liquid expressions error | Action names with spaces must be referenced exactly; adjust in your tenant. |

## Jira

| Problem | Fix |
|---|---|
| 401 Unauthorized | Verify `JIRA_USER_EMAIL` + `JIRA_API_TOKEN` Basic auth header. |
| Priority name rejected | Jira priority names are site-specific; configure `JiraPriorityMapping`. |
| Transition id invalid | Retrieve real ids via `GET /rest/api/3/issue/{key}/transitions`. |
| Duplicate tickets | Ensure the dedup label is not manually removed; check JQL. |

## EventBridge / delivery

| Problem | Fix |
|---|---|
| No events reach Tines | Check the rule pattern and `guardduty_min_severity`; verify GuardDuty is enabled. |
| Events in DLQ | Check Tines/Jira reachability and credentials; inspect DLQ messages. |
| 429 from Jira | The client retries with `Retry-After`; if persistent, reduce volume or raise limits. |
