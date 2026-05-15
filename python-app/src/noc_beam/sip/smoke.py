"""Packaged executable SIP smoke diagnostics."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from noc_beam.sip import _pjsua2_loader


def run_sip_smoke(*, require_native: bool = True) -> tuple[int, dict[str, Any]]:
    """Create and destroy a PJSIP endpoint, returning an exit code and report."""

    report: dict[str, Any] = {
        "ok": False,
        "source": _pjsua2_loader.PJSUA2_SOURCE,
        "available": _pjsua2_loader.PJSUA2_AVAILABLE,
        "native_required": require_native,
        "endpoint_created": False,
        "endpoint_destroyed": False,
        "pjsip_version": "",
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
    finally:
        if endpoint is not None:
            try:
                endpoint.libDestroy()
                report["endpoint_destroyed"] = True
            except Exception as exc:
                errors.append(f"Endpoint destroy failed: {exc}")

    if report["endpoint_created"] and report["endpoint_destroyed"] and not errors:
        report["ok"] = True
        return 0, report
    return 1, report


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
