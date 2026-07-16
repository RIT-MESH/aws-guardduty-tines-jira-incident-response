"""Jira Cloud REST API v3 payload generation, deduplication and JQL helpers.

The Jira REST API v3 ``POST /rest/api/3/issue`` endpoint expects rich-text
fields (``description`` and comments) as Atlassian Document Format (ADF)
documents rather than plain HTML. This module builds valid ADF documents from a
normalized ``Finding`` so callers do not need to know ADF.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from .config import JiraConfig
from .exceptions import JiraPayloadError
from .models import Finding

_GUARDDUTY_CONSOLE_URL = (
    "https://console.aws.amazon.com/guardduty/home?" "#/findings?search=id%3D{finding_id}"
)

# GuardDuty finding ids are 87-character hex strings which are safe in JQL
# string literals, but we sanitise defensively anyway.
_JQL_SAFE = re.compile(r"[^A-Za-z0-9:\-]")


def build_summary(finding: Finding) -> str:
    """Build the Jira issue summary.

    Format: ``[GuardDuty][<Priority>][<account>][<region>] <title>``
    """
    priority = finding.severity.value
    account = finding.aws_account_id or "unknown-account"
    region = finding.aws_region or "unknown-region"
    title = finding.title or finding.finding_type or finding.finding_id
    return f"[GuardDuty][{priority}][{account}][{region}] {title}"


def _adf_text(text: str | None) -> dict[str, Any]:
    """Build an ADF paragraph node containing a single text run."""
    return {
        "type": "paragraph",
        "content": [{"type": "text", "text": text if text else "N/A"}],
    }


def _adf_heading(text: str, level: int = 3) -> dict[str, Any]:
    return {
        "type": "heading",
        "attrs": {"level": level},
        "content": [{"type": "text", "text": text}],
    }


def _adf_bullet(text: str) -> dict[str, Any]:
    return {
        "type": "bulletList",
        "content": [
            {
                "type": "listItem",
                "content": [_adf_text(text)],
            }
        ],
    }


def _adf_key_value(label: str, value: str | None) -> dict[str, Any]:
    return _adf_text(f"{label}: {value if value else 'N/A'}")


def build_description(finding: Finding) -> dict[str, Any]:
    """Build a valid ADF document for the Jira issue description."""
    content: list[dict[str, Any]] = []

    content.append(_adf_heading("Executive summary", 2))
    content.append(
        _adf_text(
            finding.description
            or f"Amazon GuardDuty reported a {finding.severity.value} severity "
            f"finding of type {finding.finding_type or 'unknown'}."
        )
    )

    content.append(_adf_heading("Finding details", 2))
    content.append(_adf_key_value("GuardDuty finding ID", finding.finding_id))
    content.append(_adf_key_value("Finding type", finding.finding_type))
    content.append(_adf_key_value("Severity", finding.severity.value))
    if finding.severity_score is not None:
        content.append(_adf_key_value("Severity score", f"{finding.severity_score:.1f}"))
    content.append(_adf_key_value("AWS account", finding.aws_account_id))
    content.append(_adf_key_value("AWS region", finding.aws_region))
    content.append(_adf_key_value("First observed", finding.first_seen))
    content.append(_adf_key_value("Last observed", finding.last_seen))

    content.append(_adf_heading("Affected resources", 2))
    if finding.resources:
        for res in finding.resources:
            label = f"{res.type or 'Resource'} - {res.id or 'unknown id'}"
            content.append(_adf_bullet(label))
    else:
        content.append(_adf_text("No affected resources reported."))

    if finding.resource_identifiers_text():
        content.append(_adf_heading("Resource identifiers", 3))
        content.append(_adf_text(finding.resource_identifiers_text()))

    if finding.remote_actors:
        content.append(_adf_heading("Remote actor details", 2))
        for actor in finding.remote_actors:
            parts = [f"IP {actor.ip_address or 'unknown'}"]
            if actor.country:
                parts.append(f"({actor.country})")
            if actor.port is not None:
                parts.append(f"port {actor.port}")
            content.append(_adf_bullet(" ".join(parts)))

    content.append(_adf_heading("Recommended investigation steps", 2))
    content.append(_adf_text(investigation_steps(finding)))

    content.append(_adf_heading("Recommended containment steps", 2))
    content.append(_adf_text(containment_steps(finding)))

    content.append(_adf_heading("Evidence & automation metadata", 2))
    content.append(_adf_text(f"Service: {finding.service_name or 'N/A'}"))
    content.append(_adf_text(f"Service action: {finding.service_action_type or 'N/A'}"))
    content.append(_adf_text(f"Deduplication key: {deduplication_key(finding)}"))

    console = _GUARDDUTY_CONSOLE_URL.format(finding_id=finding.finding_id)
    content.append(_adf_heading("GuardDuty console link", 3))
    content.append(_adf_text(console))

    return {
        "type": "doc",
        "version": 1,
        "content": content,
    }


def investigation_steps(finding: Finding) -> str:
    """Return short, finding-aware recommended investigation steps."""
    t = (finding.finding_type or "").lower()
    if "credentialaccess" in t or "iamuser" in t or "unauthorizedaccess" in t:
        return (
            "1. Identify which IAM principal generated the finding. "
            "2. Review CloudTrail for anomalous API calls around last_seen. "
            "3. Check whether the access key is still active. "
            "4. Do NOT disable the key before evidence is captured."
        )
    if "cryptocurrency" in t:
        return (
            "1. Identify the EC2 instance and its security groups. "
            "2. Review VPC flow logs for outbound mining connections. "
            "3. Capture process/network evidence. "
            "4. Isolate the instance only after evidence capture."
        )
    return (
        "1. Review the GuardDuty finding and affected resources. "
        "2. Correlate with CloudTrail and VPC flow logs. "
        "3. Determine blast radius and whether human approval is required before containment."
    )


def containment_steps(finding: Finding) -> str:
    """Return recommended containment steps.

    Automated destructive containment is intentionally NOT performed by this
    workflow; these steps are guidance for the human responder.
    """
    t = (finding.finding_type or "").lower()
    if "iamuser" in t or "credentialaccess" in t or "unauthorizedaccess" in t:
        return (
            "Deactivate or rotate the IAM access key (human approval required). "
            "Revoke active sessions. Review IAM policies attached to the principal."
        )
    if "cryptocurrency" in t or "trojan" in t or "ec2" in t:
        return (
            "Isolate the EC2 instance by moving it to a quarantine security group "
            "(human approval required). Capture a memory/disk snapshot before termination."
        )
    return "Apply the playbook-specific containment step after human approval."


def deduplication_key(finding: Finding) -> str:
    """Generate a stable deduplication key for a finding.

    The key is derived from the GuardDuty finding id (which is stable across
    occurrences of the same finding) so it can be used to correlate repeated
    observations of the same underlying issue without creating duplicate tickets.
    """
    base = finding.finding_id
    return "gd-" + hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


def build_jql_for_finding(finding: Finding, custom_field: str | None = None) -> str:
    """Build a JQL query to find an existing ticket for this finding.

    When a dedicated custom field is configured we search it directly;
    otherwise we search the finding id within the issue text and labels.
    """
    safe_id = _JQL_SAFE.sub("", finding.finding_id)
    if custom_field:
        return f'project = "{{project}}" AND "{custom_field}" = "{safe_id}"'
    dedup = deduplication_key(finding)
    return f'project = "{{project}}" AND ' f'(text ~ "{safe_id}" OR labels = "{dedup}")'


def build_issue_payload(
    finding: Finding,
    config: JiraConfig,
    environment: str | None = None,
) -> dict[str, Any]:
    """Build the JSON body for ``POST /rest/api/3/issue``."""
    if not config.project_key:
        raise JiraPayloadError("Jira project key is required")

    labels = config.safe_labels(environment)
    labels = labels + [f"severity-{finding.severity.value.lower()}"]
    labels.append(deduplication_key(finding))

    fields: dict[str, Any] = {
        "project": {"key": config.project_key},
        "summary": build_summary(finding),
        "description": build_description(finding),
        "issuetype": {"name": config.issue_type},
        "labels": labels,
        "priority": {"name": config.priority_mapping.priority_for(finding.severity.value)},
    }

    if config.finding_id_custom_field:
        fields[config.finding_id_custom_field] = finding.finding_id

    return {"fields": fields}


def build_duplicate_comment(
    finding: Finding, occurrence_count: int | None = None
) -> dict[str, Any]:
    """Build an ADF comment body for a duplicate (recurring) finding."""
    content = [
        _adf_heading("GuardDuty finding recurrence", 3),
        _adf_key_value("Finding ID", finding.finding_id),
        _adf_key_value("Last observed", finding.last_seen),
        _adf_key_value("Current severity", finding.severity.value),
    ]
    if occurrence_count is not None:
        content.append(_adf_key_value("Occurrence count", str(occurrence_count)))
    content.append(_adf_text("No new ticket created; this finding is already tracked."))
    return {"type": "doc", "version": 1, "content": content}
