"""Custom exceptions for the incident-response automation package."""

from __future__ import annotations


class IncidentResponseError(Exception):
    """Base class for all errors raised by this package."""


class ValidationError(IncidentResponseError):
    """Raised when a GuardDuty event fails structural validation."""


class NormalizationError(IncidentResponseError):
    """Raised when a validated event cannot be normalized."""


class JiraPayloadError(IncidentResponseError):
    """Raised when a Jira issue payload cannot be constructed."""


class HttpClientError(IncidentResponseError):
    """Base class for HTTP client errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class HttpTimeoutError(HttpClientError):
    """Raised when an HTTP request times out."""


class HttpPermanentError(HttpClientError):
    """Raised for permanent HTTP failures (non-retryable)."""


class HttpTransientError(HttpClientError):
    """Raised for transient HTTP failures (retryable)."""
