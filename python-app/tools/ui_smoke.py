from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

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
    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("screenshots-for-review")
    capture_shell(output_dir, "light", False)
    capture_shell(output_dir, "dark", False)
    capture_shell(output_dir, "light", True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
