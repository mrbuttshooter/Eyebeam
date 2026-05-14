"""Top title bar.

Wordmark on the left, active-account chip in the middle, global dial
bar on the right. Kept inside the central widget rather than replacing
the OS chrome -- frameless windows on Windows need careful Aero Snap
handling that's out of scope for the v2 first cut.

Public API:
- `set_accounts(list[(account_id, label)])` -- populates the chip menu
- `set_active_account(account_id)`           -- moves the chip selection
- `active_account_id` property               -- returns the current pick
- Signals: `dial_requested(str)`, `active_account_changed(str)`
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QPainter, QPixmap


TITLE_BAR_H = 44
WORDMARK_PX = 18
RESOURCES = Path(__file__).resolve().parent / "resources"


def _wordmark_pixmap(height_px: int = WORDMARK_PX, color: str = "#E6EDF3") -> QPixmap:
    """Render the title-bar wordmark SVG to a pixmap at `height_px` height."""
    svg_path = RESOURCES / "logo-wordmark.svg"
    if not svg_path.exists():
        return QPixmap()
    raw = svg_path.read_text(encoding="utf-8").replace("currentColor", color)
    renderer = QSvgRenderer(QByteArray(raw.encode("utf-8")))
    aspect = renderer.defaultSize().width() / max(renderer.defaultSize().height(), 1)
    width_px = int(height_px * aspect)
    pix = QPixmap(QSize(width_px, height_px))
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(painter)
    painter.end()
    return pix


class TitleBar(QFrame):
    dial_requested = Signal(str)
    active_account_changed = Signal(str)
    active_account_clicked = Signal()  # opens the Accounts destination

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(TITLE_BAR_H)

        self._accounts: list[tuple[str, str]] = []
        self._active_id: str = ""

        # ---- Wordmark
        self.wordmark = QLabel()
        self.wordmark.setObjectName("Wordmark")
        pm = _wordmark_pixmap()
        if not pm.isNull():
            self.wordmark.setPixmap(pm)
        else:
            self.wordmark.setText("noc_beam")
        self.wordmark.setFixedHeight(TITLE_BAR_H)

        # ---- Active account chip (button with dropdown menu)
        self.chip = QToolButton(self)
        self.chip.setObjectName("AccountChip")
        self.chip.setText("No account")
        self.chip.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.chip.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.chip.setMenu(QMenu(self.chip))
        self.chip.clicked.connect(self.active_account_clicked.emit)

        # ---- Dial bar (Ctrl+K focuses it)
        self.dial = QLineEdit(self)
        self.dial.setObjectName("DialBar")
        self.dial.setPlaceholderText("Enter number or SIP URI  (Ctrl+K)")
        self.dial.setClearButtonEnabled(True)
        self.dial.setMaximumWidth(360)
        self.dial.returnPressed.connect(self._on_return)
        self.dial.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        focus_dial = QAction(self)
        focus_dial.setShortcut(QKeySequence("Ctrl+K"))
        focus_dial.triggered.connect(self._focus_dial)
        # Add to self so the shortcut is window-scoped via parent's WindowShortcut
        self.addAction(focus_dial)

        # ---- Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(12)
        layout.addWidget(self.wordmark)
        layout.addSpacing(4)
        layout.addWidget(self.chip)
        layout.addStretch(1)
        layout.addWidget(self.dial)

    # ------------------------------------------------------------------
    def _focus_dial(self) -> None:
        self.dial.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.dial.selectAll()

    def _on_return(self) -> None:
        target = self.dial.text().strip()
        if not target:
            return
        self.dial_requested.emit(target)
        self.dial.clear()

    # ------------------------------------------------------------------
    def set_accounts(self, accounts: list[tuple[str, str]]) -> None:
        """`accounts` is list of (account_id, display_label). Order = menu order."""
        self._accounts = list(accounts)
        menu = QMenu(self.chip)
        if not accounts:
            empty = menu.addAction("No accounts")
            empty.setEnabled(False)
        else:
            for acc_id, label in accounts:
                act = menu.addAction(label)
                act.triggered.connect(lambda _checked=False, aid=acc_id: self._select(aid))
        menu.addSeparator()
        manage = menu.addAction("Manage accounts…")
        manage.triggered.connect(self.active_account_clicked.emit)
        self.chip.setMenu(menu)
        # Re-select the active account if it still exists, else first
        ids = [a for a, _ in accounts]
        if self._active_id in ids:
            self._set_chip_text(self._active_id)
        elif ids:
            self._select(ids[0])
        else:
            self._active_id = ""
            self.chip.setText("No account")

    def set_active_account(self, account_id: str) -> None:
        if account_id != self._active_id:
            self._select(account_id)

    @property
    def active_account_id(self) -> str:
        return self._active_id

    # ------------------------------------------------------------------
    def _select(self, account_id: str) -> None:
        self._active_id = account_id
        self._set_chip_text(account_id)
        self.active_account_changed.emit(account_id)

    def _set_chip_text(self, account_id: str) -> None:
        label = next((lbl for aid, lbl in self._accounts if aid == account_id), account_id)
        # The chip carries a ● dot prefix so it reads as a status pill, not a button.
        self.chip.setText(f"●  {label}")
