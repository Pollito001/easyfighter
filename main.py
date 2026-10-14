#!/usr/bin/env python3
"""IKEMEN GO Character Editor — editor de personajes para IKEMEN GO."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PyQt6.QtWidgets import QApplication  # noqa: E402

import i18n  # noqa: E402,F401
from ui.common import APP_NAME  # noqa: E402


def main():
    if getattr(sys, "frozen", False) and sys.platform.startswith("linux"):
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    icon = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "icon.png"
    if icon.is_file():
        from PyQt6.QtGui import QIcon
        app.setWindowIcon(QIcon(str(icon)))
    from ui import theme
    theme.apply(app)
    from ui.mainwindow import MainWindow
    w = MainWindow()
    w.show()
    args = [a for a in sys.argv[1:] if a.lower().endswith(".def")]
    if args:
        w.open_project(args[0])
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
