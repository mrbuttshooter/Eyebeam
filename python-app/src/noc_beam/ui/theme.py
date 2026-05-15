"""Stylesheet swap helper.

Three themes shipped: light (Bria-evolution default for the phone
shell), dark (the original NOC dashboard look), and dark-hc (high-
contrast). Falls back gracefully: missing stylesheets quietly keep
the previous one rather than blanking the UI.
"""
from __future__ import annotations

import logging
from importlib import resources

from PySide6.QtWidgets import QApplication

log = logging.getLogger(__name__)


def _load(name: str) -> str:
    try:
        return resources.files("noc_beam.ui.resources").joinpath(name).read_text(
            encoding="utf-8"
        )
    except Exception:
        log.warning("Could not load stylesheet %s", name, exc_info=True)
        return ""


def load_theme_qss(*, theme: str = "light", high_contrast: bool = False) -> str:
    """Returns the QSS text for the chosen theme, or '' on failure.

    theme in: 'light' | 'dark'. high_contrast=True forces 'dark-hc.qss'.
    """
    if high_contrast:
        return _load("dark-hc.qss")
    if theme == "dark":
        return _load("dark.qss")
    return _load("light.qss")


def apply_theme(app: QApplication, high_contrast: bool = False, *, theme: str = "light") -> None:
    qss = load_theme_qss(theme=theme, high_contrast=high_contrast)
    if qss:
        app.setStyleSheet(qss)
