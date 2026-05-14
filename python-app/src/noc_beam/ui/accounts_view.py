"""Accounts destination -- accounts list + add/edit/remove actions.

Re-parents the v1 QListWidget into a proper view with an inline action
bar at the top. Replaces the bottom-of-window add/edit/remove toolbar.
The list payload (UserRole = account_id) is unchanged so MainWindow
can keep using its existing selection helpers.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from noc_beam.config.store import AccountConfig


class AccountsView(QWidget):
    add_clicked = Signal()
    edit_clicked = Signal()
    remove_clicked = Signal()
    selected_account_changed = Signal(str)  # account_id, "" if cleared

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # ---- Header bar with title + count + actions
        title = QLabel("Accounts")
        title.setObjectName("ViewTitle")
        self.count_label = QLabel("0")
        self.count_label.setObjectName("ViewCount")

        self.add_btn = QPushButton("Add account")
        self.edit_btn = QPushButton("Edit account")
        self.remove_btn = QPushButton("Remove account")
        self.add_btn.clicked.connect(self.add_clicked.emit)
        self.edit_btn.clicked.connect(self.edit_clicked.emit)
        self.remove_btn.clicked.connect(self.remove_clicked.emit)

        header = QHBoxLayout()
        header.setContentsMargins(16, 12, 16, 8)
        header.setSpacing(8)
        header.addWidget(title)
        header.addWidget(self.count_label)
        header.addStretch(1)
        header.addWidget(self.add_btn)
        header.addWidget(self.edit_btn)
        header.addWidget(self.remove_btn)

        # ---- List itself (kept compatible with v1's payload contract)
        self.list = QListWidget()
        self.list.setObjectName("AccountList")
        self.list.currentItemChanged.connect(self._on_current_changed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(header)
        layout.addWidget(self.list, 1)

    # ------------------------------------------------------------------
    def populate(self, accounts: list[AccountConfig]) -> None:
        self.list.clear()
        for acc in accounts:
            label = acc.display_name or f"{acc.username}@{acc.domain}"
            item = QListWidgetItem(f"{label}  [{acc.transport.upper()}]")
            item.setData(Qt.ItemDataRole.UserRole, acc.id)
            self.list.addItem(item)
        self.count_label.setText(str(len(accounts)))

    def selected_account_id(self) -> str | None:
        item = self.list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_current_changed(self, current, _previous) -> None:  # noqa: ANN001
        if current is None:
            self.selected_account_changed.emit("")
        else:
            self.selected_account_changed.emit(current.data(Qt.ItemDataRole.UserRole))
