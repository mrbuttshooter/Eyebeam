"""Left icon rail.

Five destinations + a registration status pill at the foot. Replaces
v1's left-side accounts list and the bottom QStatusBar combined.

Layout: 64 px wide, vertical. Each destination is a checkable QToolButton
in an exclusive QButtonGroup. Selecting one drives `destination_changed`
which the MainWindow uses to swap the QStackedWidget page.

NOC scope: Contacts / Voicemail / Conference are deliberately excluded
(see NOC_Beam/INTEGRATION.md). A Diagnostics destination is reserved
for Phase E.
"""
from __future__ import annotations

from enum import IntEnum

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPaintEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from noc_beam.ui.rail_icons import rail_icon_pair


RAIL_W = 64
ICON_PX = 22


class Dest(IntEnum):
    """Stack page indices, mirrored by rail button positions."""
    CALLS = 0
    TRACE = 1
    ACCOUNTS = 2
    HISTORY = 3
    SETTINGS = 4
    DIAGNOSTICS = 5  # Phase E adds the page; rail button is built unconditionally


_DESTINATIONS: tuple[tuple[Dest, str, str], ...] = (
    (Dest.CALLS,       "calls",       "Calls"),
    (Dest.TRACE,       "trace",       "Trace"),
    (Dest.ACCOUNTS,    "accounts",    "Accounts"),
    (Dest.HISTORY,     "history",     "History"),
    (Dest.SETTINGS,    "settings",    "Settings"),
    (Dest.DIAGNOSTICS, "diagnostics", "Diag"),
)


class StatusPill(QFrame):
    """Foot-of-rail registration counter. Replaces v1's QStatusBar.

    Shows N/M registered with a coloured dot. show_message(text, ms)
    flashes a transient line of status text below the counter so the
    pill keeps the surface area v1's status bar gave us. Falls back to
    the registration counter when ms elapses.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RailStatusPill")
        self.setFixedWidth(RAIL_W)

        self._registered = 0
        self._total = 0
        self._dot_color = QColor("#7C8696")  # neutral when nothing's registered

        self.counter = QLabel("0/0")
        self.counter.setObjectName("RailCounter")
        self.counter.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.flash = QLabel("")
        self.flash.setObjectName("RailFlash")
        self.flash.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.flash.setWordWrap(True)
        self.flash.setMinimumHeight(0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 6, 4, 8)
        layout.setSpacing(2)
        layout.addWidget(self.counter)
        layout.addWidget(self.flash)

        self._timer_id: int | None = None

    # ------------------------------------------------------------------
    def set_registration(self, registered: int, total: int) -> None:
        self._registered = registered
        self._total = total
        self.counter.setText(f"{registered}/{total}")
        if total == 0:
            self._dot_color = QColor("#7C8696")
        elif registered == total:
            self._dot_color = QColor("#66D19E")  # all green
        elif registered == 0:
            self._dot_color = QColor("#FF5C7A")  # none — danger
        else:
            self._dot_color = QColor("#F0C36D")  # partial — warning
        self.update()

    def show_message(self, text: str, ms: int = 0) -> None:
        """Flash a transient status line; ms<=0 means sticky until next call."""
        self.flash.setText(text)
        if self._timer_id is not None:
            self.killTimer(self._timer_id)
            self._timer_id = None
        if ms > 0:
            self._timer_id = self.startTimer(ms)

    def timerEvent(self, event):  # noqa: N802, ANN001
        if event.timerId() == self._timer_id:
            self.killTimer(self._timer_id)
            self._timer_id = None
            self.flash.setText("")
        super().timerEvent(event)

    # Compatibility shim so MainWindow can keep calling `self.status.showMessage`.
    def showMessage(self, text: str, ms: int = 0) -> None:  # noqa: N802
        self.show_message(text, ms)

    # ------------------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(self._dot_color)
        painter.setPen(Qt.PenStyle.NoPen)
        cx = self.width() // 2
        # 4 px dot, sits above the counter text
        painter.drawEllipse(cx - 4, 4, 8, 8)
        painter.end()


class Rail(QFrame):
    destination_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Rail")
        self.setFixedWidth(RAIL_W)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: dict[int, QToolButton] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(2)

        for dest, icon_name, label in _DESTINATIONS:
            btn = self._build_button(icon_name, label)
            self.group.addButton(btn, int(dest))
            self.buttons[int(dest)] = btn
            layout.addWidget(btn)

        layout.addStretch(1)

        self.status_pill = StatusPill(self)
        layout.addWidget(self.status_pill)

        self.group.idClicked.connect(self._on_id_clicked)

        # Default destination
        self.buttons[int(Dest.CALLS)].setChecked(True)

    # ------------------------------------------------------------------
    def _build_button(self, icon_name: str, label: str) -> QToolButton:
        btn = QToolButton(self)
        btn.setObjectName("RailBtn")
        btn.setCheckable(True)
        btn.setIcon(rail_icon_pair(icon_name, px=ICON_PX))
        btn.setIconSize(QSize(ICON_PX, ICON_PX))
        btn.setText(label)
        btn.setToolTip(label)
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        btn.setFixedSize(RAIL_W, 56)
        btn.setAutoExclusive(True)
        return btn

    def _on_id_clicked(self, btn_id: int) -> None:
        self.destination_changed.emit(btn_id)

    # ------------------------------------------------------------------
    def select(self, dest: int) -> None:
        btn = self.buttons.get(int(dest))
        if btn is not None and not btn.isChecked():
            btn.setChecked(True)
            self.destination_changed.emit(int(dest))
