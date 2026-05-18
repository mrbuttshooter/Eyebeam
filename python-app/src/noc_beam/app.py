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

# Module-level mutex handle. Kept alive for the process lifetime so the
# named mutex stays held until the OS reaps the process. Windows auto-
# releases the handle on process exit; we deliberately do NOT close it.
_SINGLE_INSTANCE_MUTEX = None
_SINGLE_INSTANCE_NAME = "Global\\NOC_Beam_SingleInstance"
_ERROR_ALREADY_EXISTS = 183


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


def _acquire_single_instance_or_exit(argv: list[str]) -> int | None:
    """Attempt to acquire the process-wide single-instance mutex.

    Returns None on success (this is the only instance, continue startup).
    Returns an int exit code if another instance is already running --
    caller should propagate that code out of run().

    On non-Windows we skip entirely: the mutex API is Win32-only and our
    target platform is Windows. POSIX builds would need flock/fcntl, but
    NOC_Beam is shipped only on Windows so adding that surface is dead
    code today.
    """
    global _SINGLE_INSTANCE_MUTEX
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        # bInitialOwner=True so the first instance immediately owns it.
        # The handle is intentionally leaked to module scope; process
        # exit releases it. Name is in the Global\ namespace so it works
        # across user sessions on the same machine (terminal services /
        # fast user switching) -- last-writer-wins on accounts.json is a
        # machine-wide concern, not a per-user one.
        _SINGLE_INSTANCE_MUTEX = kernel32.CreateMutexW(None, True, _SINGLE_INSTANCE_NAME)
        err = kernel32.GetLastError()
    except Exception:
        log.exception("Single-instance check failed; allowing startup")
        return None

    if err != _ERROR_ALREADY_EXISTS:
        return None

    # Another instance is already running. Show a friendly dialog and
    # bail with exit code 0 (this is the expected user-facing outcome,
    # not a failure).
    log.warning("NOC_Beam is already running; aborting second instance")
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        _msg_app = QApplication.instance() or QApplication(argv)
        QMessageBox.information(
            None,
            __app_name__,
            "NOC_Beam is already running. Check your system tray.",
        )
    except Exception:
        # If even the message box fails (no display, etc.), the log line
        # above is our breadcrumb. Still exit cleanly.
        log.exception("Failed to show already-running message box")
    return 0


def run(argv: list[str]) -> int:
    # Single-instance guard FIRST -- before logging setup, crash handler,
    # or any PJSIP/Qt construction. Two NOC_Beam processes both writing
    # accounts.json + call_history.json silently lose CDRs (last-writer-
    # wins), and PJSIP itself wants a singleton process.
    _existing = _acquire_single_instance_or_exit(argv)
    if _existing is not None:
        return _existing

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
