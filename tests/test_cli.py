"""Tests for the simulate_finding CLI."""

from __future__ import annotations

import json

from tools import simulate_finding


def test_dry_run_default(high_severity_event, tmp_path, capsys):
    p = tmp_path / "ev.json"
    p.write_text(json.dumps(high_severity_event), encoding="utf-8")
    rc = simulate_finding.main(["--input", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "JIRA PAYLOAD" in out
    assert "DRY RUN: nothing was sent" in out


def test_send_requires_webhook_url(high_severity_event, tmp_path, capsys):
    p = tmp_path / "ev.json"
    p.write_text(json.dumps(high_severity_event), encoding="utf-8")
    rc = simulate_finding.main(["--input", str(p), "--send"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "webhook" in err.lower()


def test_invalid_json(tmp_path, capsys):
    p = tmp_path / "bad.json"
    p.write_text("{not valid json", encoding="utf-8")
    rc = simulate_finding.main(["--input", str(p)])
    assert rc == 1


def test_malformed_guardduty_event(malformed_event, tmp_path, capsys):
    p = tmp_path / "malformed.json"
    p.write_text(json.dumps(malformed_event), encoding="utf-8")
    rc = simulate_finding.main(["--input", str(p)])
    assert rc == 1


def test_no_accidental_transmission(high_severity_event, tmp_path, monkeypatch, capsys):
    called = {"n": 0}

    def boom(*args, **kwargs):
        called["n"] += 1
        raise AssertionError("HttpClient should not be called in dry-run")

    monkeypatch.setattr(
        simulate_finding, "HttpClient", lambda *a, **k: type("X", (), {"post_json": boom})()
    )
    p = tmp_path / "ev.json"
    p.write_text(json.dumps(high_severity_event), encoding="utf-8")
    rc = simulate_finding.main(["--input", str(p)])
    assert rc == 0
    assert called["n"] == 0


def test_missing_input_file_returns_error(tmp_path, capsys):
    rc = simulate_finding.main(["--input", str(tmp_path / "nope.json")])
    assert rc == 1


def test_accepts_jira_options(high_severity_event, tmp_path, capsys):
    p = tmp_path / "ev.json"
    p.write_text(json.dumps(high_severity_event), encoding="utf-8")
    rc = simulate_finding.main(
        [
            "--input",
            str(p),
            "--jira-project",
            "SECOPS",
            "--jira-issue-type",
            "Security Incident",
            "--environment",
            "prod",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "SECOPS" in out
    assert "Security Incident" in out
    assert "environment-prod" in out
