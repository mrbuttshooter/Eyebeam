"""Calls destination -- idle hero + active call view + multi-call view.

Three layouts in a `QStackedLayout`:
  - Idle  : hero block (Ready / No active calls / active account meta) + dialpad
  - Active: compact call list on top + the existing CallWidget below + dialpad
  - Multi : same as active for now (Tier-3 swaps in callstrips)

The active state is driven from the outside via `set_state()`. MainWindow
calls it from the existing call_added / call_removed handlers based on the
CallManager record count -- 0 = idle, 1 = active, >=2 = multi.

The dialpad and call_widget are passed in by MainWindow (they keep the
existing slots wired). This module only owns the hero block + the
QStackedLayout layout.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from noc_beam.ui.rail_icons import rail_icon


# State indices -- public so MainWindow can read them as constants.
IDLE = 0
ACTIVE = 1
MULTI = 2


class _Hero(QFrame):
    """Idle-state hero card: Ready glyph + title + meta line."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("CallsHero")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(132)

        # Render the check via QSvgRenderer instead of a unicode glyph so the
        # icon stays sharp at any DPI and won't get auto-emoji-ed by Windows.
        self.glyph = QLabel(self)
        self.glyph.setObjectName("HeroGlyph")
        self.glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.glyph.setPixmap(rail_icon("check", color="#66D19E", px=28).pixmap(28, 28))

        self.state_label = QLabel("READY", self)
        self.state_label.setObjectName("HeroState")

        self.title = QLabel("No active calls", self)
        self.title.setObjectName("HeroTitle")

        self.meta = QLabel("", self)
        self.meta.setObjectName("HeroMeta")
        self.meta.setText("")  # populated by set_meta

        body = QVBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(4)
        body.addWidget(self.state_label)
        body.addWidget(self.title)
        body.addWidget(self.meta)
        body.addStretch(1)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(26, 22, 26, 22)
        outer.setSpacing(22)
        outer.addWidget(self.glyph, 0, Qt.AlignmentFlag.AlignTop)
        outer.addLayout(body, 1)

    def set_meta(self, account_label: str | None, codec: str | None) -> None:
        """Render the muted mono line under the title."""
        bits: list[str] = []
        if account_label:
            bits.append(account_label)
        else:
            bits.append("no account")
        if codec:
            bits.append(codec)
        self.meta.setText("  ·  ".join(bits))


class CallsPage(QWidget):
    """Idle / active / multi states for the Calls destination.

    Composition: each state is its own QWidget inside a QStackedLayout.
    The dialpad lives in a fixed right column shared across all states
    (MainWindow only constructs one dialpad; this page re-parents it on
    demand if the layout needs to move it).
    """

    def __init__(
        self,
        dialpad: QWidget,
        call_list: QWidget,
        call_widget: QWidget,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._dialpad = dialpad
        self._call_list = call_list
        self._call_widget = call_widget
        self._meta_provider: Callable[[], tuple[str | None, str | None]] | None = None

        # Right-column dialpad holder is shared visual furniture; re-used
        # across the three state layouts via reparenting. Wrapping it in a
        # holder widget makes the reparent atomic.
        self._dialpad_holder = QWidget(self)
        dl = QVBoxLayout(self._dialpad_holder)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.setSpacing(0)
        dl.addWidget(self._dialpad)
        dl.addStretch(1)
        self._dialpad_holder.setMaximumWidth(320)

        # Hero (idle) widget.
        self.hero = _Hero(self)

        # Build the three pages.
        self._idle_page = self._build_idle_page()
        self._active_page = self._build_active_page()
        # Multi shares the active layout for Tier-2; Tier-3 will replace.
        self._multi_page = self._active_page

        self._stack = QStackedLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._stack.addWidget(self._idle_page)
        self._stack.addWidget(self._active_page)
        # Multi index intentionally points at the same widget instance as
        # active -- QStackedLayout supports duplicates by index.
        # Placeholder kept so the index map matches the IDLE/ACTIVE/MULTI
        # constants above without a separate mapping.
        self._stack.addWidget(QWidget())  # MULTI = 2 -- swapped in set_state

        self._state = IDLE

    # ------------------------------------------------------------------
    def _build_idle_page(self) -> QWidget:
        page = QWidget()
        outer = QHBoxLayout(page)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(20)

        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(16)
        left.addWidget(self.hero)
        left.addStretch(1)
        outer.addLayout(left, 1)

        # Right column gets the dialpad holder (parent-swap each time we
        # build a layout -- only one of the three layouts is parented at
        # a time so there's no aliasing).
        outer.addWidget(self._dialpad_holder)
        return page

    def _build_active_page(self) -> QWidget:
        page = QWidget()
        outer = QHBoxLayout(page)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(20)

        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(8)
        left.addWidget(self._call_list)
        left.addWidget(self._call_widget, 1)
        outer.addLayout(left, 1)
        return page

    # ------------------------------------------------------------------
    def set_meta_provider(
        self, provider: Callable[[], tuple[str | None, str | None]]
    ) -> None:
        """MainWindow supplies a callback returning (account_label, codec)
        for the idle hero meta line. Called whenever set_state(IDLE)."""
        self._meta_provider = provider

    def set_state(self, state: int) -> None:
        if state not in (IDLE, ACTIVE, MULTI):
            return
        self._state = state
        # Move the dialpad holder into the right slot before swapping pages.
        # Idle keeps the dialpad in its right column; active hides it (the
        # user is in a call, the dialpad collapses to make room).
        if state == IDLE:
            self._idle_page.layout().addWidget(self._dialpad_holder)
            self._dialpad_holder.show()
            if self._meta_provider is not None:
                acc, codec = self._meta_provider()
                self.hero.set_meta(acc, codec)
        else:
            # Hide dialpad; active call surface gets the full width.
            self._dialpad_holder.hide()
        self._stack.setCurrentIndex(state)

    @property
    def state(self) -> int:
        return self._state
