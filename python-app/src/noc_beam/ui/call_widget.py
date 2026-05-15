"""Active-call display + in-call controls.

Matches mockup panel 2: a rounded card containing an avatar circle,
the peer info (number + display name), a status pill (e.g. "200 OK"
green) and duration counter; below the card a row of in-call action
buttons with End Call rendered ~2× wider than the secondary controls.
"""
from __future__ import annotations

import time

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def _split_peer(remote: str) -> tuple[str, str]:
    """Split a SIP URI / display string into (number-or-uri, friendly-name).

    Best-effort: ``"Alice East" <sip:+1...@host>`` → ("+1...", "Alice East");
    bare ``"sip:+1...@host"`` → ("+1...@host", "+1..."); a plain number stays
    as the headline with an empty subtitle.
    """
    if not remote:
        return ("", "")
    s = remote.strip()
    # "Alice East" <sip:...>
    name = ""
    uri = s
    if s.startswith('"') or s[0:1] == '<':
        # Try to peel out a quoted display name.
        if '<' in s and '>' in s:
            name_part, _, rest = s.partition('<')
            uri = rest.rstrip('>')
            name = name_part.strip().strip('"').strip()
    elif '<' in s and '>' in s:
        name_part, _, rest = s.partition('<')
        if name_part.strip():
            name = name_part.strip().strip('"').strip()
        uri = rest.rstrip('>')
    if uri.startswith("sip:"):
        uri = uri[4:]
    elif uri.startswith("sips:"):
        uri = uri[5:]
    user, _, host = uri.partition("@")
    headline = user or uri
    if not name:
        name = host or ""
    return (headline.strip(), name.strip())


