# NOC_Beam Full UI Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the existing NOC_Beam Qt UI into a premium Windows NOC operator console while preserving SIP, account persistence, contacts, history, trace, and Test Runner internals.

**Architecture:** Add a small shared UI foundation for tokens, common widgets, and theme verification, then rebuild each visible surface around those primitives. Existing domain services remain the source of truth; UI classes call current stores, SIP endpoint APIs, and runner APIs rather than duplicating backend behavior.

**Tech Stack:** Python 3, PySide6, Qt QSS themes, pytest, pytest-qt where available, PyInstaller packaging scripts already present in the repository.

---

## File Structure Map

Create:

- `python-app/src/noc_beam/ui/design_tokens.py`: shared semantic sizes, object names, color role names, and theme metadata used by widgets and tests.
- `python-app/src/noc_beam/ui/components.py`: reusable Qt widgets/helpers: `StatusPill`, `SipCodeBadge`, `IconActionButton`, `MetricChip`, `SectionHeader`, `FormSection`, `FooterActionBar`, and row helpers.
- `python-app/tests/test_ui_components.py`: focused tests for the shared widgets and theme object names.
- `python-app/tests/test_ui_theme_contract.py`: tests that light, dark, and high-contrast QSS contain required selectors and focus states.
- `python-app/tests/test_phone_shell_redesign.py`: smoke tests for shell construction, width, navigation, and critical object names.
- `python-app/tests/test_trace_view_redesign.py`: trace grouping/density/selector smoke tests.
- `python-app/tests/test_dialog_redesign.py`: account/settings/contact dialog object-name and validation smoke tests.
- `python-app/tests/test_ui_accessibility_contract.py`: accessible names, keyboard focus, and no color-only state smoke tests.
- `python-app/tools/ui_smoke.py`: optional local screenshot/smoke harness for source app pages and themes.

Modify:

- `python-app/src/noc_beam/ui/resources/light.qss`: rebuilt light theme selectors.
- `python-app/src/noc_beam/ui/resources/dark.qss`: rebuilt dark theme selectors in lockstep with light.
- `python-app/src/noc_beam/ui/resources/dark-hc.qss`: rebuilt high-contrast selectors in lockstep with light and dark.
- `python-app/src/noc_beam/ui/theme.py`: expose required theme names and helper used by tests.
- `python-app/src/noc_beam/ui/phone_shell.py`: new shell width, top status strip, navigation, and page composition.
- `python-app/src/noc_beam/ui/bottom_tabs.py`: flatter compact bottom navigation.
- `python-app/src/noc_beam/ui/audio_strip.py`: compact operator status strip styling and accessible labels.
- `python-app/src/noc_beam/ui/call_widget.py`: active-call hierarchy and compact controls.
- `python-app/src/noc_beam/ui/dialpad.py`: compact keypad dimensions and labels.
- `python-app/src/noc_beam/ui/quick_dial.py`: dense recent/quick row styling.
- `python-app/src/noc_beam/ui/contacts_view.py`: dense grouped Contacts plus form-section dialog.
- `python-app/src/noc_beam/ui/favorites_view.py`: same row system as Contacts.
- `python-app/src/noc_beam/ui/history_view.py`: grouped dense rows with result badges and fixed action column.
- `python-app/src/noc_beam/ui/cdr_detail_dialog.py`: match dialog footer/form system.
- `python-app/src/noc_beam/ui/trace_view.py`: table-like grouped Trace rows.
- `python-app/src/noc_beam/ui/settings_dialog.py`: split rail/form layout.
- `python-app/src/noc_beam/ui/account_dialog.py`: split rail/form layout plus inline validation.
- `python-app/src/noc_beam/ui/account_settings_dialog.py`: align with account/settings form system where still used.
- `python-app/src/noc_beam/ui/test_runner_view.py`: operational toolbar/results-grid redesign.

Do not modify backend SIP/account/history/test-runner semantics except where a UI test reveals an existing UI integration bug.

---

### Task 1: UI Foundation And Theme Contract

**Files:**
- Create: `python-app/src/noc_beam/ui/design_tokens.py`
- Create: `python-app/src/noc_beam/ui/components.py`
- Create: `python-app/tests/test_ui_components.py`
- Create: `python-app/tests/test_ui_theme_contract.py`
- Modify: `python-app/src/noc_beam/ui/theme.py`
- Modify: `python-app/src/noc_beam/ui/resources/light.qss`
- Modify: `python-app/src/noc_beam/ui/resources/dark.qss`
- Modify: `python-app/src/noc_beam/ui/resources/dark-hc.qss`

- [ ] **Step 1: Write component tests**

Add `python-app/tests/test_ui_components.py`:

```python
from PySide6.QtWidgets import QApplication

from noc_beam.ui.components import FooterActionBar, SipCodeBadge, StatusPill


def test_status_pill_exposes_text_level_and_accessible_name(qtbot):
    pill = StatusPill("Registered", "ok")
    qtbot.addWidget(pill)

    assert pill.text() == "Registered"
    assert pill.objectName() == "StatusPill"
    assert pill.property("level") == "ok"
    assert "Registered" in pill.accessibleName()


def test_sip_code_badge_uses_fixed_level_and_tooltip(qtbot):
    badge = SipCodeBadge(180, "Ringing")
    qtbot.addWidget(badge)

    assert badge.text() == "180"
    assert badge.objectName() == "SipCodeBadge"
    assert badge.property("level") == "progress"
    assert badge.toolTip() == "180 Ringing"


def test_footer_action_bar_keeps_primary_last(qtbot):
    bar = FooterActionBar(primary_text="Save", secondary_text="Cancel")
    qtbot.addWidget(bar)

    buttons = bar.findChildren(type(bar.primary_button))
    assert bar.primary_button.text() == "Save"
    assert bar.secondary_button.text() == "Cancel"
    assert buttons[-1] is bar.primary_button
```

- [ ] **Step 2: Write theme contract tests**

Add `python-app/tests/test_ui_theme_contract.py`:

