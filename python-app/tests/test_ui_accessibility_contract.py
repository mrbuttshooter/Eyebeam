from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QApplication = QtWidgets.QApplication
QPushButton = QtWidgets.QPushButton
QToolButton = QtWidgets.QToolButton
_APP = QApplication.instance()
if _APP is None:
    _APP = QApplication([])

from noc_beam.ui.phone_shell import PhoneShell  # noqa: E402


def test_shell_interactive_controls_have_accessible_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("noc_beam.ui.phone_shell.QTimer.singleShot", lambda _ms, _fn: None)
    shell = PhoneShell()

    try:
        controls = shell.findChildren(QPushButton) + shell.findChildren(QToolButton)
        named = [c for c in controls if c.accessibleName() or c.toolTip() or c.text()]
        assert len(named) == len(controls)
    finally:
        shell.close()


def test_destructive_buttons_are_text_labeled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("noc_beam.ui.phone_shell.QTimer.singleShot", lambda _ms, _fn: None)
    shell = PhoneShell()

    try:
        destructive = shell.findChildren(QPushButton, "HangupButton")
        for button in destructive:
            label = button.text() + button.accessibleName()
            assert button.text().strip()
            assert "hang" in label.lower()
    finally:
        shell.close()
