from __future__ import annotations

from noc_beam.config.store import AccountConfig
from noc_beam.sip.netselect import (
    effective_transport_for_account,
    parse_sip_target,
    route_target_for_account,
)


def test_parse_sip_target_accepts_bare_host() -> None:
    target = parse_sip_target("208.87.170.99")

    assert target.host == "208.87.170.99"
    assert target.port == 5060
    assert target.transport == "udp"


def test_parse_sip_target_uses_proxy_uri_host_port_and_transport() -> None:
    target = parse_sip_target("<sip:alice@proxy.example.test:5070;transport=tcp;lr>")

    assert target.host == "proxy.example.test"
    assert target.port == 5070
    assert target.transport == "tcp"


def test_route_target_prefers_proxy_over_registrar() -> None:
    cfg = AccountConfig(
        id="a",
        domain="208.87.170.99",
        proxy="sip:208.87.169.100;lr",
        port=5090,
    )

    assert route_target_for_account(cfg) == "sip:208.87.169.100;lr"


def test_route_target_appends_account_port_without_proxy() -> None:
    cfg = AccountConfig(id="a", domain="sip.example.test", port=5070)

    assert route_target_for_account(cfg) == "sip.example.test:5070"


def test_teles_accounts_default_to_tcp_transport() -> None:
    cfg = AccountConfig(id="a", switch_type="teles", transport="udp")

    assert effective_transport_for_account(cfg) == "tcp"


def test_teles_accounts_preserve_explicit_tls_transport() -> None:
    cfg = AccountConfig(id="a", switch_type="teles", transport="tls")

    assert effective_transport_for_account(cfg) == "tls"