```python
from noc_beam.ui.theme import REQUIRED_THEME_SELECTORS, load_theme_qss


def test_all_themes_define_required_redesign_selectors():
    themes = [
        ("light", False),
        ("dark", False),
        ("light", True),
    ]

    for theme, high_contrast in themes:
        qss = load_theme_qss(theme=theme, high_contrast=high_contrast)
        assert qss
        for selector in REQUIRED_THEME_SELECTORS:
            assert selector in qss, f"{selector} missing from {theme} hc={high_contrast}"


def test_all_themes_include_visible_focus_states():
    for theme, high_contrast in [("light", False), ("dark", False), ("light", True)]:
        qss = load_theme_qss(theme=theme, high_contrast=high_contrast)
        assert ":focus" in qss
        assert "FocusRing" in qss or "focus" in qss.lower()
```

- [ ] **Step 3: Run tests and verify failure**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest tests/test_ui_components.py tests/test_ui_theme_contract.py -q
```

Expected: FAIL because `noc_beam.ui.components` and `REQUIRED_THEME_SELECTORS` do not exist yet.

- [ ] **Step 4: Add design tokens**

Create `python-app/src/noc_beam/ui/design_tokens.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


SPACING_UNIT = 4
RADIUS_SM = 4
RADIUS_MD = 6
BOTTOM_NAV_HEIGHT = 48
ICON_BUTTON_SIZE = 28
PRIMARY_BUTTON_HEIGHT = 32
COMPACT_INPUT_HEIGHT = 32


STATUS_LEVELS = {
    "ok": "ok",
    "progress": "progress",
    "warn": "warn",
    "danger": "danger",
    "info": "info",
    "muted": "muted",
    "running": "running",
}


@dataclass(frozen=True)
class ThemeRole:
    name: str
    meaning: str


THEME_ROLES = (
    ThemeRole("brand", "NOC_Beam mark and active navigation"),
    ThemeRole("ok", "registered, pass, call, SIP 200"),
    ThemeRole("progress", "ringing, pending, SIP 180"),
    ThemeRole("danger", "fail, missed, error"),
    ThemeRole("info", "trace and metadata"),
    ThemeRole("muted", "idle, disabled, secondary text"),
)
```

- [ ] **Step 5: Add reusable components**

Create `python-app/src/noc_beam/ui/components.py` with these classes:

```python
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
            self.setToolTip(f"{code} {reason}".strip())
            self.setAccessibleName(f"SIP code {code} {reason}".strip())


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
```

- [ ] **Step 6: Expose theme contract**

Modify `python-app/src/noc_beam/ui/theme.py`:

```python
REQUIRED_THEME_SELECTORS = (
    "QLabel#StatusPill",
    "QLabel#SipCodeBadge",
    "QLabel#MetricChip",
    "QToolButton#IconActionButton",
    "QFrame#FormSection",
    "QLabel#SectionHeader",
    "QFrame#FooterActionBar",
    "QPushButton#PrimaryAction",
    "QPushButton#SecondaryAction",
    "QWidget:focus",
)
```

Keep the existing `_load`, `load_theme_qss`, and `apply_theme` functions unchanged.

- [ ] **Step 7: Add required QSS selectors to all themes**

In `light.qss`, `dark.qss`, and `dark-hc.qss`, add a section named `Operator redesign primitives`. Use theme-appropriate colors, but keep the same selector names in all three files:

```css
/* Operator redesign primitives */
QWidget:focus {
    outline: none;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QToolButton:focus, QPushButton:focus {
    border: 1px solid #E85D04;
}
QLabel#StatusPill, QLabel#SipCodeBadge, QLabel#MetricChip {
    border-radius: 4px;
    padding: 2px 8px;
    min-height: 18px;
    font-size: 11px;
    font-weight: 600;
}
QLabel#StatusPill[level="ok"], QLabel#SipCodeBadge[level="ok"], QLabel#MetricChip[level="ok"] {
    color: #116329;
    background-color: #DFF7E8;
    border: 1px solid #A9E7BC;
}
QLabel#StatusPill[level="progress"], QLabel#SipCodeBadge[level="progress"], QLabel#MetricChip[level="progress"] {
    color: #8A5A00;
    background-color: #FFF3CD;
    border: 1px solid #F2D27A;
}
QLabel#StatusPill[level="danger"], QLabel#SipCodeBadge[level="danger"], QLabel#MetricChip[level="danger"] {
    color: #9F1D28;
    background-color: #FCE7E9;
    border: 1px solid #F2B8BE;
}
QLabel#StatusPill[level="info"], QLabel#SipCodeBadge[level="info"], QLabel#MetricChip[level="info"] {
    color: #145C8A;
    background-color: #E5F2FA;
    border: 1px solid #B8DDF2;
}
QLabel#StatusPill[level="muted"], QLabel#SipCodeBadge[level="muted"], QLabel#MetricChip[level="muted"] {
    color: #57606A;
    background-color: #F5F6F8;
    border: 1px solid #D8DEE4;
}
QToolButton#IconActionButton {
    background-color: transparent;
    border: 1px solid #D8DEE4;
    border-radius: 4px;
    padding: 0;
}
QToolButton#IconActionButton:hover {
    background-color: #F5F6F8;
}
QFrame#FormSection {
    background-color: transparent;
    border: none;
}
QLabel#SectionHeader {
    color: #57606A;
    font-size: 11px;
    font-weight: 700;
}
QFrame#FooterActionBar {
    background-color: #FFFFFF;
    border-top: 1px solid #D8DEE4;
}
QPushButton#PrimaryAction {
    min-height: 32px;
    border-radius: 4px;
    padding: 0 14px;
    background-color: #E85D04;
    border: 1px solid #E85D04;
    color: #FFFFFF;
    font-weight: 700;
}
QPushButton#SecondaryAction {
    min-height: 32px;
    border-radius: 4px;
    padding: 0 14px;
    background-color: #FFFFFF;
    border: 1px solid #D8DEE4;
    color: #1F2933;
}
```

Adapt only color values for dark and high-contrast; do not change selector names.

- [ ] **Step 8: Run foundation tests**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest tests/test_ui_components.py tests/test_ui_theme_contract.py -q
```

Expected: PASS.

