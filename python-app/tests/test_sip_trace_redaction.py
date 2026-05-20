from __future__ import annotations

from types import SimpleNamespace

from noc_beam.sip import trace


def test_redact_sip_body_masks_uri_userparts() -> None:
    body = (
        "INVITE sip:0096171488860@208.87.170.99 SIP/2.0\n"
        "From: <sip:U080@208.87.170.99>\n"
        "Contact: <sip:U080@10.35.150.193:53728;transport=TCP>\n"
    )

    redacted = trace.redact_sip_body(body)

    assert "sip:00***@208.87.170.99" in redacted
    assert "sip:U0***@208.87.170.99" in redacted
    assert "0096171488860@208.87.170.99" not in redacted
    assert "U080@208.87.170.99" not in redacted


def test_trace_redaction_can_be_disabled_from_settings(monkeypatch) -> None:
    settings = SimpleNamespace(
        compliance=SimpleNamespace(trace_pii_redaction=False)
    )
    monkeypatch.delenv("SIP_TRACE_DIAGNOSTIC", raising=False)
    monkeypatch.setattr(
        "noc_beam.config.store.load_settings",
        lambda: settings,
    )

    assert trace.trace_redaction_enabled() is False


def test_trace_diagnostic_env_disables_redaction(monkeypatch) -> None:
    monkeypatch.setenv("SIP_TRACE_DIAGNOSTIC", "1")

    assert trace.trace_redaction_enabled() is False
