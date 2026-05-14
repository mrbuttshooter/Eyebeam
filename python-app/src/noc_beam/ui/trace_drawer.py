"""Right-side slide-out drawer for the live SIP trace.

Phase C wires the show/hide and the layout slot. Phase D drives the
QPropertyAnimation on `maximumWidth` (240 ms ease-out). Open/close
calls in C are immediate; the same API still works once D animates.

The drawer hosts an existing TraceView -- we re-parent it rather
than build a second viewer. The trace destination on the rail uses
its own TraceView so the user can have a focused full-width view as
well as the always-on-call companion.
"""
from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


DRAWER_W = 360
DUR_SLOW = 240  # ms — matches motion.md REVEAL bucket


class TraceDrawer(QFrame):
    """Slide-out frame on the right edge of the window.

    The animation is driven by `_anim_width` (a Qt property the
    animation can target) which forwards to setMaximumWidth +
    setMinimumWidth so the layout actually re-flows. `closed_width`
    is 0 and `open_width` is DRAWER_W.
    """

    closed = Signal()
    opened = Signal()

    def __init__(self, body: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TraceDrawer")
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._open = False
        self._anim_w_value = 0
        self.setMinimumWidth(0)
        self.setMaximumWidth(0)

        # ---- Header: title + ● LIVE pulse + close button
        self.header_title = QLabel("Live trace")
        self.header_title.setObjectName("DrawerTitle")
        self.live_label = QLabel("●  LIVE")
        self.live_label.setObjectName("DrawerLive")
        self.close_btn = QPushButton("Close")
        self.close_btn.setObjectName("DrawerClose")
        self.close_btn.setFlat(True)
        self.close_btn.clicked.connect(self.close)

        header = QHBoxLayout()
        header.setContentsMargins(12, 8, 8, 8)
        header.setSpacing(8)
        header.addWidget(self.header_title)
        header.addStretch(1)
        header.addWidget(self.live_label)
        header.addWidget(self.close_btn)

        # ---- Body slot (a TraceView re-parented in by MainWindow)
        self.body = body
        body.setParent(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(header)
        layout.addWidget(self.body, 1)

        # ---- Animation (Phase D drives this; Phase C just snaps width)
        self._anim = QPropertyAnimation(self, b"_animWidth", self)
        self._anim.setDuration(DUR_SLOW)
        # OutCubic is the closest preset to cubic-bezier(0.2, 0, 0, 1).
        # Phase D swaps in a custom QEasingCurve.Type.BezierSpline with
        # explicit control points + the reduced-motion gate.
        self._anim.setEasingCurve(QEasingCurve(QEasingCurve.Type.OutCubic))

    # ------------------------------------------------------------------
    # Qt Property used as the animation target. We don't animate
    # maximumWidth directly because Qt won't refresh the layout each
    # frame from a stylesheet-managed dimension; mirroring the value
    # onto both min and max keeps things deterministic.
    def _get_anim_w(self) -> int:
        return self._anim_w_value

    def _set_anim_w(self, value: int) -> None:
        self._anim_w_value = max(0, value)
        self.setMinimumWidth(self._anim_w_value)
        self.setMaximumWidth(self._anim_w_value)

    _animWidth = Property(int, _get_anim_w, _set_anim_w)

    # ------------------------------------------------------------------
    def is_open(self) -> bool:
        return self._open

    def open(self) -> None:  # noqa: A003
        if self._open:
            return
        self._open = True
        self._animate_to(DRAWER_W)
        self.opened.emit()

    def close(self) -> None:
        if not self._open:
            return
        self._open = False
        self._animate_to(0)
        self.closed.emit()

    def toggle(self) -> None:
        self.close() if self._open else self.open()

    # Phase D switches this to the property animation. For now, snap.
    def _animate_to(self, target: int) -> None:
        # The Property+animation infrastructure is wired so Phase D
        # can simply enable the start/stop calls below. Snap-only for
        # Phase C keeps the layout deterministic in tests.
        self._anim.stop()
        self._set_anim_w(target)
