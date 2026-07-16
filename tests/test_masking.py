"""Tests for secret masking and structured logging."""

from __future__ import annotations

import json

from incident_response.logging_config import JsonFormatter, get_logger
from incident_response.masking import (
    MASKED,
    mask_secrets,
    mask_url,
    scrub_secrets_from_text,
)


def test_mask_nested_dict():
    data = {"a": {"api_token": "supersecret", "ok": "visible"}, "b": 1}
    out = mask_secrets(data)
    assert out["a"]["api_token"] == MASKED
    assert out["a"]["ok"] == "visible"
    assert out["b"] == 1


def test_mask_list_of_dicts():
    data = [{"authorization": "Bearer xyz"}, {"token": "t"}, {"safe": "s"}]
    out = mask_secrets(data)
    assert out[0]["authorization"] == MASKED
    assert out[1]["token"] == MASKED
    assert out[2]["safe"] == "s"


def test_mask_authorization_header():
    data = {"headers": {"Authorization": "Bearer SECRET", "Content-Type": "application/json"}}
    out = mask_secrets(data)
    assert out["headers"]["Authorization"] == MASKED
    assert out["headers"]["Content-Type"] == "application/json"


def test_mask_all_sensitive_keys():
    keys = [
        "authorization",
        "api_token",
        "jira_api_token",
        "token",
        "password",
        "secret",
        "shared_secret",
        "webhook_url",
        "cookie",
        "x-api-key",
    ]
    for k in keys:
        out = mask_secrets({k: "v"})
        assert out[k] == MASKED, f"key {k} not masked"


def test_mask_url_hides_credentials_and_path():
    assert (
        mask_url("https://user:pass@example.com/secret/path?token=abc") == "https://example.com/***"
    )
    assert mask_url("https://example.com/webhook/abc-secret-token") == "https://example.com/***"


def test_mask_url_none_and_empty():
    assert mask_url(None) == "N/A"
    assert mask_url("") == "N/A"


def test_scrub_secrets_from_text():
    text = "error calling https://hook.example/abc with token=abc"
    out = scrub_secrets_from_text(text, secrets=["abc"])
    assert "abc" not in out
    assert MASKED in out


def test_json_log_structure_no_token_leak():
    import logging as _logging

    record = _logging.LogRecord(
        name="incident_response",
        level=_logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="test",
        args=None,
        exc_info=None,
    )
    record.authorization = "Bearer LEAK"
    record.data = {"api_token": "LEAK"}
    formatter = JsonFormatter()
    line = formatter.format(record)
    parsed = json.loads(line)
    assert parsed["msg"] == "test"
    assert "LEAK" not in line
    assert parsed["authorization"] == MASKED
    assert parsed["data"]["api_token"] == MASKED


def test_get_logger_child_name():
    log = get_logger("child")
    assert log.name == "incident_response.child"
