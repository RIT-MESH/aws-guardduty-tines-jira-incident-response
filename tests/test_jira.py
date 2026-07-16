"""Tests for Jira ADF payload generation, deduplication and JQL."""

from __future__ import annotations

import pytest

from incident_response.config import JiraConfig, JiraPriorityMapping
from incident_response.exceptions import JiraPayloadError
from incident_response.jira import (
    build_description,
    build_duplicate_comment,
    build_issue_payload,
    build_jql_for_finding,
    build_summary,
    deduplication_key,
)
from incident_response.normalizer import normalize_event


def _finding(event):
    return normalize_event(event)


def test_adf_structure_valid(high_severity_event):
    doc = build_description(_finding(high_severity_event))
    assert doc["type"] == "doc"
    assert doc["version"] == 1
    assert isinstance(doc["content"], list) and doc["content"]
    # Every node has a type.
    for node in doc["content"]:
        assert "type" in node


def test_issue_summary_format(high_severity_event):
    f = _finding(high_severity_event)
    summary = build_summary(f)
    assert summary.startswith("[GuardDuty][High][111122223333][us-east-1]")
    assert "Trojan" in summary


def test_issue_payload_labels_and_priority(high_severity_event):
    f = _finding(high_severity_event)
    payload = build_issue_payload(f, JiraConfig(), environment="dev")
    fields = payload["fields"]
    assert fields["project"]["key"] == "SEC"
    assert fields["issuetype"]["name"] == "Incident"
    assert fields["priority"]["name"] == "High"
    assert "guardduty" in fields["labels"]
    assert "severity-high" in fields["labels"]
    assert "environment-dev" in fields["labels"]
    assert fields["description"]["type"] == "doc"


def test_priority_by_id_via_configurable_mapping(critical_severity_event):
    f = _finding(critical_severity_event)
    mapping = JiraPriorityMapping(low="4", medium="3", high="2", critical="1")
    cfg = JiraConfig(priority_mapping=mapping)
    payload = build_issue_payload(f, cfg)
    assert payload["fields"]["priority"]["name"] == "1"


def test_custom_guardduty_field_present(high_severity_event):
    f = _finding(high_severity_event)
    cfg = JiraConfig(finding_id_custom_field="customfield_10001")
    payload = build_issue_payload(f, cfg)
    assert payload["fields"]["customfield_10001"] == f.finding_id


def test_custom_field_absent_when_not_configured(high_severity_event):
    f = _finding(high_severity_event)
    payload = build_issue_payload(f, JiraConfig())
    assert "customfield_10001" not in payload["fields"]


def test_deduplication_key_is_stable(high_severity_event):
    f1 = _finding(high_severity_event)
    f2 = _finding(high_severity_event)
    assert deduplication_key(f1) == deduplication_key(f2)
    assert deduplication_key(f1).startswith("gd-")


def test_deduplication_key_differs_per_finding(high_severity_event, medium_severity_event):
    a = deduplication_key(_finding(high_severity_event))
    b = deduplication_key(_finding(medium_severity_event))
    assert a != b


def test_jql_escaping_safe():
    from incident_response.models import Finding
    from incident_response.severity import Severity

    f = Finding(finding_id="evil'; DROP TABLE; --", severity=Severity.LOW)
    jql = build_jql_for_finding(f)
    assert ";" not in jql
    assert "'" not in jql


def test_jql_with_custom_field():
    from incident_response.models import Finding
    from incident_response.severity import Severity

    f = Finding(finding_id="abc123", severity=Severity.LOW)
    jql = build_jql_for_finding(f, custom_field="customfield_10001")
    assert "customfield_10001" in jql
    assert "abc123" in jql


def test_duplicate_comment_payload(high_severity_event):
    f = _finding(high_severity_event)
    comment = build_duplicate_comment(f, occurrence_count=5)
    assert comment["type"] == "doc"
    text = str(comment["content"])
    assert "recurrence" in text or "Finding ID" in text


def test_issue_payload_requires_project_key(high_severity_event):
    f = _finding(high_severity_event)
    with pytest.raises(JiraPayloadError):
        build_issue_payload(f, JiraConfig(project_key=""))


def test_description_has_console_link(high_severity_event):
    f = _finding(high_severity_event)
    doc = build_description(f)
    rendered = str(doc["content"])
    assert "console.aws.amazon.com/guardduty" in rendered
    assert f.finding_id in rendered
