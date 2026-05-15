"""Dialog to add/edit a single SIP account."""
from __future__ import annotations

import logging
import re
import uuid

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from noc_beam.config.store import AccountConfig
from noc_beam.ui.components import FooterActionBar, FormSection

log = logging.getLogger(__name__)


# How long to wait for a registration response before declaring timeout.
TEST_TIMEOUT_MS = 8000

# Reject anything that isn't a normal host name. Specifically blocks
# CR/LF and other control chars that could smuggle SIP headers when
# the URI is interpolated into an outgoing request.
_DOMAIN_RX = re.compile(r"^[A-Za-z0-9._:\[\]\-]+$")


class AccountDialog(QDialog):
    def __init__(self, account: AccountConfig | None = None, parent=None) -> None:  # noqa: ANN001
        super().__init__(parent)
        self.setWindowTitle("Edit SIP account" if account is not None else "Add SIP account")
        self.setMinimumWidth(420)

        self._editing = account is not None
        if account is None:
            account = AccountConfig(id=str(uuid.uuid4()))

        self.display_name = QLineEdit(account.display_name)
        self.username = QLineEdit(account.username)
        self.auth_user = QLineEdit(account.auth_user)
        self.domain = QLineEdit(account.domain)
        self.password = QLineEdit(account.password)
        self.password.setEchoMode(QLineEdit.Password)
        self.proxy = QLineEdit(account.proxy)
        self.stun_server = QLineEdit(account.stun_server)
        # Optional port. Blank or 0 = transport default (5060 / 5061).
        # Many real ITSPs publish on non-default ports.
        self.port = QLineEdit("" if not getattr(account, "port", 0) else str(account.port))
        self.port.setPlaceholderText("default (5060 / 5061)")
        self.port.setMaximumWidth(180)

        self.transport = QComboBox()
        self.transport.addItems(["udp", "tcp", "tls"])
        self.transport.setCurrentText(account.transport)

        self.srtp = QComboBox()
        self.srtp.addItems(["disabled", "optional", "mandatory"])
        self.srtp.setCurrentText(account.srtp)

        self.dtmf_method = QComboBox()
        self.dtmf_method.addItems(["rfc2833", "info", "inband"])
        self.dtmf_method.setCurrentText(account.dtmf_method)

        self.register = QCheckBox("Register on add")
        self.register.setChecked(account.register)

        self.enabled = QCheckBox("Enabled")
        self.enabled.setChecked(account.enabled)

        identity = FormSection("Identity", self)
        identity_form = QFormLayout()
        identity_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        identity_form.addRow("Display name", self.display_name)
        identity_form.addRow("Username *", self.username)
        identity_form.addRow("Auth user", self.auth_user)
        identity.body.addLayout(identity_form)

        connection = FormSection("Connection", self)
        connection_form = QFormLayout()
        connection_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        connection_form.addRow("Domain *", self.domain)
        connection_form.addRow("Port", self.port)
        connection_form.addRow("Password", self.password)
        connection_form.addRow("Outbound proxy", self.proxy)
        connection_form.addRow("STUN server", self.stun_server)
        connection.body.addLayout(connection_form)

        options = FormSection("Options", self)
        options_form = QFormLayout()
        options_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        options_form.addRow("Transport", self.transport)
        options_form.addRow("SRTP", self.srtp)
        options_form.addRow("DTMF method", self.dtmf_method)
        options_form.addRow(self.register)
        options_form.addRow(self.enabled)
        options.body.addLayout(options_form)

        self.error = QLabel("", self)
        self.error.setObjectName("DialogError")
        self.error.setWordWrap(True)

        # Test row — its label is reused for live + final status.
        self.test_btn = QPushButton("Test registration")
        self.test_btn.clicked.connect(self._on_test)
        self.test_status = QLabel("")
        self.test_status.setObjectName("AccountTestStatus")
        self.test_status.setWordWrap(True)
        test_row = QHBoxLayout()
        test_row.addWidget(self.test_btn)
        test_row.addWidget(self.test_status, 1, Qt.AlignVCenter)

        self.footer = FooterActionBar("Save" if self._editing else "Add account", "Cancel", self)
        self.footer.primary_button.clicked.connect(self.accept)
        self.footer.secondary_button.clicked.connect(self.reject)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)
        root.addWidget(identity)
        root.addWidget(connection)
        root.addWidget(options)
        root.addWidget(self.error)
        root.addLayout(test_row)
        root.addWidget(self.footer)

        self._account_id = account.id

        # Per-test bookkeeping
        self._test_id: str | None = None
        self._test_timer: QTimer | None = None
        self._test_conn = None

    def result_account(self) -> AccountConfig:
        port_txt = self.port.text().strip()
        try:
            port_val = int(port_txt) if port_txt else 0
        except ValueError:
            port_val = 0
        return AccountConfig(
            id=self._account_id,
            display_name=self.display_name.text().strip(),
            username=self.username.text().strip(),
            auth_user=self.auth_user.text().strip(),
            domain=self.domain.text().strip(),
            password=self.password.text(),
            proxy=self.proxy.text().strip(),
            transport=self.transport.currentText(),
            register=self.register.isChecked(),
            srtp=self.srtp.currentText(),
            dtmf_method=self.dtmf_method.currentText(),
            stun_server=self.stun_server.text().strip(),
            enabled=self.enabled.isChecked(),
            port=port_val,
        )

    def accept(self) -> None:
        missing = []
        if not self.username.text().strip():
            missing.append("Username")
        if not self.domain.text().strip():
            missing.append("Domain")
        if missing:
            self.error.setText(", ".join(missing) + " required.")
            first = self.username if "Username" in missing else self.domain
            first.setFocus()
            return
        # Domain field can carry SIP-injection if it contains \r, \n,
        # or other control chars -- the URI is interpolated into a
        # SIP message later. Reject anything that isn't host-allowed.
        domain = self.domain.text().strip()
        if not _DOMAIN_RX.match(domain):
            self.error.setText(
                "Domain must be a host name (letters, digits, dots, dashes only)."
            )
            self.domain.setFocus()
            return
        # Optional port: if filled, must be 1..65535.
        port_txt = self.port.text().strip()
        if port_txt:
            try:
                port_val = int(port_txt)
                if not (1 <= port_val <= 65535):
                    raise ValueError
            except ValueError:
                self.error.setText("Port must be a number between 1 and 65535.")
                self.port.setFocus()
                return
        # Tear down any in-flight test-registration before accepting --
        # the test account would otherwise leak past dialog close.
        self._cleanup_test()
        super().accept()

    def reject(self) -> None:
        # Same cleanup on Cancel: without this, a test-registration
        # that was issued and then Cancel'd leaves a __test__* PJSIP
        # account live AND keeps the registration_changed signal
        # connected to a slot on a deleted QDialog -> SIGSEGV.
        self._cleanup_test()
        super().reject()

    def closeEvent(self, event):  # noqa: ANN001
        self._cleanup_test()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Test registration
    # ------------------------------------------------------------------
    def _on_test(self) -> None:
        username = self.username.text().strip()
        domain = self.domain.text().strip()
        if not username or not domain:
            self._set_status("Username and domain are required.", ok=False)
            return

        # Late import to avoid pulling SIP at dialog construction time.
        from noc_beam.sip.endpoint import SipEndpoint
        from noc_beam.sip.events import sip_events

        ep = SipEndpoint.instance()
        if not ep.is_started():
            self._set_status("SIP endpoint isn't running yet.", ok=False)
            return

        # Build a throw-away account with a sentinel id so we can match the
        # incoming registration_changed signal without colliding with any
        # real account.
        self._test_id = f"__test__{uuid.uuid4().hex[:8]}"
        cfg = self.result_account()
        cfg.id = self._test_id
        cfg.register = True
        cfg.enabled = True

        self._set_status("Registering…", ok=None)
        self.test_btn.setEnabled(False)

        self._test_conn = sip_events().registration_changed.connect(self._on_reg_event)
        self._test_timer = QTimer(self)
        self._test_timer.setSingleShot(True)
        self._test_timer.timeout.connect(self._on_test_timeout)
        self._test_timer.start(TEST_TIMEOUT_MS)

        try:
            ep.add_account(cfg)
        except Exception as e:
            log.exception("test add_account failed")
            self._set_status(f"Could not start test: {e}", ok=False)
            self._cleanup_test()

    def _on_reg_event(self, account_id: str, code: int, reason: str) -> None:
        if account_id != self._test_id:
            return
        # 0 with empty reason is the initial "not yet" event; ignore it.
        if code == 0 and not reason:
            return
        ok = 200 <= code < 300
        verdict = "OK" if ok else "FAIL"
        self._set_status(f"{verdict} — {code} {reason}", ok=ok)
        self._cleanup_test()

    def _on_test_timeout(self) -> None:
        self._set_status("Timeout — no response within "
                         f"{TEST_TIMEOUT_MS // 1000}s.", ok=False)
        self._cleanup_test()

    def _cleanup_test(self) -> None:
        from noc_beam.sip.endpoint import SipEndpoint

        if self._test_timer is not None:
            self._test_timer.stop()
            self._test_timer = None
        # Only attempt a disconnect when we actually wired up the slot.
        # _cleanup_test is now also called from reject() / closeEvent()
        # before any test was started; the previous unconditional
        # disconnect would raise RuntimeError (caught silently) on
        # every dialog cancel, masking real wiring bugs.
        if self._test_conn is not None:
            try:
                from noc_beam.sip.events import sip_events
                sip_events().registration_changed.disconnect(self._on_reg_event)
            except Exception:
                pass
            self._test_conn = None
        if self._test_id is not None:
            try:
                SipEndpoint.instance().remove_account(self._test_id)
            except Exception:
                log.exception("could not remove test account %s", self._test_id)
            self._test_id = None
        self.test_btn.setEnabled(True)

    def _set_status(self, text: str, ok: bool | None) -> None:
        self.test_status.setText(text)
        color = {
            True:  "#66D19E",   # success
            False: "#FF5C7A",   # danger
            None:  "#B7C0CC",   # in-progress / neutral
        }[ok]
        self.test_status.setStyleSheet(f"color: {color};")
