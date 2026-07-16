"""Configuration objects for the incident-response automation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class JiraPriorityMapping:
    """Maps canonical severity labels to Jira priority names.

    Jira sites use different priority names and IDs. This mapping is fully
    configurable so the workflow adapts to the target Jira project.
    """

    low: str = "Low"
    medium: str = "Medium"
    high: str = "High"
    critical: str = "Highest"

    def priority_for(self, severity_label: str) -> str:
        """Return the configured Jira priority name for a severity label."""
        mapping = {
            "Low": self.low,
            "Medium": self.medium,
            "High": self.high,
            "Critical": self.critical,
        }
        return mapping.get(severity_label, self.low)


@dataclass(frozen=True)
class JiraConfig:
    """Configuration for building and sending Jira incident payloads."""

    project_key: str = "SEC"
    issue_type: str = "Incident"
    finding_id_custom_field: str | None = None
    priority_mapping: JiraPriorityMapping = field(default_factory=JiraPriorityMapping)
    labels: tuple[str, ...] = ("guardduty", "aws-security", "automated-incident")
    base_url: str | None = None
    user_email: str | None = None
    api_token: str | None = None
    dry_run: bool = True

    def safe_labels(self, environment: str | None = None) -> list[str]:
        """Return the base labels plus an environment label and severity label."""
        labels = list(self.labels)
        if environment:
            labels.append(f"environment-{environment.lower()}")
        return labels


@dataclass(frozen=True)
class HttpRetryConfig:
    """Retry policy for outbound HTTP requests."""

    max_retries: int = 3
    initial_backoff_seconds: float = 0.5
    max_backoff_seconds: float = 10.0
    timeout_seconds: float = 10.0
    # Status codes that should be retried despite being 4xx.
    retryable_4xx: tuple[int, ...] = (408, 429)
    # 5xx status codes that are retryable.
    retryable_5xx: tuple[int, ...] = (500, 502, 503, 504)

    def is_retryable(self, status_code: int) -> bool:
        """Return True if a response status code warrants a retry."""
        return status_code in self.retryable_4xx or status_code in self.retryable_5xx


@dataclass
class AppConfig:
    """Top-level application configuration."""

    environment: str = "dev"
    project_name: str = "guardduty-incident-response"
    jira: JiraConfig = field(default_factory=JiraConfig)
    http: HttpRetryConfig = field(default_factory=HttpRetryConfig)
    extras: dict[str, Any] = field(default_factory=dict)
