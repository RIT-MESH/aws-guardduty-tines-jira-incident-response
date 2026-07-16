"""Tests for GuardDuty severity mapping and Jira priority mapping."""

from __future__ import annotations

import pytest

from incident_response.config import JiraPriorityMapping
from incident_response.severity import Severity, severity_label


@pytest.mark.parametrize(
    "score,expected",
    [
        (0, Severity.LOW),
        (1.99, Severity.LOW),
        (3.9, Severity.MEDIUM),
        (4, Severity.MEDIUM),
        (5.99, Severity.MEDIUM),
        (6.9, Severity.HIGH),
        (7, Severity.HIGH),
        (7.99, Severity.HIGH),
        (8.9, Severity.CRITICAL),
        (9, Severity.CRITICAL),
        (10, Severity.CRITICAL),
    ],
)
def test_severity_from_score(score, expected):
    assert Severity.from_score(score) == expected


def test_negative_severity_clamps_to_low():
    assert Severity.from_score(-5) == Severity.LOW


def test_severity_above_10_is_critical():
    assert Severity.from_score(12) == Severity.CRITICAL


def test_severity_none_defaults_low():
    assert Severity.from_score(None) == Severity.LOW


def test_severity_invalid_defaults_low():
    assert Severity.from_score("not-a-number") == Severity.LOW  # type: ignore[arg-type]


def test_severity_label_string():
    assert severity_label(9.5) == "Critical"
    assert severity_label(1.0) == "Low"


@pytest.mark.parametrize(
    "label,expected_priority",
    [
        ("Low", "Low"),
        ("Medium", "Medium"),
        ("High", "High"),
        ("Critical", "Highest"),
    ],
)
def test_default_priority_mapping(label, expected_priority):
    mapping = JiraPriorityMapping()
    assert mapping.priority_for(label) == expected_priority


def test_configurable_priority_mapping():
    mapping = JiraPriorityMapping(low="4", medium="3", high="2", critical="1")
    assert mapping.priority_for("Critical") == "1"
    assert mapping.priority_for("Low") == "4"


def test_priority_mapping_unknown_label_defaults_low():
    mapping = JiraPriorityMapping()
    assert mapping.priority_for("Unknown") == "Low"
