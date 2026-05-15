from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from noc_beam.ui.design_tokens import ICON_BUTTON_SIZE


def sip_level(code: int | None) -> str:
    if code is None:
        return "muted"
    if 100 <= code < 200:
        return "progress"
    if 200 <= code < 300:
        return "ok"
    if 300 <= code < 400:
        return "warn"
    if code >= 400:
        return "danger"
    return "muted"


class StatusPill(QLabel):
    def __init__(self, text: str, level: str = "muted", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("StatusPill")
        self.setProperty("level", level)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAccessibleName(f"Status: {text}")


class SipCodeBadge(QLabel):
    def __init__(
        self,
        code: int | None,
        reason: str = "",
        parent: QWidget | None = None,
    ) -> None:
        text = "" if code is None else str(code)
        super().__init__(text, parent)
        self.setObjectName("SipCodeBadge")
        self.setProperty("level", sip_level(code))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if code is not None:
            label = f"{code} {reason}".strip()
            self.setToolTip(label)
            self.setAccessibleName(f"SIP code {label}")


class MetricChip(QLabel):
    def __init__(self, text: str, level: str = "muted", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("MetricChip")
        self.setProperty("level", level)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAccessibleName(text)


class IconActionButton(QToolButton):
    def __init__(self, tooltip: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("IconActionButton")
        self.setFixedSize(ICON_BUTTON_SIZE, ICON_BUTTON_SIZE)
        self.setToolTip(tooltip)
        self.setAccessibleName(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class SectionHeader(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text.upper(), parent)
        self.setObjectName("SectionHeader")


class FormSection(QFrame):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("FormSection")
        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(8)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(SectionHeader(title, self))
        layout.addLayout(self.body)


class FooterActionBar(QFrame):
    def __init__(
        self,
        primary_text: str,
        secondary_text: str = "Cancel",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("FooterActionBar")
        self.secondary_button = QPushButton(secondary_text, self)
        self.secondary_button.setObjectName("SecondaryAction")
        self.primary_button = QPushButton(primary_text, self)
        self.primary_button.setObjectName("PrimaryAction")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        layout.addStretch(1)
        layout.addWidget(self.secondary_button)
        layout.addWidget(self.primary_button)
