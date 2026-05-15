# Windows Packaged Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Windows executable more release-ready and apply default-shell accessibility settings live.

**Architecture:** Keep release metadata in build files, keep runtime accessibility behavior in `PhoneShell`, and test release configuration with lightweight text tests plus one Qt behavior test.

**Tech Stack:** PyInstaller, PowerShell, GitHub Actions, PySide6, pytest.

---

### Task 1: Release Metadata And Checksums

**Files:**
- Create: `python-app/build/version_info.txt`
- Modify: `python-app/build/noc_beam.spec`
- Modify: `python-app/build/build_windows.ps1`
- Modify: `.github/workflows/build-windows.yml`
- Test: `python-app/tests/test_windows_packaging.py`

- [ ] Add a PyInstaller `VSVersionInfo` file for `NOC_Beam 0.1.0`.
- [ ] Point `noc_beam.spec` `version=` at the version file.
- [ ] Change workflow dispatch default from `ui-only` to `full`.
- [ ] After a successful packaged smoke, write `dist/NOC_Beam.exe.sha256`.
- [ ] Upload both `NOC_Beam.exe` and `NOC_Beam.exe.sha256` in CI.
- [ ] Add tests that read the workflow/spec/version file and assert the defaults and metadata exist.

### Task 2: Live Accessibility Settings

**Files:**
- Modify: `python-app/src/noc_beam/ui/phone_shell.py`
- Modify: `python-app/tests/test_test_runner_view.py`

- [ ] Add `_apply_accessibility_settings()` to `PhoneShell`.
- [ ] Call it after settings are saved in `_on_settings()`.
- [ ] In the helper, call `apply_theme(QApplication.instance(), high_contrast, theme=theme)`.
- [ ] If `_wide_window` exists and has a drawer, call `drawer.set_reduced_motion(...)`.
- [ ] Add a Qt test that stubs `SettingsDialog`, accepts it, and asserts `apply_theme` receives the updated high-contrast value.

### Task 3: Focus Visibility

**Files:**
- Modify: `python-app/src/noc_beam/ui/resources/light.qss`
- Modify: `python-app/src/noc_beam/ui/resources/dark.qss`
- Modify: `python-app/src/noc_beam/ui/resources/dark-hc.qss`
- Test: `python-app/tests/test_windows_packaging.py`

- [ ] Replace bottom-tab `outline: none` with visible light-theme focus styling.
- [ ] Replace rail-button `outline: none` with visible dark and high-contrast focus styling.
- [ ] Add text tests that assert the old focus-hiding selectors are gone.

### Task 4: Verification

- [ ] Run focused tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_windows_packaging.py tests\test_test_runner_view.py::test_phone_shell_settings_apply_theme_live -q
```

- [ ] Run full tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

- [ ] Rebuild:

```powershell
powershell -ExecutionPolicy Bypass -File .\build\build_windows.ps1 -PythonExe .\.venv\Scripts\python.exe
```

- [ ] Verify `dist/NOC_Beam.exe.sha256` exists and packaged SIP smoke still passes.
- [ ] Commit and push:

```powershell
git add -- .github/workflows/build-windows.yml python-app/build/build_windows.ps1 python-app/build/noc_beam.spec python-app/build/version_info.txt python-app/src/noc_beam/ui/phone_shell.py python-app/src/noc_beam/ui/resources/light.qss python-app/src/noc_beam/ui/resources/dark.qss python-app/src/noc_beam/ui/resources/dark-hc.qss python-app/tests/test_windows_packaging.py python-app/tests/test_test_runner_view.py
git commit -m "feat: harden windows packaged readiness"
git push origin claude/debug-error-Dlc4I
```

## Self-Review

- Spec coverage: release defaults/checksum/version metadata in Task 1, live accessibility in Task 2, focus rings in Task 3, rebuild verification in Task 4.
- Placeholder scan: no TBD/TODO placeholders remain.
- Type consistency: `PhoneShell._apply_accessibility_settings()` uses existing `self.settings.appearance` fields.
