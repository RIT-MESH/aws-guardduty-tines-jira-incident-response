"""Simulate a GuardDuty finding: normalize it and show the Jira payload.

Dry-run is the default. No network request is made unless ``--send`` is
explicitly supplied together with a ``--webhook-url``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from incident_response.config import JiraConfig, JiraPriorityMapping
from incident_response.exceptions import ValidationError
from incident_response.http_client import HttpClient
from incident_response.jira import build_issue_payload
from incident_response.logging_config import configure_logging, get_logger
from incident_response.masking import mask_secrets, mask_url
from incident_response.normalizer import normalize_event


def _load_event(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")
    with p.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.simulate_finding",
        description="Normalize a GuardDuty finding and display the Jira incident payload.",
    )
    parser.add_argument("--input", required=True, help="Path to a GuardDuty event JSON file.")
    parser.add_argument("--dry-run", action="store_true", help="Do not send anything (default).")
    parser.add_argument(
        "--send", action="store_true", help="Send the normalized payload to a webhook."
    )
    parser.add_argument("--webhook-url", default=None, help="Webhook URL used with --send.")
    parser.add_argument("--jira-project", default="SEC", help="Jira project key.")
    parser.add_argument("--jira-issue-type", default="Incident", help="Jira issue type name.")
    parser.add_argument("--environment", default=None, help="Environment label (e.g. dev/prod).")
    parser.add_argument(
        "--jira-priority-low",
        default="Low",
        help="Jira priority name for GuardDuty Low severity.",
    )
    parser.add_argument(
        "--jira-priority-medium",
        default="Medium",
        help="Jira priority name for GuardDuty Medium severity.",
    )
    parser.add_argument(
        "--jira-priority-high",
        default="High",
        help="Jira priority name for GuardDuty High severity.",
    )
    parser.add_argument(
        "--jira-priority-critical",
        default="Highest",
        help="Jira priority name for GuardDuty Critical severity.",
    )
    parser.add_argument(
        "--jira-finding-field",
        default=None,
        help="Optional Jira custom field id that stores the GuardDuty finding id.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    log = get_logger("simulate_finding")
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.send and not args.webhook_url:
        print("ERROR: --send requires --webhook-url", file=sys.stderr)
        return 2

    # If neither flag is given, default to dry-run.
    dry_run = not args.send

    try:
        event = _load_event(args.input)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: could not load input: {exc}", file=sys.stderr)
        log.error("load_failed", extra={"error": str(exc)})
        return 1

    try:
        finding = normalize_event(event)
    except ValidationError as exc:
        print(f"ERROR: invalid GuardDuty event: {exc}", file=sys.stderr)
        log.error("validation_failed", extra={"error": str(exc)})
        return 1

    priority_mapping = JiraPriorityMapping(
        low=args.jira_priority_low,
        medium=args.jira_priority_medium,
        high=args.jira_priority_high,
        critical=args.jira_priority_critical,
    )
    jira_config = JiraConfig(
        project_key=args.jira_project,
        issue_type=args.jira_issue_type,
        finding_id_custom_field=args.jira_finding_field,
        priority_mapping=priority_mapping,
        dry_run=dry_run,
    )

    payload = build_issue_payload(finding, jira_config, environment=args.environment)

    print(json.dumps(mask_secrets(finding.raw), indent=2, default=str))
    print("---JIRA PAYLOAD---")
    print(json.dumps(payload, indent=2, default=str))

    if dry_run:
        print("---DRY RUN: nothing was sent---")
        return 0

    # --send path
    client = HttpClient()
    log.info("sending", extra={"url": mask_url(args.webhook_url)})
    response = client.post_json(args.webhook_url, payload)
    print("---WEBHOOK RESPONSE---")
    print(json.dumps(mask_secrets(response), indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