- [ ] **Step 9: Run full suite**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest -q
```

Expected: PASS.

- [ ] **Step 10: Commit foundation**

Run:

```powershell
git add python-app/src/noc_beam/ui/design_tokens.py python-app/src/noc_beam/ui/components.py python-app/src/noc_beam/ui/theme.py python-app/src/noc_beam/ui/resources/light.qss python-app/src/noc_beam/ui/resources/dark.qss python-app/src/noc_beam/ui/resources/dark-hc.qss python-app/tests/test_ui_components.py python-app/tests/test_ui_theme_contract.py
git commit -m "feat(ui): add operator design system foundation"
```

---

### Task 2: Shell, Navigation, And Status Strip

**Files:**
- Modify: `python-app/src/noc_beam/ui/phone_shell.py`
- Modify: `python-app/src/noc_beam/ui/bottom_tabs.py`
- Modify: `python-app/src/noc_beam/ui/audio_strip.py`
- Modify: `python-app/src/noc_beam/ui/resources/light.qss`
- Modify: `python-app/src/noc_beam/ui/resources/dark.qss`
- Modify: `python-app/src/noc_beam/ui/resources/dark-hc.qss`
- Create: `python-app/tests/test_phone_shell_redesign.py`

- [ ] **Step 1: Write shell tests**

Add `python-app/tests/test_phone_shell_redesign.py`:

```python
from noc_beam.ui.bottom_tabs import BOTTOM_NAV_HEIGHT, Tab
from noc_beam.ui.phone_shell import PhoneShell


def test_phone_shell_uses_operator_width_and_critical_regions(qtbot, monkeypatch):
    monkeypatch.setattr("noc_beam.ui.phone_shell.QTimer.singleShot", lambda _ms, _fn: None)
    shell = PhoneShell()
    qtbot.addWidget(shell)

    assert shell.minimumWidth() >= 380
    assert shell.findChild(type(shell.account_chip), "AccountChip") is not None
    assert shell.findChild(type(shell.status_banner), "StatusBanner") is not None
    assert shell.findChild(type(shell.tabs), "BottomTabs") is not None


def test_bottom_tabs_are_compact_and_include_existing_pages(qtbot):
    from noc_beam.ui.bottom_tabs import BottomTabs

    tabs = BottomTabs()
    qtbot.addWidget(tabs)

    assert tabs.height() == BOTTOM_NAV_HEIGHT
    assert tabs._buttons[int(Tab.DIALPAD)].text().startswith("Dial")
    assert tabs._buttons[int(Tab.TRACE)].text().startswith("Trace")
```

- [ ] **Step 2: Run shell tests and verify failure**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest tests/test_phone_shell_redesign.py -q
```

Expected: FAIL because `BOTTOM_NAV_HEIGHT` is not exported and shell width is still too narrow.

- [ ] **Step 3: Update bottom tab constants**

In `bottom_tabs.py`, import and expose the constant:

```python
from noc_beam.ui.design_tokens import BOTTOM_NAV_HEIGHT
```

Replace:

```python
self.setFixedHeight(48)
```

with:

```python
self.setObjectName("BottomTabs")
self.setFixedHeight(BOTTOM_NAV_HEIGHT)
```

- [ ] **Step 4: Update shell dimensions and object names**

In `PhoneShell.__init__`, replace:

```python
self.resize(340, 720)
self.setMinimumWidth(300)
```

with:

```python
self.resize(420, 740)
self.setMinimumWidth(380)
```

Keep existing menu actions and signal wiring.

- [ ] **Step 5: Consolidate status strip naming**

In `phone_shell.py`, keep `TopStrip`, `AccountChip`, `AudioStrip`, and `StatusBanner` object names stable. Add accessible names:

```python
self.status_banner.setAccessibleName("Registration and call status")
self.menu_btn.setAccessibleName("Application menu")
self.account_chip.setAccessibleName("Active SIP account")
```

- [ ] **Step 6: Update shell and bottom tab QSS in all themes**

Ensure all three QSS files define:

```css
QFrame#TopStrip {
    border-bottom: 1px solid #D8DEE4;
}
QFrame#BottomTabs {
    border-top: 1px solid #D8DEE4;
}
QToolButton#TabBtn {
    border: none;
    border-top: 2px solid transparent;
    padding: 4px 0 3px 0;
    font-size: 10px;
}
QToolButton#TabBtn:checked {
    border-top-color: #E85D04;
    color: #E85D04;
}
```

Use dark and high-contrast equivalents for borders/backgrounds.

- [ ] **Step 7: Run shell tests**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest tests/test_phone_shell_redesign.py -q
```

Expected: PASS.

- [ ] **Step 8: Run full suite**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest -q
```

Expected: PASS.

- [ ] **Step 9: Commit shell**

Run:

```powershell
git add python-app/src/noc_beam/ui/phone_shell.py python-app/src/noc_beam/ui/bottom_tabs.py python-app/src/noc_beam/ui/audio_strip.py python-app/src/noc_beam/ui/resources/light.qss python-app/src/noc_beam/ui/resources/dark.qss python-app/src/noc_beam/ui/resources/dark-hc.qss python-app/tests/test_phone_shell_redesign.py
git commit -m "feat(ui): rebuild operator shell navigation"
```

---

### Task 3: Dial, Dialpad, Quick Dial, And Active Call

**Files:**
- Modify: `python-app/src/noc_beam/ui/call_widget.py`
- Modify: `python-app/src/noc_beam/ui/dialpad.py`
- Modify: `python-app/src/noc_beam/ui/quick_dial.py`
- Modify: `python-app/src/noc_beam/ui/phone_shell.py`
- Modify: `python-app/src/noc_beam/ui/resources/light.qss`
- Modify: `python-app/src/noc_beam/ui/resources/dark.qss`
- Modify: `python-app/src/noc_beam/ui/resources/dark-hc.qss`
- Create or extend: `python-app/tests/test_phone_shell_redesign.py`

- [ ] **Step 1: Add dial surface tests**

Append to `test_phone_shell_redesign.py`:

```python
def test_dial_surface_has_compact_controls(qtbot, monkeypatch):
    monkeypatch.setattr("noc_beam.ui.phone_shell.QTimer.singleShot", lambda _ms, _fn: None)
    shell = PhoneShell()
    qtbot.addWidget(shell)

    assert shell.dial_input.objectName() == "DialInput"
    assert shell.call_btn.objectName() == "CallButton"
    assert shell.call_btn.minimumHeight() <= 40
    assert shell.findChild(type(shell.dialpad), "DialPad") is not None
```

