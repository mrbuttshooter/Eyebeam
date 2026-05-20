"""Helpers for selecting SIP-facing local addresses."""
from __future__ import annotations

from dataclasses import dataclass
import socket

from noc_beam.config.store import AccountConfig


@dataclass(frozen=True)
class SipTarget:
    scheme: str
    host: str
    port: int
    transport: str


def parse_sip_target(value: str, default_transport: str = "udp") -> SipTarget:
    """Parse the host/port/transport portion of a SIP route target.

    Accepts full SIP URIs, bare host[:port], and route-set values such as
    ``<sip:proxy.example.com;lr>``. It intentionally ignores userinfo and
    route params because route selection only needs the next-hop socket.
    """
    target = (value or "").strip()
    if not target:
        raise ValueError("SIP target is empty")
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()

    if ":" in target and target.split(":", 1)[0].lower() in {"sip", "sips"}:
        scheme, rest = target.split(":", 1)
        scheme = scheme.lower()
    else:
        scheme = "sip"
        rest = target

    main, _, params = rest.partition(";")
    main = main.split("?", 1)[0]
    hostport = main.rsplit("@", 1)[-1].strip()
    if not hostport:
        raise ValueError("SIP target host is empty")

    default_port = 5061 if scheme == "sips" else 5060
    if hostport.startswith("["):
        end = hostport.find("]")
        if end < 0:
            raise ValueError("Invalid IPv6 SIP target")
        host = hostport[1:end]
        tail = hostport[end + 1:]
        port = int(tail[1:]) if tail.startswith(":") else default_port
    elif ":" in hostport:
        host, port_text = hostport.rsplit(":", 1)
        port = int(port_text)
    else:
        host = hostport
        port = default_port

    transport = "tls" if scheme == "sips" else (default_transport or "udp").lower()
    for param in params.split(";"):
        key, _, param_value = param.partition("=")
        if key.strip().lower() == "transport" and param_value:
            transport = param_value.strip().lower()
            break
    return SipTarget(scheme=scheme, host=host, port=port, transport=transport)


def route_target_for_account(cfg: AccountConfig) -> str:
    proxy = (getattr(cfg, "proxy", "") or "").strip()
    if proxy:
        return proxy
    host = (getattr(cfg, "domain", "") or "").strip()
    port = int(getattr(cfg, "port", 0) or 0)
    if port and host and not (host.endswith(f":{port}") or "]" in host):
        return f"{host}:{port}"
    return host


def effective_transport_for_account(cfg: AccountConfig) -> str:
    transport = (getattr(cfg, "transport", "") or "udp").lower()
    if (getattr(cfg, "switch_type", "") or "").lower() == "teles" and transport == "udp":
        return "tcp"
    return transport


def local_address_for_sip_target(value: str, default_transport: str = "udp") -> str:
    """Return the local IP Windows would use to reach a SIP next hop."""
    target = parse_sip_target(value, default_transport=default_transport)
    family = socket.AF_INET6 if ":" in target.host and not target.host.count(".") else socket.AF_INET
    # UDP connect only asks the kernel to select a route/local address; it
    # does not send a packet and works even when the peer would reject TCP.
    with socket.socket(family, socket.SOCK_DGRAM) as sock:
        sock.settimeout(0.5)
        sock.connect((target.host, target.port))
        return str(sock.getsockname()[0])


def local_address_for_account(cfg: AccountConfig) -> str:
    return local_address_for_sip_target(
        route_target_for_account(cfg),
        default_transport=effective_transport_for_account(cfg),
    )
