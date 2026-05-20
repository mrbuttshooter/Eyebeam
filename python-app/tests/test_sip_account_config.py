from __future__ import annotations

from noc_beam.sip.account import _contact_uri_params_for_transport, _normalize_proxy_uri


def test_normalize_proxy_uri_ignores_blank_proxy() -> None:
    assert _normalize_proxy_uri("", "sip") == ""
    assert _normalize_proxy_uri("   ", "sip") == ""


def test_normalize_proxy_uri_keeps_explicit_sip_scheme() -> None:
    assert _normalize_proxy_uri(" sip:208.87.170.99 ", "sip") == "sip:208.87.170.99"
    assert _normalize_proxy_uri("sips:proxy.example.net", "sip") == "sips:proxy.example.net"


def test_normalize_proxy_uri_accepts_bare_host_for_pjsip_route() -> None:
    assert _normalize_proxy_uri("208.87.170.99", "sip") == "sip:208.87.170.99"
    assert _normalize_proxy_uri("proxy.example.net:5080;transport=tcp", "sip") == (
        "sip:proxy.example.net:5080;transport=tcp"
    )


def test_contact_uri_params_for_tcp_matches_eyebeam_contact() -> None:
    assert _contact_uri_params_for_transport("udp") == ""
    assert _contact_uri_params_for_transport("tcp") == ";transport=TCP"
    assert _contact_uri_params_for_transport("tls") == ";transport=TLS"