- [ ] **Step 2: Run dial test and verify failure or current gaps**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest tests/test_phone_shell_redesign.py::test_dial_surface_has_compact_controls -q
```

Expected before implementation: FAIL if `dialpad` object name or compact height is missing.

- [ ] **Step 3: Set dialpad object name and compact sizing**

In `dialpad.py`, ensure the root widget has:

```python
self.setObjectName("DialPad")
```

For keypad buttons, use fixed or maximum heights between 40 and 48 px:

```python
btn.setObjectName("DialPadButton")
btn.setMinimumHeight(40)
btn.setMaximumHeight(48)
btn.setAccessibleName(f"Dial digit {digit}")
```

- [ ] **Step 4: Standardize call controls**

In `call_widget.py`, replace large secondary text buttons with compact object names:

```python
self.setObjectName("CallWidget")
self.hangup_btn.setObjectName("HangupButton")
self.hold_btn.setObjectName("CallControlButton")
self.mute_btn.setObjectName("CallControlButton")
self.transfer_btn.setObjectName("CallControlButton")
```

Set accessible names:

```python
self.hangup_btn.setAccessibleName("Hang up active call")
self.hold_btn.setAccessibleName("Hold active call")
self.mute_btn.setAccessibleName("Mute microphone")
self.transfer_btn.setAccessibleName("Transfer active call")
```

- [ ] **Step 5: Update quick dial row object names**

In `quick_dial.py`, ensure recent/quick rows use:

```python
row.setObjectName("QuickDialRow")
call_btn.setObjectName("IconActionButton")
```

Keep existing signals unchanged.

- [ ] **Step 6: Update QSS for dial controls in all themes**

Ensure all three themes define:

```css
QLineEdit#DialInput {
    min-height: 32px;
    max-height: 36px;
    border-radius: 4px;
}
QPushButton#CallButton {
    min-height: 32px;
    max-height: 36px;
    border-radius: 4px;
    background-color: #2EBD5C;
    color: #FFFFFF;
}
QWidget#DialPad QToolButton#DialPadButton {
    min-height: 40px;
    max-height: 48px;
    border-radius: 4px;
}
QFrame#QuickDialRow {
    border-bottom: 1px solid #D8DEE4;
}
QPushButton#HangupButton {
    min-height: 32px;
    border-radius: 4px;
    background-color: #D33841;
    color: #FFFFFF;
}
QPushButton#CallControlButton {
    min-height: 28px;
    border-radius: 4px;
}
```

- [ ] **Step 7: Run focused tests**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest tests/test_phone_shell_redesign.py -q
```

Expected: PASS.

- [ ] **Step 8: Run full suite**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest -q
```

Expected: PASS.

- [ ] **Step 9: Commit dial**

Run:

```powershell
git add python-app/src/noc_beam/ui/call_widget.py python-app/src/noc_beam/ui/dialpad.py python-app/src/noc_beam/ui/quick_dial.py python-app/src/noc_beam/ui/phone_shell.py python-app/src/noc_beam/ui/resources/light.qss python-app/src/noc_beam/ui/resources/dark.qss python-app/src/noc_beam/ui/resources/dark-hc.qss python-app/tests/test_phone_shell_redesign.py
git commit -m "feat(ui): rebuild dial and active call surfaces"
```

---

### Task 4: Contacts, Favorites, And Shared Dense Rows

**Files:**
- Modify: `python-app/src/noc_beam/ui/components.py`
- Modify: `python-app/src/noc_beam/ui/contacts_view.py`
- Modify: `python-app/src/noc_beam/ui/favorites_view.py`
- Modify: `python-app/src/noc_beam/ui/resources/light.qss`
- Modify: `python-app/src/noc_beam/ui/resources/dark.qss`
- Modify: `python-app/src/noc_beam/ui/resources/dark-hc.qss`
- Modify: `python-app/tests/test_contacts_view.py`
- Modify: `python-app/tests/test_favorites_view.py`

- [ ] **Step 1: Add dense row helper tests**

Append to `python-app/tests/test_ui_components.py`:

```python
from noc_beam.ui.components import DenseListRow


def test_dense_list_row_has_fixed_action_column(qtbot):
    row = DenseListRow(title="Alice", subtitle="sip:alice@example.com", marker="★")
    qtbot.addWidget(row)

    assert row.objectName() == "DenseListRow"
    assert row.title_label.text() == "Alice"
    assert row.subtitle_label.text() == "sip:alice@example.com"
    assert row.marker_label.text() == "★"
```

- [ ] **Step 2: Run dense row test and verify failure**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest tests/test_ui_components.py::test_dense_list_row_has_fixed_action_column -q
```

Expected: FAIL because `DenseListRow` does not exist.

- [ ] **Step 3: Add DenseListRow**

Append to `components.py`:

```python
class DenseListRow(QFrame):
    def __init__(
        self,
        title: str,
        subtitle: str = "",
        marker: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("DenseListRow")
        self.marker_label = QLabel(marker, self)
        self.marker_label.setObjectName("DenseRowMarker")
        self.marker_label.setFixedWidth(20)
        self.marker_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel(title, self)
        self.title_label.setObjectName("DenseRowTitle")
        self.subtitle_label = QLabel(subtitle, self)
        self.subtitle_label.setObjectName("DenseRowSubtitle")

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(1)
        text_col.addWidget(self.title_label)
        text_col.addWidget(self.subtitle_label)

        self.action_holder = QFrame(self)
        self.action_holder.setObjectName("DenseRowActions")
        self.action_layout = QHBoxLayout(self.action_holder)
        self.action_layout.setContentsMargins(0, 0, 0, 0)
        self.action_layout.setSpacing(4)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)
        layout.addWidget(self.marker_label)
        layout.addLayout(text_col, 1)
        layout.addWidget(self.action_holder)
```

- [ ] **Step 4: Refactor Contacts rows to use dense row object names**

In `contacts_view.py`, keep existing signals and store calls. Ensure `ContactRow` object names match the shared system:

```python
self.setObjectName("DenseListRow")
marker.setObjectName("DenseRowMarker")
name_lbl.setObjectName("DenseRowTitle")
number_lbl.setObjectName("DenseRowSubtitle")
call_btn.setObjectName("IconActionButton")
edit_btn.setObjectName("IconActionButton")
delete_btn.setObjectName("IconActionButton")
```

Keep `call_requested`, `edit_requested`, and `delete_requested` signals unchanged.

- [ ] **Step 5: Refactor Favorites rows to match Contacts**

In `favorites_view.py`, apply the same object names:

```python
self.setObjectName("DenseListRow")
marker.setObjectName("DenseRowMarker")
name_lbl.setObjectName("DenseRowTitle")
number_lbl.setObjectName("DenseRowSubtitle")
call_btn.setObjectName("IconActionButton")
```

