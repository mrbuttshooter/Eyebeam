from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QApplication = QtWidgets.QApplication
_APP = QApplication.instance()
if _APP is None:
    _APP = QApplication([])

from noc_beam.config.store import GlobalSettings  # noqa: E402
from noc_beam.ui.account_dialog import AccountDialog  # noqa: E402
from noc_beam.ui.settings_dialog import SettingsDialog  # noqa: E402


def test_account_dialog_has_form_sections_and_footer() -> None:
    dlg = AccountDialog()

    try:
        assert dlg.findChild(QtWidgets.QFrame, "FormSection") is not None
        assert dlg.findChild(QtWidgets.QFrame, "FooterActionBar") is not None
        assert dlg.windowTitle() in {"Add SIP account", "Edit SIP account"}
    finally:
        dlg.close()


def test_account_dialog_required_fields_show_inline_error() -> None:
    dlg = AccountDialog()

    try:
        dlg.accept()
        assert "required" in dlg.error.text().lower()
    finally:
        dlg.close()


def test_settings_dialog_has_footer_action_bar() -> None:
    dlg = SettingsDialog(GlobalSettings())

    try:
        assert dlg.findChild(QtWidgets.QFrame, "FooterActionBar") is not None
    finally:
        dlg.close()
