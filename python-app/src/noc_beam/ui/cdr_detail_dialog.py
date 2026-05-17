"""Modal showing every field of a single CDR plus Redial / Export actions.

Opened from HistoryView when the user double-clicks a row. The export
writes a single-row CSV with all fields so the user can drop it into
ticketing / analytics tools.
"""
from __future__ import annotations

import csv
import time

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from noc_beam.config.history import CdrEntry
from noc_beam.ui.components import StatusPill


def _fmt_ts(ts: float | None) -> str:
    if not ts:
        return "—"
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


def _fmt_duration(seconds: float) -> str:
    if seconds <= 0:
        return "—"
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h:d}:{m:02d}:{sec:02d}"
    return f"{m:d}:{sec:02d}"


def _direction_label(entry: CdrEntry) -> str:
    if entry.direction == "in":
        return "Incoming (answered)" if entry.was_answered else "Incoming (missed)"
    return "Outgoing (answered)" if entry.was_answered else "Outgoing (failed)"


class CdrDetailDialog(QDialog):
    """Single-CDR detail view. Emits redial_requested(peer_uri) on Redial."""

    redial_requested = Signal(str)

    def __init__(self, entry: CdrEntry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._entry = entry
        self.setObjectName("CdrDetailDialog")
        self.setWindowTitle("Call detail")
        self.setMinimumWidth(420)

        # Header: peer URI big + direction underneath
        peer_lbl = QLabel(entry.peer_uri or "Unknown peer")
        peer_lbl.setObjectName("CdrDetailPeer")
        peer_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        if entry.was_answered:
            level = "ok"
        elif entry.direction == "in":
            level = "danger"
        else:
            level = "warn"
        direction_lbl = StatusPill(_direction_label(entry), level, self)

        # Field grid
        form = QFormLayout()
        form.setSpacing(6)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        for label, value in (
            ("Call ID", str(entry.call_id)),
            ("Account",  entry.account_id or "—"),
            ("Started",  _fmt_ts(entry.started_at)),
            ("Connected", _fmt_ts(entry.connected_at) if entry.connected_at else "—"),
            ("Ended",    _fmt_ts(entry.ended_at)),
            ("Duration", _fmt_duration(entry.duration_s)),
            ("End code", f"{entry.end_code} {entry.end_reason}".strip() or "—"),
            ("Codec",    entry.codec or "—"),
        ):
            v = QLabel(value)
            v.setObjectName("CdrDetailValue")
            v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            v.setWordWrap(True)
            form.addRow(label, v)

        # FAS analysis (shown only when a verdict was captured at end-of-call).
        self._fas_section_widgets: list = []
        fas_verdict = getattr(entry, "fas_verdict", "") or ""
        if fas_verdict:
            from noc_beam.ui.components import FasBadge

            fas_header = QLabel("FAS Analysis")
            fas_header.setObjectName("CdrDetailSectionHeader")
            self._fas_section_widgets.append(fas_header)

            fas_badge = FasBadge(fas_verdict, self)
            fas_badge.update_verdict(
                fas_verdict,
                float(getattr(entry, "fas_confidence", 0.0) or 0.0),
                getattr(entry, "fas_reasons", "") or "",
            )

            fas_form = QFormLayout()
            fas_form.setSpacing(6)
            fas_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
            fas_form.addRow("Verdict:", fas_badge)
            conf = float(getattr(entry, "fas_confidence", 0.0) or 0.0)
            conf_lbl = QLabel(f"{conf:.0%}")
            conf_lbl.setObjectName("CdrDetailValue")
            fas_form.addRow("Confidence:", conf_lbl)
            reasons = getattr(entry, "fas_reasons", "") or "—"
            reasons_lbl = QLabel(reasons)
            reasons_lbl.setObjectName("CdrDetailValue")
            reasons_lbl.setWordWrap(True)
            reasons_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            fas_form.addRow("Signals:", reasons_lbl)
            self._fas_section_widgets.append(fas_form)

        # Action row: Redial (left) + Export CSV (right) + Close
        self.redial_btn = QPushButton("Redial")
        self.redial_btn.setObjectName("PrimaryAction")
        self.redial_btn.setEnabled(bool(entry.peer_uri))
        self.redial_btn.clicked.connect(self._on_redial)

        self.export_btn = QPushButton("Export CSV…")
        self.export_btn.clicked.connect(self._on_export)

        actions = QHBoxLayout()
        actions.addWidget(self.redial_btn)
        actions.addWidget(self.export_btn)
        actions.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(peer_lbl)
        layout.addWidget(direction_lbl)
        layout.addSpacing(8)
        layout.addLayout(form)
        # Inject FAS Analysis section below the field grid when present.
        for item in self._fas_section_widgets:
            layout.addSpacing(8)
            if hasattr(item, "addRow"):
                layout.addLayout(item)
            else:
                layout.addWidget(item)
        layout.addSpacing(8)
        layout.addLayout(actions)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------
    def _on_redial(self) -> None:
        if self._entry.peer_uri:
            self.redial_requested.emit(self._entry.peer_uri)
            self.accept()

    @staticmethod
    def _csv_safe(value):
        """Prefix `'` when a CSV field starts with a character Excel/Sheets
        would interpret as a formula trigger. A malicious caller-id
        (peer_uri=`=cmd|...`) becomes a live formula on open otherwise --
        classic CSV-injection vector. Per OWASP CSV-injection guidance."""
        if value is None:
            return ""
        s = str(value)
        if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
            return "'" + s
        return s

    def _on_export(self) -> None:
        default_name = f"cdr-{self._entry.call_id}-{int(self._entry.ended_at)}.csv"
        path, _filter = QFileDialog.getSaveFileName(
            self, "Export CDR", default_name, "CSV (*.csv);;All Files (*.*)"
        )
        if not path:
            return
        safe = self._csv_safe
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "call_id", "account_id", "peer_uri", "direction",
                    "started_at", "connected_at", "ended_at",
                    "duration_s", "end_code", "end_reason", "codec",
                ])
                writer.writerow([
                    self._entry.call_id,
                    safe(self._entry.account_id),
                    safe(self._entry.peer_uri),
                    safe(self._entry.direction),
                    _fmt_ts(self._entry.started_at),
                    _fmt_ts(self._entry.connected_at) if self._entry.connected_at else "",
                    _fmt_ts(self._entry.ended_at),
                    f"{self._entry.duration_s:.1f}",
                    self._entry.end_code,
                    safe(self._entry.end_reason),
                    safe(self._entry.codec),
                ])
            QMessageBox.information(self, "Export CDR", f"Saved CDR to:\n{path}")
        except Exception as exc:
            QMessageBox.warning(self, "Export CDR", f"Could not write file:\n{exc}")
