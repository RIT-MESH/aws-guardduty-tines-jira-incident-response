"""Shared pytest fixtures for the incident-response test suite."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def load_example(name: str) -> dict[str, Any]:
    """Load a sanitized example event from examples/."""
    with (EXAMPLES_DIR / name).open("r", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture
def examples_dir() -> Path:
    return EXAMPLES_DIR


@pytest.fixture
def high_severity_event() -> dict[str, Any]:
    return load_example("guardduty-high-severity.json")


@pytest.fixture
def medium_severity_event() -> dict[str, Any]:
    return load_example("guardduty-medium-severity.json")


@pytest.fixture
def low_severity_event() -> dict[str, Any]:
    return load_example("guardduty-low-severity.json")


@pytest.fixture
def critical_severity_event() -> dict[str, Any]:
    return load_example("guardduty-critical-severity.json")


@pytest.fixture
def missing_optional_event() -> dict[str, Any]:
    return load_example("guardduty-missing-optional-fields.json")


@pytest.fixture
def malformed_event() -> dict[str, Any]:
    return load_example("guardduty-malformed.json")


@pytest.fixture
def s3_event() -> dict[str, Any]:
    return load_example("guardduty-s3.json")


@pytest.fixture
def kubernetes_event() -> dict[str, Any]:
    return load_example("guardduty-kubernetes.json")


@pytest.fixture
def malware_event() -> dict[str, Any]:
    return load_example("guardduty-malware.json")


@pytest.fixture
def iam_event() -> dict[str, Any]:
    return load_example("guardduty-iam-unauthorized-access.json")


@pytest.fixture
def recon_event() -> dict[str, Any]:
    return load_example("guardduty-ec2-recon.json")


@pytest.fixture
def crypto_event() -> dict[str, Any]:
    return load_example("guardduty-ec2-cryptocurrency.json")


@pytest.fixture
def event_factory() -> Any:
    """Return a callable that loads and deep-copies an example by name."""

    def _make(name: str) -> dict[str, Any]:
        return copy.deepcopy(load_example(name))

    return _make


def make_event(detail: dict[str, Any]) -> dict[str, Any]:
    """Build a minimal valid EventBridge envelope around a detail dict."""
    return {
        "version": "0",
        "id": "test-envelope",
        "detail-type": "GuardDuty Finding",
        "source": "aws.guardduty",
        "account": "111122223333",
        "region": "us-east-1",
        "time": "2026-07-17T12:00:00Z",
        "resources": [],
        "detail": detail,
    }


@pytest.fixture
def make_envelope() -> Any:
    return make_event
