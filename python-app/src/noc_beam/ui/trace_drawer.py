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
    QPointF,
    QPropertyAnimation,
    Qt,
    Signal,
)
from PySide6.QtCore import QSize as _QSize
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from noc_beam.ui.rail_icons import rail_icon


DRAWER_W = 360
DUR_SLOW = 240  # ms — matches motion.md REVEAL bucket
PULSE_LIVE = 1400  # ms — ● LIVE dot loop


def _live_dot_pixmap(px: int = 10, color_hex: str = "#FF5C7A") -> QPixmap:
    """Solid coloured circle for the LIVE indicator -- crisper than a glyph."""
    pix = QPixmap(_QSize(px, px))
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setBrush(QColor(color_hex))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(0, 0, px, px)
    painter.end()
    return pix


def house_curve() -> QEasingCurve:
    """cubic-bezier(0.2, 0, 0, 1) -- the motion.md house ease-out."""
    curve = QEasingCurve(QEasingCurve.Type.BezierSpline)
    curve.addCubicBezierSegment(
        QPointF(0.2, 0.0),
        QPointF(0.0, 1.0),
        QPointF(1.0, 1.0),
    )
    return curve


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
        self._reduced_motion = False
        self.setMinimumWidth(0)
        self.setMaximumWidth(0)

        # ---- Header: title + ● LIVE pulse + close button
        self.header_title = QLabel("Live trace")
        self.header_title.setObjectName("DrawerTitle")

        # LIVE badge: pixmap dot + "LIVE" text. Pulse is on the QGraphicsOpacityEffect
        # attached to the row so the dot + label fade together.
        self.live_badge = QFrame()
        self.live_badge.setObjectName("DrawerLiveBadge")
        live_l = QHBoxLayout(self.live_badge)
        live_l.setContentsMargins(0, 0, 0, 0)
        live_l.setSpacing(6)
        self.live_dot = QLabel(self.live_badge)
        self.live_dot.setObjectName("DrawerLiveDot")
        self.live_dot.setPixmap(_live_dot_pixmap())
        self.live_dot.setFixedSize(10, 10)
        self.live_label = QLabel("LIVE", self.live_badge)
        self.live_label.setObjectName("DrawerLive")
        live_l.addWidget(self.live_dot)
        live_l.addWidget(self.live_label)

        self._live_effect = QGraphicsOpacityEffect(self.live_badge)
        self._live_effect.setOpacity(1.0)
        self.live_badge.setGraphicsEffect(self._live_effect)
        self._live_anim = QPropertyAnimation(self._live_effect, b"opacity", self)
        self._live_anim.setDuration(PULSE_LIVE)
        self._live_anim.setStartValue(1.0)
        self._live_anim.setKeyValueAt(0.5, 0.35)
        self._live_anim.setEndValue(1.0)
        self._live_anim.setLoopCount(-1)
        self._live_anim.setEasingCurve(QEasingCurve(QEasingCurve.Type.InOutSine))

        # Close button: use the rail's "close" SVG (X icon) rendered to a pixmap.
        self.close_btn = QPushButton(self)
        self.close_btn.setObjectName("DrawerClose")
        self.close_btn.setIcon(rail_icon("close", color="#B7C0CC", px=14))
        self.close_btn.setIconSize(_QSize(14, 14))
        self.close_btn.setFlat(True)
        self.close_btn.setToolTip("Close trace drawer")
        self.close_btn.clicked.connect(self.close)

        header = QHBoxLayout()
        header.setContentsMargins(14, 10, 10, 10)
        header.setSpacing(10)
        header.addWidget(self.header_title)
        header.addStretch(1)
        header.addWidget(self.live_badge)
        header.addWidget(self.close_btn)

        # ---- Body slot (a TraceView re-parented in by MainWindow)
        self.body = body
        body.setParent(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(header)
        layout.addWidget(self.body, 1)

        # ---- Slide animation. House curve = cubic-bezier(0.2, 0, 0, 1).
        # set_reduced_motion(True) bypasses the animation and snaps.
        self._anim = QPropertyAnimation(self, b"_animWidth", self)
        self._anim.setDuration(DUR_SLOW)
        self._anim.setEasingCurve(house_curve())

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
        self._start_pulse()
        self.opened.emit()

    def close(self) -> None:
        if not self._open:
            return
        self._open = False
        self._animate_to(0)
        self._stop_pulse()
        self.closed.emit()

    def toggle(self) -> None:
        self.close() if self._open else self.open()

    # ------------------------------------------------------------------
    def set_reduced_motion(self, on: bool) -> None:
        """Honour the prefers-reduced-motion gate. Stops loops and snaps
        the slide animation so future opens/closes are instantaneous."""
        self._reduced_motion = on
        if on:
            self._anim.stop()
            self._stop_pulse()
            self._live_effect.setOpacity(1.0)
        elif self._open:
            self._start_pulse()

    # ------------------------------------------------------------------
    def _animate_to(self, target: int) -> None:
        self._anim.stop()
        if self._reduced_motion:
            self._set_anim_w(target)
            return
        self._anim.setStartValue(self._anim_w_value)
        self._anim.setEndValue(target)
        self._anim.start()

    def _start_pulse(self) -> None:
        if self._reduced_motion:
            return
        if self._live_anim.state() != QPropertyAnimation.State.Running:
            self._live_anim.start()

    def _stop_pulse(self) -> None:
        self._live_anim.stop()
        self._live_effect.setOpacity(1.0)
