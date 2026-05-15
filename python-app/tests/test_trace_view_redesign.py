from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QApplication = QtWidgets.QApplication
_APP = QApplication.instance()
if _APP is None:
    _APP = QApplication([])

from noc_beam.ui.trace_view import TraceMsgRow, _Msg  # noqa: E402


def test_trace_msg_row_has_table_like_cells() -> None:
    msg = _Msg(
        ts=1.0,
        direction="RX",
        peer="sip:alice@example.com",
        body="SIP/2.0 180 Ringing\r\nCall-ID: abc",
        when="12:00:01",
        summary="SIP/2.0 180 Ringing",
        is_error=False,
        chip="180",
        chip_level="progress",
    )
    row = TraceMsgRow(msg)

    try:
        assert row.objectName() == "TraceMsgRow"
        assert row.property("dir") == "rx"
        assert row.findChild(QtWidgets.QLabel, "TraceMsgTime") is not None
        assert row.findChild(QtWidgets.QLabel, "TraceMsgDir") is not None
        assert row.findChild(QtWidgets.QLabel, "TraceMsgSummary") is not None
    finally:
        row.close()
