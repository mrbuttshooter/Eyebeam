from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QApplication = QtWidgets.QApplication
_APP = QApplication.instance()
if _APP is None:
    _APP = QApplication([])

from noc_beam.ui import call_widget as call_widget_module  # noqa: E402
from noc_beam.ui.call_widget import CallWidget  # noqa: E402


@pytest.fixture
def qt_app() -> QApplication:
    return _APP


def test_outgoing_setup_timer_counts_before_answer(
    qt_app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = 1000.0
    monkeypatch.setattr(call_widget_module.time, "time", lambda: now)
    widget = CallWidget()

    try:
        widget.show_outgoing(7, "sip:0096171488860@208.87.170.99")
        assert widget.state_label.text() == "Calling\u2026"
        assert widget.duration_label.text() == "00:00"

        now = 1005.0
        widget._tick_duration()

        assert widget.duration_label.text() == "00:00:05"
    finally:
        widget.close()


def test_outgoing_state_switches_from_calling_to_ringing(
    qt_app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = 2000.0
    monkeypatch.setattr(call_widget_module.time, "time", lambda: now)
    widget = CallWidget()

    try:
        widget.show_outgoing(8, "sip:0035795762492@208.87.170.99")
        widget.update_state("CALLING", 100, "Trying")
        assert widget.state_label.text() == "Calling..."

        now = 2004.0
        widget.update_state("EARLY", 180, "Ringing")

        assert widget.state_label.text() == "Ringing"
        assert widget.duration_label.text() == "00:00:04"
    finally:
        widget.close()


def test_answered_call_timer_restarts_from_confirmed_time(
    qt_app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = 3000.0
    monkeypatch.setattr(call_widget_module.time, "time", lambda: now)
    widget = CallWidget()

    try:
        widget.show_outgoing(9, "sip:0096171488860@208.87.170.99")
        now = 3010.0
        widget.update_state("CONFIRMED", 200, "OK")

        assert widget.duration_label.text() == "00:00:00"

        now = 3016.0
        widget._tick_duration()

        assert widget.duration_label.text() == "00:00:06"
    finally:
        widget.close()
