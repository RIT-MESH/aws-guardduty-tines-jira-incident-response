"""Data models for normalized GuardDuty findings and Jira incidents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .severity import Severity


@dataclass(frozen=True)
class AffectedResource:
    """A single affected resource extracted from a finding."""

    type: str | None = None
    id: str | None = None
    region: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RemoteActor:
    """Remote actor / network details associated with a finding."""

    ip_address: str | None = None
    country: str | None = None
    organization: str | None = None
    port: int | None = None
    protocol: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Finding:
    """A normalized, defensively-extracted GuardDuty finding.

    Every optional field defaults to ``None`` or an empty container so that
    callers never need to special-case missing keys after normalization.
    """

    finding_id: str
    finding_type: str | None = None
    title: str | None = None
    description: str | None = None
    severity_score: float | None = None
    severity: Severity = Severity.LOW
    aws_account_id: str | None = None
    aws_region: str | None = None
    first_seen: str | None = None
    last_seen: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    occurrence_count: int | None = None
    resources: list[AffectedResource] = field(default_factory=list)
    service_name: str | None = None
    service_action: dict[str, Any] = field(default_factory=dict)
    service_action_type: str | None = None
    remote_actors: list[RemoteActor] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def finding_type_short(self) -> str:
        """Return the short, human-readable finding type."""
        if not self.finding_type:
            return "Unknown"
        return self.finding_type.split("/")[-1] if "/" in self.finding_type else self.finding_type

    def resource_identifiers_text(self) -> str:
        """Return a compact, human-readable list of resource identifiers."""
        if not self.resources:
            return ""
        lines = []
        for res in self.resources:
            parts = [res.type or "Resource"]
            if res.id:
                parts.append(res.id)
            if res.region:
                parts.append(f"region={res.region}")
            lines.append(" | ".join(parts))
        return "\n".join(lines)
