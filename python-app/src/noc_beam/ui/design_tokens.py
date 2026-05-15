from __future__ import annotations

from dataclasses import dataclass


SPACING_UNIT = 4
RADIUS_SM = 4
RADIUS_MD = 6
BOTTOM_NAV_HEIGHT = 48
ICON_BUTTON_SIZE = 28
PRIMARY_BUTTON_HEIGHT = 32
COMPACT_INPUT_HEIGHT = 32


STATUS_LEVELS = {
    "ok": "ok",
    "progress": "progress",
    "warn": "warn",
    "danger": "danger",
    "info": "info",
    "muted": "muted",
    "running": "running",
}


@dataclass(frozen=True)
class ThemeRole:
    name: str
    meaning: str


THEME_ROLES = (
    ThemeRole("brand", "NOC_Beam mark and active navigation"),
    ThemeRole("ok", "registered, pass, call, SIP 200"),
    ThemeRole("progress", "ringing, pending, SIP 180"),
    ThemeRole("danger", "fail, missed, error"),
    ThemeRole("info", "trace and metadata"),
    ThemeRole("muted", "idle, disabled, secondary text"),
)
