"""Bria-style dialog for editing settings on an existing SIP account."""
from __future__ import annotations

from noc_beam.config.store import AccountConfig
from noc_beam.ui.account_dialog import AccountDialog


class AccountSettingsDialog(AccountDialog):
    """Account-specific settings editor.

    This is intentionally separate from PhoneShell wiring and persistence. It
    reuses the existing account form so the editable SIP fields stay aligned
    with the add/edit account dialog while providing a distinct public entry
    point for Bria-parity account settings.
    """

    def __init__(self, account: AccountConfig, parent=None) -> None:  # noqa: ANN001
        super().__init__(account=account, parent=parent)
        self.setWindowTitle("Account Settings")
        self.register.setText("Register this account")
