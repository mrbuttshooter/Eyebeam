from pathlib import Path

from tools.ui_smoke import screenshot_path


def test_screenshot_path_uses_theme_and_page(tmp_path: Path) -> None:
    path = screenshot_path(tmp_path, "light", "dial")
    assert path == tmp_path / "light-dial.png"