Keep existing favorites load/save behavior unchanged.

- [ ] **Step 6: Update list QSS in all themes**

Add to each theme:

```css
QFrame#DenseListRow {
    border-bottom: 1px solid #D8DEE4;
    background-color: transparent;
}
QFrame#DenseListRow:hover {
    background-color: #F5F6F8;
}
QLabel#DenseRowMarker {
    font-size: 13px;
    color: #E85D04;
}
QLabel#DenseRowTitle {
    font-size: 13px;
    font-weight: 600;
}
QLabel#DenseRowSubtitle {
    font-size: 11px;
    color: #57606A;
}
QFrame#DenseRowActions {
    background-color: transparent;
    border: none;
}
```

Adapt colors for dark and high-contrast.

- [ ] **Step 7: Run contacts/favorites tests**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest tests/test_ui_components.py tests/test_contacts_view.py tests/test_favorites_view.py -q
```

Expected: PASS.

- [ ] **Step 8: Run full suite**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest -q
```

Expected: PASS.

- [ ] **Step 9: Commit list rows**

Run:

```powershell
git add python-app/src/noc_beam/ui/components.py python-app/src/noc_beam/ui/contacts_view.py python-app/src/noc_beam/ui/favorites_view.py python-app/src/noc_beam/ui/resources/light.qss python-app/src/noc_beam/ui/resources/dark.qss python-app/src/noc_beam/ui/resources/dark-hc.qss python-app/tests/test_ui_components.py python-app/tests/test_contacts_view.py python-app/tests/test_favorites_view.py
git commit -m "feat(ui): rebuild contacts and favorites rows"
```

---

### Task 5: History Redesign

**Files:**
- Modify: `python-app/src/noc_beam/ui/history_view.py`
- Modify: `python-app/src/noc_beam/ui/cdr_detail_dialog.py`
- Modify: `python-app/src/noc_beam/ui/resources/light.qss`
- Modify: `python-app/src/noc_beam/ui/resources/dark.qss`
- Modify: `python-app/src/noc_beam/ui/resources/dark-hc.qss`
- Modify: `python-app/tests/test_history.py`

- [ ] **Step 1: Add History row tests**

Append to `python-app/tests/test_history.py`:

```python
from noc_beam.config.history import CdrEntry
from noc_beam.ui.history_view import HistoryRow


def test_history_row_uses_result_badge_and_action_column(qtbot):
    entry = CdrEntry(
        direction="out",
        peer_uri="sip:alice@example.com",
        started_at=1.0,
        connected_at=2.0,
        ended_at=8.0,
        end_code=200,
        end_reason="OK",
        codec="PCMU",
        account_id="acc-1",
    )
    row = HistoryRow(entry, 0)
    qtbot.addWidget(row)

    assert row.objectName() == "HistoryRow"
    assert row.findChild(object, "SipCodeBadge") is not None
    assert row.findChild(object, "HistoryRowCall") is not None
```

- [ ] **Step 2: Run History test and verify failure**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest tests/test_history.py::test_history_row_uses_result_badge_and_action_column -q
```

Expected: FAIL because `HistoryRow` does not create a `SipCodeBadge`.

- [ ] **Step 3: Add SipCodeBadge to HistoryRow**

In `history_view.py`, import:

```python
from noc_beam.ui.components import SipCodeBadge
```

Inside `HistoryRow.__init__`, after metadata labels are built, create:

```python
code = entry.end_code if entry.end_code else (200 if entry.was_answered else None)
badge = SipCodeBadge(code, entry.end_reason, self)
```

Add the badge before the callback button:

```python
outer.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)
outer.addWidget(self._call_btn, 0, Qt.AlignmentFlag.AlignVCenter)
```

- [ ] **Step 4: Keep missed/failed state at rest**

Ensure `HistoryRow` still sets:

```python
self.setProperty("result", _result_class(entry))
```

In all themes, define visible but restrained state:

```css
QFrame#HistoryRow[result="missed"], QFrame#HistoryRow[result="failed"] {
    background-color: #FEF6F6;
}
```

Use dark/high-contrast equivalents.

- [ ] **Step 5: Align CDR detail dialog with footer system**

In `cdr_detail_dialog.py`, use `FooterActionBar` for close/redial/export where applicable, keeping existing redial/export signals. Set:

```python
self.setObjectName("CdrDetailDialog")
```

Ensure the direction/status chip uses `StatusPill`.

- [ ] **Step 6: Run History tests**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest tests/test_history.py -q
```

Expected: PASS.

- [ ] **Step 7: Run full suite**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest -q
```

Expected: PASS.

- [ ] **Step 8: Commit History**

Run:

```powershell
git add python-app/src/noc_beam/ui/history_view.py python-app/src/noc_beam/ui/cdr_detail_dialog.py python-app/src/noc_beam/ui/resources/light.qss python-app/src/noc_beam/ui/resources/dark.qss python-app/src/noc_beam/ui/resources/dark-hc.qss python-app/tests/test_history.py
git commit -m "feat(ui): rebuild history scan rows"
```

---

### Task 6: Trace As NOC Credibility Surface

**Files:**
- Modify: `python-app/src/noc_beam/ui/trace_view.py`
- Modify: `python-app/src/noc_beam/ui/resources/light.qss`
- Modify: `python-app/src/noc_beam/ui/resources/dark.qss`
- Modify: `python-app/src/noc_beam/ui/resources/dark-hc.qss`
- Create: `python-app/tests/test_trace_view_redesign.py`

- [ ] **Step 1: Write Trace redesign tests**

Add `python-app/tests/test_trace_view_redesign.py`:

```python
from noc_beam.ui.trace_view import TraceMsgRow, _Msg


def test_trace_msg_row_has_table_like_cells(qtbot):
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
    qtbot.addWidget(row)

    assert row.objectName() == "TraceMsgRow"
    assert row.property("dir") == "rx"
    assert row.findChild(object, "TraceMsgTime") is not None
    assert row.findChild(object, "TraceMsgDir") is not None
    assert row.findChild(object, "TraceMsgSummary") is not None
```

- [ ] **Step 2: Run Trace test**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest tests/test_trace_view_redesign.py -q
```

Expected: PASS if existing object names remain; FAIL if object names drifted and need correction.

- [ ] **Step 3: Convert Trace row layout to strict columns**

