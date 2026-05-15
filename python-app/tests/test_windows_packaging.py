from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_workflow_manual_dispatch_defaults_to_full_native_build() -> None:
    workflow = (ROOT / ".github" / "workflows" / "build-windows.yml").read_text(
        encoding="utf-8"
    )

    assert "default: full" in workflow
    assert "default: ui-only" not in workflow


def test_pyinstaller_uses_windows_version_metadata() -> None:
    spec = (ROOT / "python-app" / "build" / "noc_beam.spec").read_text(
        encoding="utf-8"
    )
    version_info = (ROOT / "python-app" / "build" / "version_info.txt").read_text(
        encoding="utf-8"
    )

    assert "VERSION_INFO" in spec
    assert "version=str(VERSION_INFO)" in spec
    assert "FileDescription" in version_info
    assert "ProductName" in version_info
    assert "NOC_Beam SIP NOC test tool" in version_info
    assert "ProductVersion', '0.1.0.0'" in version_info


def test_build_script_writes_sha256_sidecar() -> None:
    script = (ROOT / "python-app" / "build" / "build_windows.ps1").read_text(
        encoding="utf-8"
    )

    assert "Get-FileHash -LiteralPath $ExePath -Algorithm SHA256" in script
    assert '"$($ExeHash.Hash)  NOC_Beam.exe"' in script
    assert "NOC_Beam.exe.sha256" in (
        ROOT / ".github" / "workflows" / "build-windows.yml"
    ).read_text(encoding="utf-8")


def test_focus_hiding_removed_from_primary_navigation_styles() -> None:
    light = (ROOT / "python-app" / "src" / "noc_beam" / "ui" / "resources" / "light.qss").read_text(
        encoding="utf-8"
    )
    dark = (ROOT / "python-app" / "src" / "noc_beam" / "ui" / "resources" / "dark.qss").read_text(
        encoding="utf-8"
    )
    high_contrast = (
        ROOT / "python-app" / "src" / "noc_beam" / "ui" / "resources" / "dark-hc.qss"
    ).read_text(encoding="utf-8")

    assert "QToolButton#TabBtn:focus { outline: none; }" not in light
    assert "QToolButton#RailBtn:focus { outline: none; }" not in dark
    assert "QToolButton#RailBtn:focus { outline: none; }" not in high_contrast
    assert "QToolButton#TabBtn:focus" in light
    assert "QToolButton#RailBtn:focus" in dark
    assert "QToolButton#RailBtn:focus" in high_contrast
