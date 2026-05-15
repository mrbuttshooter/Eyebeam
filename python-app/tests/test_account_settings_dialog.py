"""Qt tests for the account-specific settings dialog."""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QApplication = QtWidgets.QApplication
_APP = QApplication.instance()
if _APP is None:
    _APP = QApplication([])

from noc_beam.config.store import AccountConfig  # noqa: E402
from noc_beam.ui.account_settings_dialog import AccountSettingsDialog  # noqa: E402


@pytest.fixture
def qt_app() -> QApplication:
    return _APP


def _account() -> AccountConfig:
    return AccountConfig(
        id="acct-original",
        display_name="NOC Primary",
        username="1001",
        auth_user="auth-1001",
        domain="sip.example.test",
        password="secret",
        proxy="sip:proxy.example.test;transport=tcp",
        transport="tcp",
        register=False,
        srtp="optional",
        dtmf_method="info",
        stun_server="stun.example.test",
        enabled=False,
    )


def test_prefills_existing_account_fields(qt_app: QApplication) -> None:
    dialog = AccountSettingsDialog(_account())
    dialog.show()
    qt_app.processEvents()

    try:
        assert dialog.windowTitle() == "Account Settings"
        assert dialog.display_name.text() == "NOC Primary"
        assert dialog.username.text() == "1001"
        assert dialog.auth_user.text() == "auth-1001"
        assert dialog.domain.text() == "sip.example.test"
        assert dialog.password.text() == "secret"
        assert dialog.proxy.text() == "sip:proxy.example.test;transport=tcp"
        assert dialog.transport.currentText() == "tcp"
        assert not dialog.register.isChecked()
        assert dialog.srtp.currentText() == "optional"
        assert dialog.dtmf_method.currentText() == "info"
        assert dialog.stun_server.text() == "stun.example.test"
        assert not dialog.enabled.isChecked()
    finally:
        dialog.close()


def test_result_account_preserves_id_and_reflects_edits(qt_app: QApplication) -> None:
    dialog = AccountSettingsDialog(_account())

    dialog.display_name.setText("Updated NOC")
    dialog.username.setText("  2002  ")
    dialog.auth_user.setText("  auth-2002  ")
    dialog.domain.setText("  pbx.example.test  ")
    dialog.password.setText("new secret")
    dialog.proxy.setText("  sip:edge.example.test  ")
    dialog.transport.setCurrentText("tls")
    dialog.register.setChecked(True)
    dialog.srtp.setCurrentText("mandatory")
    dialog.dtmf_method.setCurrentText("inband")
    dialog.stun_server.setText("  stun2.example.test  ")
    dialog.enabled.setChecked(True)

    try:
        result = dialog.result_account()

        assert result == AccountConfig(
            id="acct-original",
            display_name="Updated NOC",
            username="2002",
            auth_user="auth-2002",
            domain="pbx.example.test",
            password="new secret",
            proxy="sip:edge.example.test",
            transport="tls",
            register=True,
            srtp="mandatory",
            dtmf_method="inband",
            stun_server="stun2.example.test",
            enabled=True,
        )
    finally:
        dialog.close()
