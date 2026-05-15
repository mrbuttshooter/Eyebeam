from __future__ import annotations

import socket
import threading

import pytest

pytest.importorskip("PySide6.QtCore")

from noc_beam.sip.endpoint import SipEndpoint  # noqa: E402


def test_parse_probe_uri_defaults_to_udp_5060() -> None:
    assert SipEndpoint._parse_probe_uri("sip:proxy.example.com") == (
        "sip",
        "proxy.example.com",
        5060,
        "udp",
    )


def test_parse_probe_uri_honors_transport_and_port() -> None:
    assert SipEndpoint._parse_probe_uri("sip:alice@proxy.example.com:5070;transport=tcp") == (
        "sip",
        "proxy.example.com",
        5070,
        "tcp",
    )


def test_parse_probe_uri_sips_defaults_to_tls_5061() -> None:
    assert SipEndpoint._parse_probe_uri("sips:proxy.example.com") == (
        "sips",
        "proxy.example.com",
        5061,
        "tls",
    )


def test_options_probe_udp_success() -> None:
    received: list[bytes] = []

    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(("127.0.0.1", 0))
    host, port = server.getsockname()

    def worker() -> None:
        try:
            data, peer = server.recvfrom(8192)
            received.append(data)
            server.sendto(
                b"SIP/2.0 200 OK\r\n"
                b"Via: SIP/2.0/UDP 127.0.0.1;branch=z9hG4bK-test\r\n"
                b"Content-Length: 0\r\n\r\n",
                peer,
            )
        finally:
            server.close()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    code, reason, rtt_ms = SipEndpoint().options_probe(f"sip:{host}:{port}", timeout_s=1.0)
    thread.join(timeout=1.0)

    assert code == 200
    assert reason == "OK"
    assert rtt_ms >= 0
    assert received
    assert received[0].startswith(f"OPTIONS sip:{host}:{port} SIP/2.0".encode("ascii"))


def test_options_probe_udp_timeout_returns_408() -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(("127.0.0.1", 0))
    host, port = server.getsockname()

    try:
        code, reason, _rtt_ms = SipEndpoint().options_probe(f"sip:{host}:{port}", timeout_s=0.05)
    finally:
        server.close()

    assert code == 408
    assert reason == "Request Timeout"


def test_parse_options_response_rejects_empty_response() -> None:
    with pytest.raises(RuntimeError, match="Empty SIP response"):
        SipEndpoint._parse_options_response(b"")
