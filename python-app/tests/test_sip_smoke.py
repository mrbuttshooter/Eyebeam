from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from noc_beam import __main__
from noc_beam.sip import _pjsua2_loader, smoke


class _Version:
    full = "2.14.1-test"


class _FakeVector(list):
    def append(self, value):  # noqa: ANN001
        super().append(value)


class _FakeUaConfig:
    def __init__(self) -> None:
        self.userAgent = ""
        self.maxCalls = 0
        self.stunServer = _FakeVector()
        self.stunIgnoreFailure = False


class _FakeLogConfig:
    def __init__(self) -> None:
        self.level = 0
        self.consoleLevel = 0


class _FakeMedConfig:
    def __init__(self) -> None:
        self.clockRate = 0


class _FakeEpConfig:
    def __init__(self) -> None:
        self.uaConfig = _FakeUaConfig()
        self.logConfig = _FakeLogConfig()
        self.medConfig = _FakeMedConfig()


class _FakeTransportConfig:
    def __init__(self) -> None:
        self.port = -1


class _FakeCodec:
    def __init__(self, codec_id: str, priority: int = 128) -> None:
        self.codecId = codec_id
        self.priority = priority


class _FakeEndpoint:
    last_config: _FakeEpConfig | None = None
    codec_ids = ["PCMU/8000/1", "G729/8000/1", "opus/48000/2"]

    def __init__(self) -> None:
        self.created = False
        self.initialized = False
        self.started = False
        self.destroyed = False
        self.transports: list[int] = []

    def libCreate(self) -> None:
        self.created = True

    def libInit(self, cfg: _FakeEpConfig) -> None:
        self.initialized = True
        type(self).last_config = cfg

    def transportCreate(self, transport_type: int, cfg: _FakeTransportConfig) -> int:
        assert cfg.port == 0
        self.transports.append(transport_type)
        return 100 + transport_type

    def codecEnum2(self) -> list[_FakeCodec]:
        return [_FakeCodec(codec_id) for codec_id in self.codec_ids]

    def libStart(self) -> None:
        self.started = True

    def libVersion(self) -> _Version:
        return _Version()

    def libDestroy(self) -> None:
        if not self.created:
            raise RuntimeError("destroy before create")
        self.destroyed = True


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
    _FakeEndpoint.last_config = None
    _FakeEndpoint.codec_ids = ["PCMU/8000/1", "G729/8000/1", "opus/48000/2"]
    monkeypatch.setattr(
        _pjsua2_loader,
        "pj",
        SimpleNamespace(
            Endpoint=_FakeEndpoint,
            EpConfig=_FakeEpConfig,
            TransportConfig=_FakeTransportConfig,
            PJSIP_TRANSPORT_UDP=1,
            PJSIP_TRANSPORT_TCP=2,
            PJSIP_TRANSPORT_TLS=3,
        ),
    )

    exit_code, report = smoke.run_sip_smoke(
        require_native=True,
        stun_servers=["stun.example.com"],
    )

    assert exit_code == 0
    assert report["ok"] is True
    assert report["endpoint_created"] is True
    assert report["endpoint_destroyed"] is True
    assert report["lib_initialized"] is True
    assert report["lib_started"] is True
    assert report["pjsip_version"] == "2.14.1-test"
    assert report["transports"]["udp"]["ok"] is True
    assert report["transports"]["tcp"]["ok"] is True
    assert report["transports"]["tls"]["ok"] is True
    assert report["required_codecs"]["g729"] is True
    assert report["required_codecs"]["opus"] is True
    assert report["stun_servers"] == ["stun.example.com"]
    assert _FakeEndpoint.last_config is not None
    assert list(_FakeEndpoint.last_config.uaConfig.stunServer) == ["stun.example.com"]
    assert report["errors"] == []


def test_sip_smoke_records_endpoint_create_failure(monkeypatch) -> None:
    monkeypatch.setattr(_pjsua2_loader, "PJSUA2_SOURCE", "native")
    monkeypatch.setattr(_pjsua2_loader, "PJSUA2_AVAILABLE", True)
    monkeypatch.setattr(_pjsua2_loader, "PJSUA2_LOAD_ERROR", "")
    monkeypatch.setattr(
        _pjsua2_loader,
        "pj",
        SimpleNamespace(
            Endpoint=_FailingEndpoint,
            EpConfig=_FakeEpConfig,
            TransportConfig=_FakeTransportConfig,
            PJSIP_TRANSPORT_UDP=1,
            PJSIP_TRANSPORT_TCP=2,
            PJSIP_TRANSPORT_TLS=3,
        ),
    )

    exit_code, report = smoke.run_sip_smoke(require_native=True)

    assert exit_code == 1
    assert report["ok"] is False
    assert report["endpoint_created"] is False
    assert report["endpoint_destroyed"] is True
    assert report["errors"] == ["Endpoint create failed: boom"]


def test_sip_smoke_fails_when_required_native_codecs_are_missing(monkeypatch) -> None:
    monkeypatch.setattr(_pjsua2_loader, "PJSUA2_SOURCE", "native")
    monkeypatch.setattr(_pjsua2_loader, "PJSUA2_AVAILABLE", True)
    monkeypatch.setattr(_pjsua2_loader, "PJSUA2_LOAD_ERROR", "")
    _FakeEndpoint.codec_ids = ["PCMU/8000/1"]
    monkeypatch.setattr(
        _pjsua2_loader,
        "pj",
        SimpleNamespace(
            Endpoint=_FakeEndpoint,
            EpConfig=_FakeEpConfig,
            TransportConfig=_FakeTransportConfig,
            PJSIP_TRANSPORT_UDP=1,
            PJSIP_TRANSPORT_TCP=2,
            PJSIP_TRANSPORT_TLS=3,
        ),
    )

    exit_code, report = smoke.run_sip_smoke(require_native=True)

    assert exit_code == 1
    assert report["ok"] is False
    assert report["required_codecs"]["g729"] is False
    assert report["required_codecs"]["opus"] is False
    assert "Missing required native codec: g729" in report["errors"]
    assert "Missing required native codec: opus" in report["errors"]


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
