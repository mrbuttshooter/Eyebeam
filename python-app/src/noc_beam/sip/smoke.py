"""Packaged executable SIP smoke diagnostics."""
from __future__ import annotations

import json
from contextlib import suppress
from pathlib import Path
from typing import Any

from noc_beam.sip import _pjsua2_loader


def run_sip_smoke(
    *,
    require_native: bool = True,
    stun_servers: list[str] | None = None,
) -> tuple[int, dict[str, Any]]:
    """Start and stop a minimal PJSIP runtime, returning an exit code/report."""

    report: dict[str, Any] = {
        "ok": False,
        "source": _pjsua2_loader.PJSUA2_SOURCE,
        "available": _pjsua2_loader.PJSUA2_AVAILABLE,
        "native_required": require_native,
        "endpoint_created": False,
        "endpoint_destroyed": False,
        "lib_initialized": False,
        "lib_started": False,
        "pjsip_version": "",
        "transports": {},
        "codecs": [],
        "required_codecs": {"g729": False, "opus": False},
        "stun_servers": list(stun_servers or []),
        "errors": [],
    }
    errors = report["errors"]

    if require_native and _pjsua2_loader.PJSUA2_SOURCE != "native":
        errors.append(
            "Expected bundled native pjsua2, "
            f"loaded {_pjsua2_loader.PJSUA2_SOURCE!r} instead"
        )
        if _pjsua2_loader.PJSUA2_LOAD_ERROR:
            errors.append(_pjsua2_loader.PJSUA2_LOAD_ERROR)
        return 1, report

    if not _pjsua2_loader.PJSUA2_AVAILABLE:
        errors.append(_pjsua2_loader.PJSUA2_LOAD_ERROR or "pjsua2 is not available")
        return 1, report

    endpoint: Any | None = None
    try:
        endpoint = _pjsua2_loader.pj.Endpoint()
        endpoint.libCreate()
        report["endpoint_created"] = True
        report["pjsip_version"] = _read_version(endpoint)
    except Exception as exc:
        errors.append(f"Endpoint create failed: {exc}")
    else:
        try:
            _run_startup_checks(endpoint, report)
        except Exception as exc:
            errors.append(f"SIP startup failed: {exc}")
    finally:
        if endpoint is not None:
            try:
                endpoint.libDestroy()
                report["endpoint_destroyed"] = True
            except Exception as exc:
                errors.append(f"Endpoint destroy failed: {exc}")

    _validate_report(report)
    if (
        report["endpoint_created"]
        and report["endpoint_destroyed"]
        and report["lib_initialized"]
        and report["lib_started"]
        and not errors
    ):
        report["ok"] = True
        return 0, report
    return 1, report


def _run_startup_checks(endpoint: Any, report: dict[str, Any]) -> None:
    _init_endpoint(endpoint, report["stun_servers"])
    report["lib_initialized"] = True
    _create_transports(endpoint, report)
    _enumerate_codecs(endpoint, report)
    endpoint.libStart()
    report["lib_started"] = True


def write_smoke_report(path: str | Path, report: dict[str, Any]) -> None:
    Path(path).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _read_version(endpoint: Any) -> str:
    try:
        version = endpoint.libVersion()
    except Exception as exc:
        raise RuntimeError(f"Could not read PJSIP version: {exc}") from exc
    return str(getattr(version, "full", version))


def _init_endpoint(endpoint: Any, stun_servers: list[str]) -> None:
    ep_cfg = _pjsua2_loader.pj.EpConfig()
    ep_cfg.uaConfig.userAgent = "NOC_Beam sip-smoke"
    ep_cfg.uaConfig.maxCalls = 16
    for server in stun_servers:
        ep_cfg.uaConfig.stunServer.append(server)
    ep_cfg.uaConfig.stunIgnoreFailure = True
    with suppress(Exception):
        ep_cfg.logConfig.level = 3
        ep_cfg.logConfig.consoleLevel = 3
    with suppress(Exception):
        ep_cfg.medConfig.clockRate = 16000
    endpoint.libInit(ep_cfg)


def _create_transports(endpoint: Any, report: dict[str, Any]) -> None:
    for name, transport_type in (
        ("udp", _pjsua2_loader.pj.PJSIP_TRANSPORT_UDP),
        ("tcp", _pjsua2_loader.pj.PJSIP_TRANSPORT_TCP),
        ("tls", _pjsua2_loader.pj.PJSIP_TRANSPORT_TLS),
    ):
        cfg = _pjsua2_loader.pj.TransportConfig()
        cfg.port = 0
        try:
            transport_id = endpoint.transportCreate(transport_type, cfg)
            report["transports"][name] = {
                "ok": True,
                "id": transport_id,
                "error": "",
            }
        except Exception as exc:
            report["transports"][name] = {
                "ok": False,
                "id": None,
                "error": str(exc),
            }


def _enumerate_codecs(endpoint: Any, report: dict[str, Any]) -> None:
    codecs = [str(codec.codecId) for codec in endpoint.codecEnum2()]
    report["codecs"] = codecs
    lower = [codec.lower() for codec in codecs]
    report["required_codecs"]["g729"] = any(
        codec.startswith("g729/") for codec in lower
    )
    report["required_codecs"]["opus"] = any(
        codec.startswith("opus/") for codec in lower
    )


def _validate_report(report: dict[str, Any]) -> None:
    if not report["endpoint_created"]:
        return
    errors = report["errors"]
    required_transports = ("udp", "tcp", "tls")
    for name in required_transports:
        transport = report["transports"].get(name)
        if not transport or not transport.get("ok"):
            reason = transport.get("error") if transport else "not attempted"
            errors.append(f"{name.upper()} transport unavailable: {reason}")
    for codec_name, present in report["required_codecs"].items():
        if not present:
            errors.append(f"Missing required native codec: {codec_name}")
