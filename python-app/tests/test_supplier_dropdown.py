from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from noc_beam.ui.supplier_dropdown import SupplierDropdown

_APP = QApplication.instance()
if _APP is None:
    _APP = QApplication([])


def test_supplier_popup_keeps_typing_after_first_character() -> None:
    widget = SupplierDropdown()
    widget.set_items(
        [
            ("Advise - C327", "327"),
            ("Ibasis (Premium) - C080", "080"),
            ("IConnect - C120", "120"),
        ],
        "327",
    )
    widget.lineEdit().textEdited.connect(widget.set_filter)
    widget.lineEdit().textEdited.connect(lambda _text: widget.showPopup())
    widget.show()
    _APP.processEvents()

    try:
        widget.lineEdit().setFocus(Qt.FocusReason.OtherFocusReason)
        widget.lineEdit().clear()
        QTest.keyClicks(widget.lineEdit(), "iba")
        _APP.processEvents()

        assert widget.lineEdit().text() == "iba"
        assert widget.view().count() == 1
        assert widget.itemData(widget.currentIndex()) == "327"
    finally:
        widget.hidePopup()
        widget.close()


def test_supplier_popup_forwards_keys_if_popup_gets_focus() -> None:
    widget = SupplierDropdown()
    widget.set_items(
        [
            ("Advise - C327", "327"),
            ("Ibasis (Premium) - C080", "080"),
        ],
        "327",
    )
    widget.lineEdit().textEdited.connect(widget.set_filter)
    widget.show()
    widget.showPopup()
    widget.lineEdit().clear()
    widget.view().setFocus(Qt.FocusReason.OtherFocusReason)
    _APP.processEvents()

    try:
        QTest.keyClicks(widget.view(), "iba")
        _APP.processEvents()

        assert widget.lineEdit().text() == "iba"
        assert widget.view().count() == 1
        assert widget.itemData(widget.currentIndex()) == "327"
    finally:
        widget.hidePopup()
        widget.close()