In `TraceMsgRow.__init__`, keep the existing widgets but enforce fixed/min widths:

```python
ts.setFixedWidth(64)
dir_lbl.setFixedWidth(28)
chip.setFixedWidth(48)
summary.setMinimumWidth(120)
summary.setToolTip(msg.summary)
```

Keep body expansion behavior unchanged.

- [ ] **Step 4: Improve dialog group header columns**

In `TraceDialogRow.__init__`, ensure these labels have stable widths:

```python
self._caret.setFixedWidth(14)
time_lbl.setFixedWidth(64)
self._id_lbl.setFixedWidth(88)
self._id_lbl.setToolTip(dialog.call_id)
```

Keep chip sequence and expand/collapse behavior unchanged.

- [ ] **Step 5: Update Trace QSS in all themes**

Ensure all themes include:

```css
QFrame#TraceDialogRow, QFrame#TraceMsgRow {
    border-bottom: 1px solid #D8DEE4;
}
QLabel#TraceDialogTime, QLabel#TraceMsgTime, QLabel#TraceDialogId {
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 11px;
}
QLabel#TraceMsgDir[dir="rx"] {
    color: #0969DA;
}
QLabel#TraceMsgDir[dir="tx"] {
    color: #1A7F37;
}
QTextEdit#TraceMsgBody {
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 11px;
}
```

Use dark/high-contrast equivalents.

- [ ] **Step 6: Run Trace tests**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest tests/test_trace_view_redesign.py tests/test_trace_parser.py -q
```

Expected: PASS.

- [ ] **Step 7: Run full suite**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest -q
```

Expected: PASS.

- [ ] **Step 8: Commit Trace**

Run:

```powershell
git add python-app/src/noc_beam/ui/trace_view.py python-app/src/noc_beam/ui/resources/light.qss python-app/src/noc_beam/ui/resources/dark.qss python-app/src/noc_beam/ui/resources/dark-hc.qss python-app/tests/test_trace_view_redesign.py
git commit -m "feat(ui): rebuild trace as operator table"
```

---

### Task 7: Settings, Account, And Contact Dialog Forms

**Files:**
- Modify: `python-app/src/noc_beam/ui/settings_dialog.py`
- Modify: `python-app/src/noc_beam/ui/account_dialog.py`
- Modify: `python-app/src/noc_beam/ui/account_settings_dialog.py`
- Modify: `python-app/src/noc_beam/ui/contacts_view.py`
- Modify: `python-app/src/noc_beam/ui/resources/light.qss`
- Modify: `python-app/src/noc_beam/ui/resources/dark.qss`
- Modify: `python-app/src/noc_beam/ui/resources/dark-hc.qss`
- Create: `python-app/tests/test_dialog_redesign.py`

- [ ] **Step 1: Write dialog redesign tests**

Add `python-app/tests/test_dialog_redesign.py`:

```python
from noc_beam.ui.account_dialog import AccountDialog
from noc_beam.ui.settings_dialog import SettingsDialog


def test_account_dialog_has_form_sections_and_footer(qtbot):
    dlg = AccountDialog()
    qtbot.addWidget(dlg)

    assert dlg.findChild(object, "FormSection") is not None
    assert dlg.findChild(object, "FooterActionBar") is not None
    assert dlg.windowTitle() in {"Add SIP account", "Edit SIP account"}


def test_account_dialog_required_fields_show_inline_error(qtbot):
    dlg = AccountDialog()
    qtbot.addWidget(dlg)

    dlg.accept()

    assert "required" in dlg.error.text().lower()


def test_settings_dialog_has_footer_action_bar(qtbot):
    dlg = SettingsDialog()
    qtbot.addWidget(dlg)

    assert dlg.findChild(object, "FooterActionBar") is not None
```

- [ ] **Step 2: Run dialog tests and verify failure**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest tests/test_dialog_redesign.py -q
```

Expected: FAIL until dialogs use `FormSection` and `FooterActionBar`.

- [ ] **Step 3: Refactor AccountDialog footer**

In `account_dialog.py`, import:

```python
from noc_beam.ui.components import FooterActionBar, FormSection
```

Replace ad hoc Save/Cancel button rows with:

```python
self.footer = FooterActionBar("Save" if is_edit else "Add account", "Cancel", self)
self.footer.primary_button.clicked.connect(self.accept)
self.footer.secondary_button.clicked.connect(self.reject)
```

Add the footer to the root layout after the form sections.

- [ ] **Step 4: Keep inline validation explicit**

In `AccountDialog.accept`, require username and domain:

```python
missing = []
if not self.username_edit.text().strip():
    missing.append("Username")
if not self.domain_edit.text().strip():
    missing.append("Domain")
if missing:
    self.error.setText(", ".join(missing) + " required.")
    first = self.username_edit if "Username" in missing else self.domain_edit
    first.setFocus()
    return
super().accept()
```

Use the actual field attribute names already present in `account_dialog.py`.

- [ ] **Step 5: Refactor SettingsDialog footer**

In `settings_dialog.py`, replace `QDialogButtonBox` or custom rows with:

```python
self.footer = FooterActionBar("Save", "Cancel", self)
self.footer.primary_button.clicked.connect(self.accept)
self.footer.secondary_button.clicked.connect(self.reject)
```

Keep existing settings controls and value extraction unchanged.

- [ ] **Step 6: Refactor ContactDialog to use shared footer**

In `contacts_view.py`, inside `ContactDialog`, use:

```python
self.footer = FooterActionBar("Save contact" if is_edit else "Add contact", "Cancel", self)
self.footer.primary_button.clicked.connect(self.accept)
self.footer.secondary_button.clicked.connect(self.reject)
```

Keep `values()` and required Name/Number validation unchanged.

- [ ] **Step 7: Update dialog QSS in all themes**

Add to each theme:

```css
QDialog QLineEdit, QDialog QComboBox, QDialog QSpinBox {
    min-height: 30px;
}
QLabel#DialogError {
    color: #D33841;
    font-size: 12px;
}
QFrame#DialogRail {
    border-right: 1px solid #D8DEE4;
}
```

Use dark/high-contrast equivalents.

- [ ] **Step 8: Run dialog tests**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest tests/test_dialog_redesign.py tests/test_account_settings_dialog.py tests/test_contacts_view.py -q
```

Expected: PASS.