class CallWidget(QWidget):
    answer_clicked = Signal(int)
    reject_clicked = Signal(int)
    hangup_clicked = Signal(int)
    hold_clicked = Signal(int)
    resume_clicked = Signal(int)
    mute_toggled = Signal(int, bool)
    transfer_clicked = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("CallWidget")
        self.setProperty("state", "idle")

        self.call_id = -1
        self._on_hold = False
        self._connected_at: float | None = None

        # ----- Card -------------------------------------------------------
        self._card = QFrame(self)
        self._card.setObjectName("CallCard")

        # Avatar circle (green pill with a glyph; the mock uses a
        # headphones/handset icon -- a unicode ☎ reads similarly without
        # adding image assets).
        self._avatar = QLabel("☎", self._card)
        self._avatar.setObjectName("CallAvatar")
        self._avatar.setFixedSize(32, 32)
        self._avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Peer block: headline (number / SIP user) on top, secondary
        # display name below in muted small text.
        self.peer_label = QLabel("", self._card)
        self.peer_label.setObjectName("CallPeer")
        self.peer_sub_label = QLabel("", self._card)
        self.peer_sub_label.setObjectName("CallPeerSub")
        peer_col = QVBoxLayout()
        peer_col.setContentsMargins(0, 0, 0, 0)
        peer_col.setSpacing(2)
        peer_col.addWidget(self.peer_label)
        peer_col.addWidget(self.peer_sub_label)

        # Right column: status pill on top, duration timer below.
        self.state_label = QLabel("", self._card)
        self.state_label.setObjectName("CallStatePill")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.duration_label = QLabel("", self._card)
        self.duration_label.setObjectName("CallDuration")
        self.duration_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        right_col = QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(4)
        right_col.addWidget(self.state_label, 0, Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(self.duration_label)

        card_row = QHBoxLayout(self._card)
        card_row.setContentsMargins(10, 6, 10, 6)
        card_row.setSpacing(10)
        card_row.addWidget(self._avatar, 0, Qt.AlignmentFlag.AlignVCenter)
        card_row.addLayout(peer_col, 1)
        card_row.addLayout(right_col, 0)

        # Codec + quality live below the card as a single muted line so
        # the card stays clean and the technical bits are still visible.
        self.codec_label = QLabel("", self)
        self.codec_label.setObjectName("CallCodec")
        self.quality_label = QLabel("", self)
        self.quality_label.setObjectName("CallQuality")
        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(4, 0, 4, 0)
        meta_row.setSpacing(8)
        meta_row.addWidget(self.codec_label)
        meta_row.addStretch(1)
        meta_row.addWidget(self.quality_label)

        # ----- Buttons --------------------------------------------------
        self.answer_btn = QPushButton("Answer")
        self.answer_btn.setObjectName("CallButton")
        self.answer_btn.setAccessibleName("Answer incoming call")
        self.reject_btn = QPushButton("Reject")
        self.reject_btn.setObjectName("RejectButton")
        self.reject_btn.setAccessibleName("Reject incoming call")
        self.hangup_btn = QPushButton("End Call")
        self.hangup_btn.setObjectName("EndCallButton")
        self.hangup_btn.setAccessibleName("End active call")
        self.hold_btn = QPushButton("Hold")
        self.hold_btn.setObjectName("CallControlButton")
        self.mute_btn = QPushButton("Mute")
        self.mute_btn.setObjectName("CallControlButton")
        self.mute_btn.setCheckable(True)
        self.speaker_btn = QPushButton("Speaker")
        self.speaker_btn.setObjectName("CallControlButton")
        self.speaker_btn.setCheckable(True)
        self.transfer_btn = QPushButton("Transfer")
        self.transfer_btn.setObjectName("CallControlButton")
        for _b in (self.answer_btn, self.reject_btn, self.hangup_btn,
                   self.speaker_btn, self.hold_btn, self.mute_btn, self.transfer_btn):
            _b.setMinimumHeight(28)

        # Wire to outbound signals (unchanged contract).
        self.answer_btn.clicked.connect(lambda: self.answer_clicked.emit(self.call_id))
        self.reject_btn.clicked.connect(lambda: self.reject_clicked.emit(self.call_id))
        self.hangup_btn.clicked.connect(lambda: self.hangup_clicked.emit(self.call_id))
        self.hold_btn.clicked.connect(self._on_hold_clicked)
        self.mute_btn.toggled.connect(lambda b: self.mute_toggled.emit(self.call_id, b))
        self.transfer_btn.clicked.connect(lambda: self.transfer_clicked.emit(self.call_id))

        # Active-call row: Mute / Speaker / Hold / Transfer / END CALL (2x).
        # Stretch factors: each secondary = 1, End Call = 2.
        self._active_row = QHBoxLayout()
        self._active_row.setContentsMargins(0, 0, 0, 0)
        self._active_row.setSpacing(6)
        self._active_row.addWidget(self.mute_btn, 1)
        self._active_row.addWidget(self.speaker_btn, 1)
        self._active_row.addWidget(self.hold_btn, 1)
        self._active_row.addWidget(self.transfer_btn, 1)
        self._active_row.addWidget(self.hangup_btn, 2)

        # Incoming-call row: big Reject + big Answer (Reject is red, Answer
        # is green, equal weight). Hidden until needed.
        self._incoming_row = QHBoxLayout()
        self._incoming_row.setContentsMargins(0, 0, 0, 0)
        self._incoming_row.setSpacing(8)
        self._incoming_row.addWidget(self.reject_btn, 1)
        self._incoming_row.addWidget(self.answer_btn, 1)

        # We stack the two row layouts so we can swap by visibility.
        self._active_row_widget = QWidget(self)
        self._active_row_widget.setLayout(self._active_row)
        self._incoming_row_widget = QWidget(self)
        self._incoming_row_widget.setLayout(self._incoming_row)
        self._incoming_row_widget.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)
        layout.addWidget(self._card)
        layout.addLayout(meta_row)
        layout.addWidget(self._active_row_widget)
        layout.addWidget(self._incoming_row_widget)
        layout.addStretch(0)

        # Tick once a second while connected to update duration.
        self._duration_timer = QTimer(self)
        self._duration_timer.setInterval(1000)
        self._duration_timer.timeout.connect(self._tick_duration)

        self.show_idle()

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------
    def show_idle(self) -> None:
        self.call_id = -1
        self._set_peer("", "")
        self.state_label.setText("")
        self.codec_label.setText("")
        self.duration_label.setText("")
        self.quality_label.setText("")
        self._connected_at = None
        self._duration_timer.stop()
        self._set_state("idle")
        self._set_active_row(True)   # default to active layout when not idle
        for b in (self.answer_btn, self.reject_btn, self.hangup_btn,
                  self.hold_btn, self.mute_btn, self.transfer_btn,
                  self.speaker_btn):
            b.setEnabled(False)

    def show_outgoing(self, call_id: int, target: str) -> None:
        self.call_id = call_id
        headline, sub = _split_peer(target)
        self._set_peer(headline or target, sub or "Outgoing call")
        self.state_label.setText("Calling…")
        self.state_label.setProperty("level", "progress")
        self.codec_label.setText("")
        self.duration_label.setText("00:00")
        self._set_active_row(True)
        self.hangup_btn.setEnabled(True)
        self.mute_btn.setEnabled(False)
        self.speaker_btn.setEnabled(False)
        self.hold_btn.setEnabled(False)
        self.transfer_btn.setEnabled(False)
        self._set_state("outgoing")

    def show_incoming(self, call_id: int, remote: str) -> None:
        self.call_id = call_id
        headline, sub = _split_peer(remote)
        self._set_peer(headline or remote, sub or "Incoming call")
        self.state_label.setText("RINGING")
        self.state_label.setProperty("level", "progress")
        self.codec_label.setText("")
        self.duration_label.setText("")
        self._set_active_row(False)   # show Reject + Answer
        self.answer_btn.setEnabled(True)
        self.reject_btn.setEnabled(True)
        self.hangup_btn.setEnabled(False)
        self.hold_btn.setEnabled(False)
        self.mute_btn.setEnabled(False)
        self.speaker_btn.setEnabled(False)
        self._set_state("incoming")

    def update_state(self, state_name: str, code: int, reason: str) -> None:
        # Right-side pill: code + short text, e.g. "200 OK".
        if code:
            pill = f"{code} {reason}".strip()
        else:
            pill = state_name.title()
        self.state_label.setText(pill)
        self._on_hold = state_name == "HELD"
        self.hold_btn.setText("Resume" if self._on_hold else "Hold")

        # Update level for state pill colouring.
        if 200 <= code < 300:
            self.state_label.setProperty("level", "ok")
        elif 100 <= code < 200:
            self.state_label.setProperty("level", "progress")
        elif code in (401, 407):
            self.state_label.setProperty("level", "auth")
        elif 400 <= code < 600:
            self.state_label.setProperty("level", "error")
        else:
            self.state_label.setProperty("level", "muted")
        self.state_label.style().unpolish(self.state_label)
        self.state_label.style().polish(self.state_label)

        if state_name == "INCOMING":
            self._set_state("incoming")
            self._set_active_row(False)
        elif state_name in ("CONFIRMED", "HELD"):
            self._set_state("active")
            self._set_active_row(True)
        elif state_name == "DISCONNECTED":
            self._set_state("idle")
        else:
            self._set_state("outgoing")
            self._set_active_row(True)

        in_call = state_name in ("CONFIRMED", "HELD")
        self.hold_btn.setEnabled(in_call)
        self.mute_btn.setEnabled(in_call)
        self.speaker_btn.setEnabled(in_call)
        self.transfer_btn.setEnabled(in_call)
        self.hangup_btn.setEnabled(state_name != "DISCONNECTED")

        if state_name == "CONFIRMED":
            if self._connected_at is None:
                self._connected_at = time.time()
            if not self._duration_timer.isActive():
                self._duration_timer.start()
            self._tick_duration()
        elif state_name == "HELD":
            self._tick_duration()
        elif state_name == "DISCONNECTED":
            self._duration_timer.stop()

    def update_quality(self, mos: float, packet_loss_pct: float) -> None:
        bars = self._mos_to_bars(mos)
        glyph = "▮" * bars + "▯" * (4 - bars)
        loss = f"  ⌀ {packet_loss_pct:.1f}%" if packet_loss_pct > 0 else ""
        self.quality_label.setText(f"{glyph}  MOS {mos:.1f}{loss}")

    def update_media(self, codec: str, clock: int, channels: int) -> None:
        if codec:
            chan = f", {channels}ch" if channels and channels > 1 else ""
            self.codec_label.setText(f"Codec: {codec} @ {clock} Hz{chan}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _set_peer(self, headline: str, subtitle: str) -> None:
        self.peer_label.setText(headline)
        self.peer_sub_label.setText(subtitle)
        self.peer_sub_label.setVisible(bool(subtitle))

    def _set_active_row(self, active: bool) -> None:
        self._active_row_widget.setVisible(active)
        self._incoming_row_widget.setVisible(not active)

    def _set_state(self, state: str) -> None:
        self.setProperty("state", state)
        self.style().unpolish(self)
        self.style().polish(self)
        # Card mirrors the same state so QSS can colour the avatar / border.
        self._card.setProperty("state", state)
        self._card.style().unpolish(self._card)
        self._card.style().polish(self._card)

    def _on_hold_clicked(self) -> None:
        if self._on_hold:
            self.resume_clicked.emit(self.call_id)
        else:
            self.hold_clicked.emit(self.call_id)

    def _tick_duration(self) -> None:
        if self._connected_at is None:
            self.duration_label.setText("")
            return
        elapsed = int(time.time() - self._connected_at)
        h, rem = divmod(elapsed, 3600)
        m, s = divmod(rem, 60)
        fmt = f"{h:02d}:{m:02d}:{s:02d}" if h else f"00:{m:02d}:{s:02d}"
        self.duration_label.setText(fmt)

    @staticmethod
    def _mos_to_bars(mos: float) -> int:
        if mos < 2.5:
            return 1
        if mos < 3.1:
            return 2
        if mos < 3.6:
            return 3
        return 4
