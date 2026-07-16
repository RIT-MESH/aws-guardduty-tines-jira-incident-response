"""Tests for finding normalization across GuardDuty resource types."""

from __future__ import annotations

from incident_response.exceptions import NormalizationError
from incident_response.normalizer import normalize_event, normalize_finding_detail
from incident_response.severity import Severity


def test_normalize_ec2(high_severity_event):
    f = normalize_event(high_severity_event)
    assert f.severity == Severity.HIGH
    assert f.resources[0].type == "EC2 Instance"
    assert f.resources[0].id == "i-highexample0001"
    assert f.remote_actors[0].ip_address == "192.0.2.20"
    assert f.remote_actors[0].protocol == "TCP"
    assert f.remote_actors[0].port == 443


def test_normalize_s3(s3_event):
    f = normalize_event(s3_event)
    assert any(r.type == "S3 Bucket" for r in f.resources)
    assert f.remote_actors[0].ip_address == "198.51.100.120"


def test_normalize_iam(iam_event):
    f = normalize_event(iam_event)
    assert f.resources[0].type == "IAM Access Key"
    assert f.resources[0].id == "AKIAMEDEXAMPLE0005"
    assert f.remote_actors[0].country == "Example Islands"


def test_normalize_kubernetes(kubernetes_event):
    f = normalize_event(kubernetes_event)
    assert any(r.type == "Kubernetes" for r in f.resources)


def test_normalize_malware(malware_event):
    f = normalize_event(malware_event)
    assert f.service_action_type == "malwareScanAction"
    assert any(r.type == "Malware Scan" for r in f.resources)


def test_normalize_remote_ip_and_country(medium_severity_event):
    f = normalize_event(medium_severity_event)
    assert f.remote_actors[0].ip_address == "203.0.113.55"
    assert f.remote_actors[0].country == "Examplestan"


def test_normalize_organization(high_severity_event):
    f = normalize_event(high_severity_event)
    assert f.remote_actors[0].organization == "Example Hosting"


def test_normalize_network_port_and_protocol(high_severity_event):
    f = normalize_event(high_severity_event)
    assert f.remote_actors[0].port == 443
    assert f.remote_actors[0].protocol == "TCP"


def test_normalize_occurrence_count(critical_severity_event):
    f = normalize_event(critical_severity_event)
    assert f.occurrence_count == 12


def test_normalize_event_count_from_service(recon_event):
    f = normalize_event(recon_event)
    assert f.occurrence_count == 3


def test_normalize_missing_optional_fields(missing_optional_event):
    f = normalize_event(missing_optional_event)
    assert f.resources == []
    assert f.remote_actors == []
    assert f.first_seen is None
    assert f.last_seen is None
    assert f.aws_account_id == "111122223333"
    assert f.severity == Severity.MEDIUM


def test_normalize_invalid_detail_raises():
    import pytest

    with pytest.raises(NormalizationError):
        normalize_finding_detail({"type": "x"})


def test_normalize_malformed_event_raises(malformed_event):
    import pytest

    from incident_response.exceptions import ValidationError

    with pytest.raises(ValidationError):
        normalize_event(malformed_event)


def test_normalize_severity_invalid_string_defaults_low(make_envelope):
    detail = {"id": "x", "type": "Recon:EC2/PortProbeUnprotectedPort", "severity": "bad"}
    f = normalize_event(make_envelope(detail))
    assert f.severity == Severity.LOW
    assert f.severity_score is None


def test_finding_type_short():
    detail = {"id": "x", "type": "UnauthorizedAccess:IAMUser/ConsoleLogin"}
    f = normalize_finding_detail(detail)
    assert f.finding_type_short == "ConsoleLogin"