- [ ] **Step 9: Run full suite**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest -q
```

Expected: PASS.

- [ ] **Step 10: Commit dialogs**

Run:

```powershell
git add python-app/src/noc_beam/ui/settings_dialog.py python-app/src/noc_beam/ui/account_dialog.py python-app/src/noc_beam/ui/account_settings_dialog.py python-app/src/noc_beam/ui/contacts_view.py python-app/src/noc_beam/ui/resources/light.qss python-app/src/noc_beam/ui/resources/dark.qss python-app/src/noc_beam/ui/resources/dark-hc.qss python-app/tests/test_dialog_redesign.py
git commit -m "feat(ui): rebuild settings and account dialogs"
```

---

### Task 8: Test Runner Operator Window

**Files:**
- Modify: `python-app/src/noc_beam/ui/test_runner_view.py`
- Modify: `python-app/src/noc_beam/ui/resources/light.qss`
- Modify: `python-app/src/noc_beam/ui/resources/dark.qss`
- Modify: `python-app/src/noc_beam/ui/resources/dark-hc.qss`
- Modify: `python-app/tests/test_test_runner_view.py`

- [ ] **Step 1: Add Test Runner visual contract tests**

Append to `python-app/tests/test_test_runner_view.py`:

```python
from noc_beam.ui.test_runner_view import TestRunnerView


def test_test_runner_uses_operator_object_names(qtbot):
    view = TestRunnerView([])
    qtbot.addWidget(view)

    assert view.findChild(object, "TestRunnerPasteGrid") is not None
    assert view.findChild(object, "OperatorToolbar") is not None
    assert view.table.objectName() == "TestRunnerResults"
    assert view.run_btn.objectName() == "RunTestButton"
```

- [ ] **Step 2: Run Test Runner visual test and verify failure**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest tests/test_test_runner_view.py::test_test_runner_uses_operator_object_names -q
```

Expected: FAIL until object names are added.

- [ ] **Step 3: Add structural object names**

In `test_runner_view.py`, set:

```python
self.callers_edit.setObjectName("TestRunnerPasteBox")
self.targets_edit.setObjectName("TestRunnerPasteBox")
self.run_btn.setObjectName("RunTestButton")
self.table.setObjectName("TestRunnerResults")
self.summary_label.setObjectName("TestRunnerSummary")
self.cancel_btn.setObjectName("SecondaryAction")
self.export_btn.setObjectName("PrimaryAction")
```

Wrap paste grid in a `QWidget` or `QFrame` named `TestRunnerPasteGrid`, and wrap controls in a `QFrame` named `OperatorToolbar`.

- [ ] **Step 4: Improve result cell display without changing CSV**

In `_populate_result_row`, when setting result/code cells, keep raw result text but add object-name aware items:

```python
self._set_text(row, 3, result.result)
self._set_text(row, 4, "" if result.sip_code is None else str(result.sip_code))
```

Do not change `CSV_HEADER` or `_write_csv`.

- [ ] **Step 5: Update Test Runner QSS in all themes**

Add:

```css
QFrame#OperatorToolbar {
    border: 1px solid #D8DEE4;
    border-radius: 4px;
    padding: 6px;
}
QTextEdit#TestRunnerPasteBox {
    border: 1px solid #D8DEE4;
    border-radius: 4px;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 12px;
}
QTableWidget#TestRunnerResults {
    gridline-color: #D8DEE4;
    selection-background-color: #E5F2FA;
}
QPushButton#RunTestButton {
    min-height: 32px;
    border-radius: 4px;
    background-color: #2EBD5C;
    color: #FFFFFF;
    font-weight: 700;
}
```

Use dark/high-contrast equivalents.

- [ ] **Step 6: Run Test Runner tests**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest tests/test_test_runner_view.py tests/test_test_runner.py tests/test_test_plan.py -q
```

Expected: PASS.

- [ ] **Step 7: Run full suite**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest -q
```

Expected: PASS.

- [ ] **Step 8: Commit Test Runner**

Run:

```powershell
git add python-app/src/noc_beam/ui/test_runner_view.py python-app/src/noc_beam/ui/resources/light.qss python-app/src/noc_beam/ui/resources/dark.qss python-app/src/noc_beam/ui/resources/dark-hc.qss python-app/tests/test_test_runner_view.py
git commit -m "feat(ui): rebuild test runner operator window"
```

---

### Task 9: Accessibility And Theme Completion

**Files:**
- Create: `python-app/tests/test_ui_accessibility_contract.py`
- Modify: `python-app/src/noc_beam/ui/resources/light.qss`
- Modify: `python-app/src/noc_beam/ui/resources/dark.qss`
- Modify: `python-app/src/noc_beam/ui/resources/dark-hc.qss`
- Modify UI files from earlier tasks only if tests reveal missing accessible names or focus states.

- [ ] **Step 1: Write accessibility contract tests**

Add `python-app/tests/test_ui_accessibility_contract.py`:

```python
from PySide6.QtWidgets import QPushButton, QToolButton

from noc_beam.ui.phone_shell import PhoneShell


def test_shell_interactive_controls_have_accessible_names(qtbot, monkeypatch):
    monkeypatch.setattr("noc_beam.ui.phone_shell.QTimer.singleShot", lambda _ms, _fn: None)
    shell = PhoneShell()
    qtbot.addWidget(shell)

    controls = shell.findChildren(QPushButton) + shell.findChildren(QToolButton)
    named = [c for c in controls if c.accessibleName() or c.toolTip() or c.text()]
    assert len(named) == len(controls)


def test_destructive_buttons_are_text_labeled(qtbot, monkeypatch):
    monkeypatch.setattr("noc_beam.ui.phone_shell.QTimer.singleShot", lambda _ms, _fn: None)
    shell = PhoneShell()
    qtbot.addWidget(shell)

    destructive = shell.findChildren(QPushButton, "HangupButton")
    for button in destructive:
        assert button.text().strip()
        assert "hang" in (button.text() + button.accessibleName()).lower()
```

