# First-Run Account Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make account creation obvious and reachable in a clean downloaded `NOC_Beam.exe` with no existing config.

**Architecture:** Keep persistence and SIP registration unchanged. Fix the first-run UI path in `PhoneShell` so the visible account chip and status link both expose `Add account...`, then cover the behavior with Qt tests using a fake modal dialog and fake SIP endpoint.

**Tech Stack:** Python 3.12, PySide6, pytest, existing `AccountConfig` persistence.

---

### Task 1: Prove Clean-Start Account Creation Is Reachable

**Files:**
- Modify: `python-app/tests/test_test_runner_view.py`
- Test: `python-app/tests/test_test_runner_view.py`

- [ ] **Step 1: Write the failing account-chip menu test**

Add this test near the other `PhoneShell` tests:

```python
def test_phone_shell_empty_account_chip_offers_add_account(
    qt_app: QApplication,
    monkeypatch,
) -> None:
    class FakeRinger:
        def start(self) -> None:
            pass

        def stop(self) -> None:
            pass

    class FakeTimer:
        @staticmethod
        def singleShot(_msec, _callback) -> None:
            pass

    monkeypatch.setattr(phone_shell_module, "load_settings", GlobalSettings)
    monkeypatch.setattr(phone_shell_module, "load_accounts", lambda: [])
    monkeypatch.setattr(phone_shell_module, "Ringer", FakeRinger)
    monkeypatch.setattr(phone_shell_module, "QTimer", FakeTimer)
    monkeypatch.setattr(PhoneShell, "_start_sip", lambda _self: None)

    shell = PhoneShell()

    try:
        labels = [action.text() for action in shell.account_chip.menu().actions()]

        assert "No accounts" in labels
        assert "Add account..." in labels
    finally:
        shell._really_quitting = True
        shell.close()
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `python -m pytest tests/test_test_runner_view.py::test_phone_shell_empty_account_chip_offers_add_account -q`

Expected: FAIL because the empty account chip menu contains only the disabled `No accounts` action.

### Task 2: Add the First-Run Account Affordances

**Files:**
- Modify: `python-app/src/noc_beam/ui/phone_shell.py`
- Test: `python-app/tests/test_test_runner_view.py`

- [ ] **Step 1: Update `_refresh_accounts` to always add an account action**

Change the empty-menu branch in `PhoneShell._refresh_accounts()` so the account chip still shows `No account  v`, but its dropdown also contains `Add account...`:

```python
        if not enabled:
            empty = menu.addAction("No accounts"); empty.setEnabled(False)
            menu.addSeparator()
            menu.addAction("Add account...", self._on_add_account)
            self._active_account_id = ""
            self.account_chip.setText("No account  v")
```

- [ ] **Step 2: Teach the status link to open account creation**

Extend `PhoneShell._on_status_link()`:

```python
        if action == "add-account":
            self._on_add_account()
            return
```

When there are no enabled accounts, set the status banner to a direct setup link:

```python
            self._set_status(
                "No SIP account configured",
                "warn",
                "Add account",
                "add-account",
            )
```

- [ ] **Step 3: Run the focused test and verify it passes**

Run: `python -m pytest tests/test_test_runner_view.py::test_phone_shell_empty_account_chip_offers_add_account -q`

Expected: PASS.

### Task 3: Prove Adding Persists and Refreshes on a Clean Start

**Files:**
- Modify: `python-app/tests/test_test_runner_view.py`
- Test: `python-app/tests/test_test_runner_view.py`

- [ ] **Step 1: Write the clean-start add flow test**

Add this test:

```python
def test_phone_shell_add_account_from_clean_start_saves_and_selects(
    qt_app: QApplication,
    monkeypatch,
) -> None:
    new_account = AccountConfig(
        id="new-acct",
        display_name="NOC Lab",
        username="1001",
        domain="sip.example.test",
        enabled=True,
    )
    saved: list[list[AccountConfig]] = []
    added: list[AccountConfig] = []

    class FakeRinger:
        def start(self) -> None:
            pass

        def stop(self) -> None:
            pass

    class FakeTimer:
        @staticmethod
        def singleShot(_msec, _callback) -> None:
            pass

    class FakeDialog:
        Accepted = 1

        def __init__(self, parent=None) -> None:
            self.parent = parent

        def result_account(self) -> AccountConfig:
            return new_account

    class FakeEndpoint:
        def add_account(self, cfg: AccountConfig) -> None:
            added.append(cfg)

    class FakeSipEndpoint:
        @staticmethod
        def instance() -> FakeEndpoint:
            return fake_endpoint

    fake_endpoint = FakeEndpoint()

    monkeypatch.setattr(phone_shell_module, "load_settings", GlobalSettings)
    monkeypatch.setattr(phone_shell_module, "load_accounts", lambda: [])
    monkeypatch.setattr(phone_shell_module, "save_accounts", lambda accounts: saved.append(list(accounts)))
    monkeypatch.setattr(phone_shell_module, "Ringer", FakeRinger)
    monkeypatch.setattr(phone_shell_module, "QTimer", FakeTimer)
    monkeypatch.setattr(phone_shell_module, "AccountDialog", FakeDialog)
    monkeypatch.setattr(phone_shell_module, "SipEndpoint", FakeSipEndpoint)
    monkeypatch.setattr(phone_shell_module, "_open_modal", lambda _dlg: True)
    monkeypatch.setattr(PhoneShell, "_start_sip", lambda _self: None)

    shell = PhoneShell()

    try:
        add_action = next(
            action for action in shell.account_chip.menu().actions()
            if action.text() == "Add account..."
        )
        add_action.trigger()

        assert saved == [[new_account]]
        assert added == [new_account]
        assert shell.accounts == [new_account]
        assert shell._active_account_id == "new-acct"
        assert shell.account_chip.text() == "NOC Lab  v"
    finally:
        shell._really_quitting = True
        shell.close()
```

- [ ] **Step 2: Run the focused add-flow test**

Run: `python -m pytest tests/test_test_runner_view.py::test_phone_shell_add_account_from_clean_start_saves_and_selects -q`

Expected: PASS.

### Task 4: Regression Verification

**Files:**
- Test: `python-app/tests/test_test_runner_view.py`
- Test: full test suite

- [ ] **Step 1: Run the PhoneShell/Test Runner tests**

Run: `python -m pytest tests/test_test_runner_view.py -q`

Expected: all tests pass.

- [ ] **Step 2: Run the full test suite**

Run: `python -m pytest -q`

Expected: all tests pass.

- [ ] **Step 3: Build the packaged executable**

Run from `python-app`: `powershell -ExecutionPolicy Bypass -File build/build_windows.ps1 -SkipNativeBuild`

Expected: `dist/NOC_Beam.exe`, `dist/NOC_Beam.exe.sha256`, packaged SIP smoke remains green when native build is included in the normal release path.

- [ ] **Step 4: Commit and push**

```bash
git add docs/superpowers/plans/2026-05-15-first-run-account-onboarding.md python-app/src/noc_beam/ui/phone_shell.py python-app/tests/test_test_runner_view.py
git commit -m "fix: expose first-run account setup"
git push origin claude/debug-error-Dlc4I
```
