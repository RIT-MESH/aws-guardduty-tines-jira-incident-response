"""Tests for GuardDuty event validation."""

from __future__ import annotations

import pytest

from incident_response.exceptions import ValidationError
from incident_response.validation import (
    is_guardduty_finding_event,
    validate_event,
    validate_finding_detail,
)


def _detail(**overrides):
    base = {"id": "finding-1", "type": "Recon:EC2/PortProbeUnprotectedPort"}
    base.update(overrides)
    return base


def test_valid_envelope(high_severity_event):
    detail = validate_event(high_severity_event)
    assert detail["id"]
    assert isinstance(detail, dict)


def test_is_guardduty_finding_event_true(high_severity_event):
    assert is_guardduty_finding_event(high_severity_event) is True


def test_invalid_source(make_envelope):
    event = make_envelope(_detail())
    event["source"] = "aws.ec2"
    assert is_guardduty_finding_event(event) is False
    with pytest.raises(ValidationError):
        validate_event(event)


def test_invalid_detail_type(make_envelope):
    event = make_envelope(_detail())
    event["detail-type"] = "EC2 Instance State-change Notification"
    with pytest.raises(ValidationError):
        validate_event(event)


def test_missing_detail(make_envelope):
    event = {"version": "0", "source": "aws.guardduty", "detail-type": "GuardDuty Finding"}
    with pytest.raises(ValidationError):
        validate_event(event)


def test_missing_finding_id(make_envelope):
    event = make_envelope({"type": "Recon:EC2/PortProbeUnprotectedPort"})
    with pytest.raises(ValidationError):
        validate_event(event)


def test_missing_type(make_envelope):
    event = make_envelope({"id": "finding-1"})
    with pytest.raises(ValidationError):
        validate_event(event)


def test_missing_account_is_allowed(make_envelope):
    # account is optional for validation; normalization handles it.
    detail = validate_event(make_envelope(_detail()))
    assert detail["id"] == "finding-1"


def test_missing_region_is_allowed(make_envelope):
    detail = {"id": "x", "type": "Recon:EC2/PortProbeUnprotectedPort"}
    out = validate_event(make_envelope(detail))
    assert out["id"] == "x"


def test_missing_severity_is_allowed(make_envelope):
    # severity is optional at validation time; normalization defaults it.
    out = validate_event(make_envelope(_detail()))
    assert "severity" not in out or out.get("severity") is None


def test_non_dict_event_rejected():
    with pytest.raises(ValidationError):
        validate_event("not a dict")  # type: ignore[arg-type]


def test_validate_finding_detail_valid():
    out = validate_finding_detail(_detail())
    assert out["id"] == "finding-1"


def test_validate_finding_detail_missing_id():
    with pytest.raises(ValidationError):
        validate_finding_detail({"type": "x"})


def test_validate_finding_detail_non_dict():
    with pytest.raises(ValidationError):
        validate_finding_detail(["not", "a", "dict"])  # type: ignore[arg-type]