- [ ] **Step 2: Run accessibility tests and verify failures**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest tests/test_ui_accessibility_contract.py -q
```

Expected: FAIL if any interactive controls lack accessible names, text, or tooltips.

- [ ] **Step 3: Patch missing accessible names**

For each failing control, set one of:

```python
button.setAccessibleName("Clear call history")
button.setToolTip("Clear call history")
button.setText("Clear")
```

Use text labels for destructive actions and tooltips for icon-only actions.

- [ ] **Step 4: Confirm high-contrast readability selectors**

In `dark-hc.qss`, make sure these selectors use high-contrast colors and visible borders:

```css
QLabel#StatusPill, QLabel#SipCodeBadge, QLabel#MetricChip,
QToolButton#IconActionButton, QPushButton#PrimaryAction, QPushButton#SecondaryAction,
QFrame#DenseListRow, QFrame#TraceMsgRow, QFrame#TraceDialogRow {
    border-width: 1px;
}
```

- [ ] **Step 5: Run accessibility and theme tests**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest tests/test_ui_accessibility_contract.py tests/test_ui_theme_contract.py -q
```

Expected: PASS.

- [ ] **Step 6: Run full suite**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest -q
```

Expected: PASS.

- [ ] **Step 7: Commit accessibility**

Run:

```powershell
git add python-app/src/noc_beam/ui python-app/tests/test_ui_accessibility_contract.py python-app/tests/test_ui_theme_contract.py
git commit -m "feat(ui): complete accessible theme coverage"
```

---

### Task 10: Source-App Screenshot Smoke Harness

**Files:**
- Create: `python-app/tools/ui_smoke.py`
- Create: `python-app/tests/test_ui_smoke_tool.py`
- Modify: `.gitignore` if screenshots or smoke artifacts are not already ignored.

- [ ] **Step 1: Write smoke tool test**

Add `python-app/tests/test_ui_smoke_tool.py`:

```python
from pathlib import Path

from tools.ui_smoke import screenshot_path


def test_screenshot_path_uses_theme_and_page(tmp_path):
    path = screenshot_path(tmp_path, "light", "dial")
    assert path == tmp_path / "light-dial.png"
```

- [ ] **Step 2: Run smoke tool test and verify failure**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest tests/test_ui_smoke_tool.py -q
```

Expected: FAIL because `tools.ui_smoke` does not exist.

- [ ] **Step 3: Add smoke harness**

Create `python-app/tools/ui_smoke.py`:

```python
from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from noc_beam.ui.phone_shell import PhoneShell
from noc_beam.ui.theme import apply_theme


def screenshot_path(output_dir: Path, theme: str, page: str) -> Path:
    return output_dir / f"{theme}-{page}.png"


def capture_shell(output_dir: Path, theme: str = "light", high_contrast: bool = False) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication(sys.argv)
    apply_theme(app, high_contrast=high_contrast, theme=theme)
    shell = PhoneShell()
    shell.show()

    def grab() -> None:
        pix = shell.grab()
        page = "high-contrast-dial" if high_contrast else f"{theme}-dial"
        pix.save(str(output_dir / f"{page}.png"))
        shell.close()
        app.quit()

    QTimer.singleShot(500, grab)
    app.exec()


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("screenshots-for-review")
    capture_shell(output_dir, "light", False)
    capture_shell(output_dir, "dark", False)
    capture_shell(output_dir, "light", True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run smoke tool test**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest tests/test_ui_smoke_tool.py -q
```

Expected: PASS.

- [ ] **Step 5: Run screenshot smoke locally**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
$env:QT_QPA_PLATFORM="offscreen"
python tools/ui_smoke.py ..\screenshots-for-review
```

Expected: PNG files are created under `E:\NOC_Beam\Eyebeam\screenshots-for-review`.

- [ ] **Step 6: Inspect generated screenshots**

Open the PNGs and check:

- Dial input and Call button do not clip.
- Bottom navigation labels fit.
- Focus rings and badges are visible.
- Light, dark, and high-contrast look like the same product.

- [ ] **Step 7: Run full suite**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest -q
```

Expected: PASS.

- [ ] **Step 8: Commit smoke harness**

Run:

```powershell
git add python-app/tools/ui_smoke.py python-app/tests/test_ui_smoke_tool.py
git commit -m "test(ui): add source screenshot smoke harness"
```

---

### Task 11: Packaged EXE Verification

**Files:**
- Modify packaging docs or tests only if current commands are stale.
- Do not commit generated `.exe` unless the repository release process requires it.

- [ ] **Step 1: Run full tests before packaging**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
pytest -q
```

Expected: PASS.

- [ ] **Step 2: Run existing packaging command**

Run:

```powershell
cd E:\NOC_Beam\Eyebeam\python-app
powershell -ExecutionPolicy Bypass -File .\build\build_windows.ps1 -PythonExe .\.venv\Scripts\python.exe
```

Expected: a new Windows `.exe` builds without missing QSS/resources.

- [ ] **Step 3: Launch packaged `.exe`**

Run the newly built `.exe` from PowerShell.

Expected:

- App launches.
- No missing stylesheet/resource errors.
- Main shell uses the new width and visual system.

- [ ] **Step 4: Account persistence smoke**

In the `.exe`:

1. Open Add SIP account.
2. Enter a test account using non-production credentials.
3. Press Save.
4. Close app.
5. Reopen app.
6. Confirm account is still listed.

Expected: account persists. If it does not, stop UI work and debug persistence before continuing.

- [ ] **Step 5: Test Runner CSV smoke**

In the `.exe`:

1. Open Test Runner.
2. Enter one caller number and one target number.
3. Run in stub or SIP mode.
4. Export CSV to a temporary file.

Expected: CSV has the documented header and one result row.

- [ ] **Step 6: Commit packaging/doc fixes if needed**

If packaging command/docs were corrected:

```powershell
git add python-app/build/build_windows.ps1 python-app/build/noc_beam.spec .github/workflows/build-windows.yml python-app/tests/test_windows_packaging.py
git commit -m "docs(release): update UI rewrite packaging verification"
```

If no files changed, do not commit.

---

## Self-Review

Spec coverage:

- Main shell and navigation: Task 2.
- Dial and active call: Task 3.
- Contacts and Favorites: Task 4.
- History: Task 5.
- Trace: Task 6.
- Settings and Account dialogs: Task 7.
- Test Runner: Task 8.
- Light/dark/high-contrast themes: Tasks 1 and 9.
- Accessibility: Task 9.
- Source screenshots and packaged `.exe` verification: Tasks 10 and 11.

No task changes SIP, account persistence, history storage, contacts storage, or CSV semantics except to preserve existing UI integrations.

Execution should commit after every task, run focused tests before full tests, and stop on the first regression that affects account saving, calling, or packaging.
