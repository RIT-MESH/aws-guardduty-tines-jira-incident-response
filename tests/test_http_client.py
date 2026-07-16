"""Tests for the HTTP client retry/backoff behavior."""

from __future__ import annotations

import io
from email.message import Message
from typing import Any
from urllib.error import HTTPError, URLError

import pytest

from incident_response.config import HttpRetryConfig
from incident_response.exceptions import HttpPermanentError, HttpTransientError
from incident_response.http_client import HttpClient


class FakeResponse:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: Any) -> None:
        return None


def _http_error(code: int, retry_after: str | None = None) -> HTTPError:
    msg = Message()
    if retry_after is not None:
        msg["Retry-After"] = retry_after
    return HTTPError("https://example/webhook", code, "err", msg, io.BytesIO(b"{}"))


def make_client(responses: list[Any], sleeper=None) -> HttpClient:
    """Build a client whose opener pops from ``responses`` and records sleeps."""
    calls = {"opens": 0, "sleeps": []}

    def opener(req):
        calls["opens"] += 1
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def sleep(seconds: float) -> None:
        calls["sleeps"].append(seconds)

    cfg = HttpRetryConfig(
        max_retries=3,
        initial_backoff_seconds=0.01,
        max_backoff_seconds=0.05,
        timeout_seconds=2.0,
    )
    client = HttpClient(config=cfg, opener=opener, sleeper=sleeper or sleep)
    client._test_calls = calls  # type: ignore[attr-defined]
    return client


def test_http_success():
    client = make_client([FakeResponse(200, b'{"ok": true}')])
    out = client.post_json("https://example/webhook", {"x": 1})
    assert out["ok"] is True
    assert out["status_code"] == 200
    assert client._test_calls["opens"] == 1


def test_http_timeout_retry_then_success():
    client = make_client([URLError("timeout"), FakeResponse(200, b'{"ok": true}')])
    out = client.post_json("https://example/webhook", {})
    assert out["ok"] is True
    assert client._test_calls["opens"] == 2
    assert client._test_calls["sleeps"]


def test_http_408_retry_then_success():
    client = make_client([_http_error(408), FakeResponse(200, b"{}")])
    out = client.post_json("https://example/webhook", {})
    assert out["status_code"] == 200
    assert client._test_calls["opens"] == 2


def test_http_429_retry_after_then_success():
    client = make_client([_http_error(429, retry_after="0"), FakeResponse(200, b"{}")])
    out = client.post_json("https://example/webhook", {})
    assert out["status_code"] == 200
    # Retry-After value should be used as the backoff.
    assert client._test_calls["sleeps"][0] == 0.0


def test_http_500_retry_then_success():
    client = make_client([_http_error(500), FakeResponse(200, b"{}")])
    out = client.post_json("https://example/webhook", {})
    assert out["status_code"] == 200


def test_http_400_no_retry():
    client = make_client([_http_error(400)])
    with pytest.raises(HttpPermanentError) as exc:
        client.post_json("https://example/webhook", {})
    assert exc.value.status_code == 400
    assert client._test_calls["opens"] == 1


def test_http_retry_exhaustion():
    client = make_client([_http_error(500), _http_error(500), _http_error(500), _http_error(500)])
    with pytest.raises(HttpTransientError):
        client.post_json("https://example/webhook", {})
    # 1 initial + 3 retries = 4 attempts.
    assert client._test_calls["opens"] == 4


def test_http_timeout_error_type():
    client = make_client([TimeoutError("boom")])
    # All attempts timeout -> transient exhaustion.
    responses = [TimeoutError("boom")] * 4
    client = make_client(responses)
    with pytest.raises(HttpTransientError):
        client.post_json("https://example/webhook", {})


def test_http_error_message_is_secret_safe():
    client = make_client([_http_error(403)])
    with pytest.raises(HttpPermanentError) as exc:
        client.post_json("https://example/webhook/secret-token", {})
    assert "secret-token" not in str(exc.value)


def test_http_success_empty_body():
    client = make_client([FakeResponse(204, b"")])
    out = client.post_json("https://example/webhook", {})
    assert out["status_code"] == 204
