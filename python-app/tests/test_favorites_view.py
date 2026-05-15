"""Qt smoke tests for contacts-backed Favorites view."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

QtCore = pytest.importorskip("PySide6.QtCore")
QtTest = pytest.importorskip("PySide6.QtTest")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QApplication = QtWidgets.QApplication
QLabel = QtWidgets.QLabel
QToolButton = QtWidgets.QToolButton
Qt = QtCore.Qt
QTest = QtTest.QTest
_APP = QApplication.instance()
if _APP is None:
    _APP = QApplication([])

from noc_beam.config import contacts
from noc_beam.ui.favorites_view import FavoriteRow, FavoritesView


@pytest.fixture
def qt_app() -> QApplication:
    return _APP


@pytest.fixture(autouse=True)
def isolated_contacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(contacts, "contacts_file", lambda: tmp_path / "contacts.json")
    yield


def _favorite_names(view: FavoritesView) -> list[str]:
    return [
        row.contact.name
        for row in view.findChildren(FavoriteRow)
        if row.isVisible()
    ]


def test_startup_loads_existing_favorite_contacts(qt_app: QApplication) -> None:
    rows: list[contacts.Contact] = []
    contacts.add_contact(rows, "Alice", "1001", group="NOC", favorite=True)
    contacts.add_contact(rows, "Bob", "2002", group="NOC", favorite=False)
    contacts.save_contacts(rows)

    view = FavoritesView()
    view.show()
    qt_app.processEvents()

    try:
        labels = [label.text() for label in view.findChildren(QLabel)]
        assert "Alice" in labels
        assert "1001" in labels
        assert "Bob" not in labels
        assert _favorite_names(view) == ["Alice"]
    finally:
        view.close()


def test_favorites_search_filters_by_number(qt_app: QApplication) -> None:
    rows: list[contacts.Contact] = []
    contacts.add_contact(rows, "Alice", "1001", group="NOC", favorite=True)
    contacts.add_contact(rows, "Carol", "3003", group="Ops", favorite=True)
    contacts.save_contacts(rows)
    view = FavoritesView()
    view.show()
    qt_app.processEvents()

    view.search.setText("3003")
    qt_app.processEvents()

    try:
        assert _favorite_names(view) == ["Carol"]
    finally:
        view.close()


def test_favorite_row_double_click_emits_call_requested(qt_app: QApplication) -> None:
    rows: list[contacts.Contact] = []
    contacts.add_contact(rows, "Alice", "1001", group="NOC", favorite=True)
    contacts.save_contacts(rows)
    view = FavoritesView()
    view.show()
    qt_app.processEvents()
    emitted: list[str] = []
    view.call_requested.connect(emitted.append)

    row = view.findChildren(FavoriteRow)[0]
    QTest.mouseDClick(row, Qt.MouseButton.LeftButton)
    qt_app.processEvents()

    try:
        assert emitted == ["1001"]
    finally:
        view.close()


def test_favorite_call_button_emits_call_requested(qt_app: QApplication) -> None:
    rows: list[contacts.Contact] = []
    contacts.add_contact(rows, "Alice", "1001", group="NOC", favorite=True)
    contacts.save_contacts(rows)
    view = FavoritesView()
    view.show()
    qt_app.processEvents()
    emitted: list[str] = []
    view.call_requested.connect(emitted.append)

    row = view.findChildren(FavoriteRow)[0]
    call_btn = next(
        button for button in row.findChildren(QToolButton)
        if button.toolTip() == "Call"
    )
    QTest.mouseClick(call_btn, Qt.MouseButton.LeftButton)
    qt_app.processEvents()

    try:
        assert emitted == ["1001"]
    finally:
        view.close()
