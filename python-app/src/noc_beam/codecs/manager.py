"""Codec discovery and priority helpers.

PJSIP exposes codecs via Endpoint.codecEnum2(). The codecId looks like
"PCMU/8000/1" or "opus/48000/2". We store priorities as a dict of substring
matches → 0..255, where 0 disables and 255 is highest priority.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from noc_beam.sip._pjsua2_loader import PJSUA2_AVAILABLE, pj

log = logging.getLogger(__name__)


@dataclass
class CodecInfo:
    codec_id: str           # e.g. "PCMU/8000/1"
    priority: int           # 0..255

    @property
    def display_name(self) -> str:
        # "PCMU/8000/1" → "PCMU 8000 Hz"
        parts = self.codec_id.split("/")
        if len(parts) >= 2:
            return f"{parts[0]} {parts[1]} Hz"
        return self.codec_id

    @property
    def enabled(self) -> bool:
        return self.priority > 0


def _endpoint_ready() -> bool:
    # See audio/devices.enumerate_devices() for the rationale. Touching
    # pj.Endpoint.instance() before libCreate dereferences an
    # uninitialised C++ vtable and segfaults the process.
    try:
        from noc_beam.sip.endpoint import SipEndpoint
        return SipEndpoint.instance().is_started()
    except Exception:
        return False


def list_codecs() -> list[CodecInfo]:
    if not PJSUA2_AVAILABLE or not _endpoint_ready():
        return []
    try:
        ep = pj.Endpoint.instance()
        items = ep.codecEnum2()
        return [CodecInfo(codec_id=c.codecId, priority=c.priority) for c in items]
    except Exception:
        log.exception("codecEnum2 failed")
        return []


def set_priority(codec_id: str, priority: int) -> None:
    priority = max(0, min(255, priority))
    if not PJSUA2_AVAILABLE or not _endpoint_ready():
        return
    try:
        pj.Endpoint.instance().codecSetPriority(codec_id, priority)
    except Exception:
        log.exception("codecSetPriority failed for %s", codec_id)
