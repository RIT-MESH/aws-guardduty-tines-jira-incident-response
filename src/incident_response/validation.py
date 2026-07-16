"""Structural validation of incoming GuardDuty events.

GuardDuty findings are delivered by Amazon EventBridge with a well-defined
envelope, but resource structures vary by finding type and optional fields may
be absent. Validation is intentionally defensive: it checks only the fields
required to drive the workflow and treats everything else as optional.
"""

from __future__ import annotations

from typing import Any

from .exceptions import ValidationError


def is_guardduty_finding_event(event: Any) -> bool:
    """Return True if an event looks like a GuardDuty finding EventBridge event."""
    if not isinstance(event, dict):
        return False
    source = event.get("source")
    detail_type = event.get("detail-type")
    detail = event.get("detail")
    if source != "aws.guardduty":
        return False
    if detail_type != "GuardDuty Finding":
        return False
    return isinstance(detail, dict)


def validate_event(event: Any) -> dict[str, Any]:
    """Validate the high-level structure of a GuardDuty EventBridge event.

    Returns the validated ``detail`` dict on success. Raises ``ValidationError``
    when required envelope or detail fields are missing.
    """
    if not isinstance(event, dict):
        raise ValidationError("Event must be a JSON object")

    if not is_guardduty_finding_event(event):
        raise ValidationError(
            "Event is not a GuardDuty finding event "
            "(expected source='aws.guardduty', detail-type='GuardDuty Finding')"
        )

    detail = event["detail"]

    finding_id = detail.get("id")
    if not finding_id or not isinstance(finding_id, str):
        raise ValidationError("Missing required field detail.id (finding id)")

    finding_type = detail.get("type")
    if not finding_type or not isinstance(finding_type, str):
        raise ValidationError("Missing required field detail.type (finding type)")

    return detail


def validate_finding_detail(detail: Any) -> dict[str, Any]:
    """Validate the inner ``detail`` object of a GuardDuty finding.

    This is useful for callers that already hold the ``detail`` payload, for
    example a Tines action that receives the unwrapped finding.
    """
    if not isinstance(detail, dict):
        raise ValidationError("Finding detail must be a JSON object")

    finding_id = detail.get("id")
    if not finding_id or not isinstance(finding_id, str):
        raise ValidationError("Missing required field id (finding id)")

    finding_type = detail.get("type")
    if not finding_type or not isinstance(finding_type, str):
        raise ValidationError("Missing required field type (finding type)")

    return detail
