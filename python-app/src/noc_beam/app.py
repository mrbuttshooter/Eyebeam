"""NOC_Beam QApplication bootstrap."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from noc_beam import __app_name__
from noc_beam.config.store import load_settings
from noc_beam.crash_handler import install as install_crash_handler
from noc_beam.logging_setup import setup_logging
from noc_beam.ui.phone_shell import PhoneShell
from noc_beam.ui.theme import apply_theme

log = logging.getLogger(__name__)


def _load_icon() -> QIcon:
    # Look for an icon next to the package or in resources
    here = Path(__file__).resolve().parent
    candidates = [
        here / "ui" / "resources" / "icon.ico",
        here.parent.parent.parent / "assets" / "icon.ico",
    ]
    for p in candidates:
        if p.exists():
            return QIcon(str(p))
    return QIcon()


def run(argv: list[str]) -> int:
    setup_logging()
    # Install crash handlers BEFORE we touch PJSIP -- a startup-time
    # native fault in libCreate is exactly the class of bug we most
    # need traces for. faulthandler + sys.excepthook + threading
    # excepthook all wired here; Sentry SDK opt-in via DSN env-var
    # or config_dir()/sentry.dsn.
    install_crash_handler()
    log.info("Starting %s", __app_name__)

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    QApplication.setApplicationName(__app_name__)
    QApplication.setOrganizationName(__app_name__)

    app = QApplication(argv)
    app.setWindowIcon(_load_icon())

    # Load persisted settings to pick the theme. PhoneShell loads them
    # again itself; this is the small price of theme being a process-
    # wide concern (QApplication.setStyleSheet) while the rest of
    # settings live on the window. Default theme is "light" (the
    # Bria-evolution direction); dark / dark-hc remain available for
    # users who prefer the original NOC dashboard look.
    settings = load_settings()
    theme = getattr(settings.appearance, "theme", "light")
    apply_theme(app, settings.appearance.high_contrast, theme=theme)

    # FAS detection engine. The audio tap is wired per-call in
    # sip/call.py:onCallMediaState; this just spins up the worker
    # thread so it's ready when the first call confirms. Honours
    # FasSettings.enabled -- when False, attach_fas_to_call becomes
    # a no-op throughout the process lifetime.
    try:
        from noc_beam.audio.fas_engine import start_fas_engine

        fas_cfg = getattr(settings, "fas", None)
        start_fas_engine(enabled=bool(fas_cfg.enabled) if fas_cfg else True)
    except Exception:
        log.exception("FAS engine failed to start; continuing without FAS detection")

    window = PhoneShell()
    # Honour StartupSettings persisted from Settings -> General.
    # start_minimized launches into the tray (or minimized to taskbar
    # if no tray) instead of popping a foreground window. Was
    # display-only at the checkbox layer until this hook.
    _start_cfg = getattr(settings, "startup", None)
    if _start_cfg is not None and getattr(_start_cfg, "start_minimized", False):
        if getattr(window, "tray", None) is not None and window.tray.available:
            window.hide()
        else:
            window.showMinimized()
    else:
        window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(run(sys.argv))
