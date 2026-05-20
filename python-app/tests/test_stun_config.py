from __future__ import annotations

import pytest

from noc_beam.config.store import AccountConfig, GlobalSettings
from noc_beam.sip import endpoint as endpoint_module
from noc_beam.sip.endpoint import SipEndpoint, collect_stun_servers


def test_collect_stun_servers_strips_dedupes_and_skips_disabled() -> None:
    accounts = [
        AccountConfig(id="a", stun_server=" stun1.example.com "),
        AccountConfig(id="b", stun_server=""),
        AccountConfig(id="c", stun_server="stun2.example.com"),
        AccountConfig(id="d", stun_server="stun1.example.com"),
        AccountConfig(id="e", stun_server="stun3.example.com", enabled=False),
    ]

    assert collect_stun_servers(accounts) == [
        "stun1.example.com",
        "stun2.example.com",
    ]


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
        self.writer = None


class _FakeMedConfig:
    def __init__(self) -> None:
        self.clockRate = 0
        self.ecTailLen = 0


class _FakeEpConfig:
    def __init__(self) -> None:
        self.uaConfig = _FakeUaConfig()
        self.logConfig = _FakeLogConfig()
        self.medConfig = _FakeMedConfig()


class _FakeTransportConfig:
    def __init__(self) -> None:
        self.port = 0


class _FakeVersion:
    full = "2.14.1-test"


class _FakeCodec:
    codecId = "PCMU/8000/1"
    priority = 128


class _FakeEndpoint:
    last_config: _FakeEpConfig | None = None

    def libCreate(self) -> None:
        pass

    def libInit(self, cfg: _FakeEpConfig) -> None:
        type(self).last_config = cfg

    def transportCreate(self, _transport_type: int, _cfg: _FakeTransportConfig) -> int:
        return 1

    def codecEnum2(self) -> list[_FakeCodec]:
        return [_FakeCodec()]

    def codecSetPriority(self, _codec_id: str, _priority: int) -> None:
        pass

    def libStart(self) -> None:
        pass

    def libVersion(self) -> _FakeVersion:
        return _FakeVersion()

    def libDestroy(self) -> None:
        pass


def test_endpoint_start_appends_account_stun_servers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(endpoint_module, "PJSUA2_AVAILABLE", True)
    monkeypatch.setattr(
        endpoint_module,
        "pj",
        type(
            "FakePj",
            (),
            {
                "Endpoint": _FakeEndpoint,
                "EpConfig": _FakeEpConfig,
                "TransportConfig": _FakeTransportConfig,
                "PJSIP_TRANSPORT_UDP": 1,
                "PJSIP_TRANSPORT_TCP": 2,
                "PJSIP_TRANSPORT_TLS": 3,
            },
        ),
    )
    _FakeEndpoint.last_config = None

    endpoint = SipEndpoint()
    endpoint.start(
        GlobalSettings(),
        accounts=[
            AccountConfig(id="a", stun_server="stun1.example.com"),
            AccountConfig(id="b", stun_server=" stun2.example.com "),
            AccountConfig(id="c", stun_server="stun1.example.com"),
        ],
    )

    assert _FakeEndpoint.last_config is not None
    assert list(_FakeEndpoint.last_config.uaConfig.stunServer) == [
        "stun1.example.com",
        "stun2.example.com",
    ]
    assert _FakeEndpoint.last_config.uaConfig.stunIgnoreFailure is True


def test_sip_advertised_address_uses_first_enabled_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        endpoint_module,
        "local_address_for_account",
        lambda _cfg: "10.35.150.184",
    )

    assert SipEndpoint._sip_advertised_address(
        [
            AccountConfig(id="disabled", enabled=False, domain="10.0.0.1"),
            AccountConfig(id="enabled", domain="208.87.170.99"),
        ]
    ) == "10.35.150.184"


def test_apply_transport_advertised_address_sets_public_address() -> None:
    class FakeTransportConfig:
        publicAddress = ""

    tcfg = FakeTransportConfig()

    SipEndpoint._apply_transport_advertised_address(tcfg, "10.35.150.184")

    assert tcfg.publicAddress == "10.35.150.184"
