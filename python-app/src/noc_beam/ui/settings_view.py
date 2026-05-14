"""Settings destination -- the dialog content as a stack page.

Wraps the existing SettingsDialog so we don't duplicate the audio /
codec / advanced UI. The dialog body lives inside the view; the
Apply button on this view triggers the same `apply_to(settings)`
flow MainWindow used to call after a modal accept.

Phase F adds the Appearance sub-tab with the high-contrast toggle.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from noc_beam.config.store import GlobalSettings
from noc_beam.ui.settings_dialog import SettingsDialog


class SettingsView(QWidget):
    """A stack-friendly wrapper around SettingsDialog.

    SettingsDialog already builds the QTabWidget; we lift it out and
    pair it with our own header + Apply button. The dialog instance is
    kept alive so apply_to() works exactly like the modal path.
    """

    apply_requested = Signal(dict)  # codec_map produced by apply_to(settings)

    def __init__(self, settings: GlobalSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        # Build a SettingsDialog but never show it as a modal -- we
        # mine its child QTabWidget for the actual UI.
        self._dialog = SettingsDialog(settings)
        # The dialog's first child is its QTabWidget (we built it that
        # way). Pluck it and re-parent into this view.
        tabs = None
        for child in self._dialog.children():
            from PySide6.QtWidgets import QTabWidget

            if isinstance(child, QTabWidget):
                tabs = child
                break
        if tabs is None:
            raise RuntimeError("SettingsDialog has no QTabWidget child")
        tabs.setParent(self)

        title = QLabel("Settings")
        title.setObjectName("ViewTitle")
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setObjectName("PrimaryAction")
        self.apply_btn.clicked.connect(self._on_apply)

        header = QHBoxLayout()
        header.setContentsMargins(16, 12, 16, 8)
        header.setSpacing(8)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.apply_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(header)
        layout.addWidget(tabs, 1)

    def _on_apply(self) -> None:
        codec_map = self._dialog.apply_to(self._settings)
        self.apply_requested.emit(codec_map)
