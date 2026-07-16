"""Mock Jira issue creation for the local emulator."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from incident_response.config import JiraConfig
from incident_response.jira import build_issue_payload, deduplication_key
from incident_response.models import Finding


@dataclass
class MockJiraStore:
    """In-memory store of created mock issues with dedup support."""

    project_key: str = "SEC"
    next_id: int = 10001
    issues: dict[str, dict[str, Any]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)


class MockJira:
    """Builds realistic Jira Cloud REST API v3 responses without a network call."""

    def __init__(
        self, store: MockJiraStore | None = None, base_url: str = "https://example.atlassian.net"
    ) -> None:
        self.store = store or MockJiraStore()
        self.base_url = base_url.rstrip("/")

    def create_or_update(
        self, finding: Finding, config: JiraConfig, environment: str | None = None
    ) -> dict[str, Any]:
        """Create a mock issue or update an existing one for a duplicate finding."""
        with self.store._lock:
            key = deduplication_key(finding)
            payload = build_issue_payload(finding, config, environment=environment)
            if key in self.store.issues:
                existing = self.store.issues[key]
                occurrence = int(existing.get("occurrence_count", 1)) + 1
                existing["occurrence_count"] = occurrence
                existing["last_seen"] = finding.last_seen
                existing["mock"] = True
                existing["duplicate"] = True
                return existing

            issue_id = str(self.store.next_id)
            self.store.next_id += 1
            issue_key = f"{self.store.project_key}-{self.store.next_id - 10000}"
            response = {
                "id": issue_id,
                "key": issue_key,
                "self": f"{self.base_url}/rest/api/3/issue/{issue_id}",
                "fields": payload["fields"],
                "occurrence_count": 1,
                "deduplication_key": key,
                "mock": True,
                "duplicate": False,
            }
            self.store.issues[key] = response
            return response
