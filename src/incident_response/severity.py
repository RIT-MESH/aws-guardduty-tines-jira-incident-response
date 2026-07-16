"""Severity handling for Amazon GuardDuty findings.

GuardDuty reports severity as a floating point score in the range 0.0-10.0.
AWS documents the following bands:

    0.0 - 1.99  -> Low
    2.0 - 5.99  -> Medium
    6.0 - 7.99  -> High
    8.0 - 10.0  -> Critical

See: https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_findings-summary.html
"""

from __future__ import annotations

from enum import StrEnum


class Severity(StrEnum):
    """Canonical internal severity labels."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

    @classmethod
    def from_score(cls, score: float | int | None) -> Severity:
        """Map a numeric GuardDuty severity score to a canonical label.

        Missing or unparseable scores default to ``Low`` so that a finding is
        never silently dropped, while still being clearly labelled.
        """
        if score is None:
            return cls.LOW
        try:
            s = float(score)
        except (TypeError, ValueError):
            return cls.LOW
        if s < 0.0:
            return cls.LOW
        if s < 2.0:
            return cls.LOW
        if s < 6.0:
            return cls.MEDIUM
        if s < 8.0:
            return cls.HIGH
        return cls.CRITICAL


def severity_label(score: float | int | None) -> str:
    """Return the canonical severity label for a score."""
    return Severity.from_score(score).value
