"""Tests for the Lambda forwarder handler."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from incident_response.exceptions import HttpPermanentError, HttpTransientError
from lambda_forwarder import handler as handler_mod
from lambda_forwarder import lambda_handler
from lambda_forwarder.config import LambdaConfig


class FakeHttpClient:
    def __init__(self, response=None, exc=None):
        self.response = response or {"status_code": 200, "ok": True}
        self.exc = exc
        self.calls = []

    def post_json(self, url, payload, headers=None, timeout=None):
        self.calls.append({"url": url, "payload": payload, "headers": headers})
        if self.exc:
            raise self.exc
        return self.response


def _ctx(request_id="req-123"):
    return SimpleNamespace(aws_request_id=request_id)


def _config(webhook="https://tines.example/webhook", min_sev=0.0):
    return LambdaConfig(
        tines_webhook_url=webhook,
        tines_shared_secret="shared",
        min_severity_score=min_sev,
    )


def test_lambda_success(monkeypatch, high_severity_event):
    fake = FakeHttpClient()
    monkeypatch.setattr(handler_mod, "HttpClient", lambda config=None: fake)
    result = lambda_handler(high_severity_event, _ctx(), config=_config())
    assert result["status"] == "forwarded"
    assert result["severity"] == "High"
    assert result["response"]["ok"] is True
    assert fake.calls[0]["headers"]["X-Tines-Shared-Secret"] == "shared"
    assert fake.calls[0]["payload"]["finding"]["id"]


def test_lambda_request_id_in_payload(monkeypatch, high_severity_event):
    fake = FakeHttpClient()
    monkeypatch.setattr(handler_mod, "HttpClient", lambda config=None: fake)
    lambda_handler(high_severity_event, _ctx("rid-999"), config=_config())
    assert fake.calls[0]["payload"]["automation"]["request_id"] == "rid-999"


def test_lambda_invalid_event(monkeypatch, malformed_event):
    fake = FakeHttpClient()
    monkeypatch.setattr(handler_mod, "HttpClient", lambda config=None: fake)
    result = lambda_handler(malformed_event, _ctx(), config=_config())
    assert result["status"] == "rejected"
    assert result["reason"] == "validation_failed"
    assert fake.calls == []


def test_lambda_missing_webhook_config(monkeypatch, high_severity_event):
    fake = FakeHttpClient()
    monkeypatch.setattr(handler_mod, "HttpClient", lambda config=None: fake)
    with pytest.raises(ValueError, match="TINES_WEBHOOK_URL"):
        lambda_handler(high_severity_event, _ctx(), config=LambdaConfig(tines_webhook_url=""))


def test_lambda_forwarding_failure(monkeypatch, high_severity_event):
    fake = FakeHttpClient(exc=HttpPermanentError("HTTP 403", status_code=403))
    monkeypatch.setattr(handler_mod, "HttpClient", lambda config=None: fake)
    with pytest.raises(HttpPermanentError):
        lambda_handler(high_severity_event, _ctx(), config=_config())


def test_lambda_transient_failure(monkeypatch, high_severity_event):
    fake = FakeHttpClient(exc=HttpTransientError("HTTP 500", status_code=500))
    monkeypatch.setattr(handler_mod, "HttpClient", lambda config=None: fake)
    with pytest.raises(HttpTransientError):
        lambda_handler(high_severity_event, _ctx(), config=_config())


def test_lambda_severity_filter(monkeypatch, low_severity_event):
    fake = FakeHttpClient()
    monkeypatch.setattr(handler_mod, "HttpClient", lambda config=None: fake)
    result = lambda_handler(low_severity_event, _ctx(), config=_config(min_sev=5.0))
    assert result["status"] == "filtered"
    assert fake.calls == []


def test_lambda_config_from_env_uses_runtime_env(monkeypatch):
    monkeypatch.setenv("TINES_WEBHOOK_URL", "https://runtime.example/webhook")
    monkeypatch.setenv("TINES_MAX_RETRIES", "5")
    cfg = LambdaConfig.from_env()
    assert cfg.tines_webhook_url == "https://runtime.example/webhook"
    assert cfg.max_retries == 5
