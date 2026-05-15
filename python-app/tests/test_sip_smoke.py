from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from noc_beam import __main__
from noc_beam.sip import _pjsua2_loader, smoke


class _Version:
    full = "2.14.1-test"


class _FakeEndpoint:
    def __init__(self) -> None:
        self.created = False

    def libCreate(self) -> None:
        self.created = True

    def libVersion(self) -> _Version:
        return _Version()

    def libDestroy(self) -> None:
        if not self.created:
            raise RuntimeError("destroy before create")


class _FailingEndpoint:
    def libCreate(self) -> None:
        raise RuntimeError("boom")

    def libDestroy(self) -> None:
        pass


def test_sip_smoke_fails_when_native_required_but_stub_loaded(monkeypatch) -> None:
    monkeypatch.setattr(_pjsua2_loader, "PJSUA2_SOURCE", "stub")
    monkeypatch.setattr(_pjsua2_loader, "PJSUA2_AVAILABLE", False)
    monkeypatch.setattr(_pjsua2_loader, "PJSUA2_LOAD_ERROR", "native missing")

    exit_code, report = smoke.run_sip_smoke(require_native=True)

    assert exit_code == 1
    assert report["ok"] is False
    assert report["source"] == "stub"
    assert "Expected bundled native pjsua2" in report["errors"][0]
    assert "native missing" in report["errors"]


def test_sip_smoke_succeeds_with_native_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(_pjsua2_loader, "PJSUA2_SOURCE", "native")
    monkeypatch.setattr(_pjsua2_loader, "PJSUA2_AVAILABLE", True)
    monkeypatch.setattr(_pjsua2_loader, "PJSUA2_LOAD_ERROR", "")
    monkeypatch.setattr(_pjsua2_loader, "pj", SimpleNamespace(Endpoint=_FakeEndpoint))

    exit_code, report = smoke.run_sip_smoke(require_native=True)

    assert exit_code == 0
    assert report["ok"] is True
    assert report["endpoint_created"] is True
    assert report["endpoint_destroyed"] is True
    assert report["pjsip_version"] == "2.14.1-test"
    assert report["errors"] == []


def test_sip_smoke_records_endpoint_create_failure(monkeypatch) -> None:
    monkeypatch.setattr(_pjsua2_loader, "PJSUA2_SOURCE", "native")
    monkeypatch.setattr(_pjsua2_loader, "PJSUA2_AVAILABLE", True)
    monkeypatch.setattr(_pjsua2_loader, "PJSUA2_LOAD_ERROR", "")
    monkeypatch.setattr(_pjsua2_loader, "pj", SimpleNamespace(Endpoint=_FailingEndpoint))

    exit_code, report = smoke.run_sip_smoke(require_native=True)

    assert exit_code == 1
    assert report["ok"] is False
    assert report["endpoint_created"] is False
    assert report["endpoint_destroyed"] is True
    assert report["errors"] == ["Endpoint create failed: boom"]


def test_write_smoke_report_writes_json(tmp_path: Path) -> None:
    path = tmp_path / "sip-smoke.json"
    smoke.write_smoke_report(path, {"ok": True, "source": "native"})

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "ok": True,
        "source": "native",
    }


def test_main_sip_smoke_routes_before_gui_start(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "sip-smoke.json"

    def fake_run_sip_smoke(*, require_native: bool) -> tuple[int, dict[str, object]]:
        assert require_native is True
        return 0, {"ok": True, "source": "native"}

    monkeypatch.setattr(smoke, "run_sip_smoke", fake_run_sip_smoke)

    exit_code = __main__.main(
        ["NOC_Beam.exe", "--sip-smoke", "--sip-smoke-output", str(output)]
    )

    assert exit_code == 0
    assert json.loads(output.read_text(encoding="utf-8")) == {
        "ok": True,
        "source": "native",
    }
