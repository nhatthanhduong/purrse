from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from .database import Database
from .qt_controller import AppController


APP_NAME = "Purrse"


def data_directory() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    return (Path(base) if base else Path.home() / ".local" / "share") / APP_NAME


def main() -> None:
    QCoreApplication.setOrganizationName("Purrse")
    QCoreApplication.setApplicationName(APP_NAME)
    QQuickStyle.setStyle("Material")
    app = QGuiApplication(sys.argv)
    package_dir = Path(__file__).resolve().parent
    icon_path = package_dir / "assets" / "miso" / "idle.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    data_dir = data_directory()
    db = Database(data_dir / "purrse.db", data_dir / "attachments")
    controller = AppController(db, data_dir)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("Controller", controller)
    qml_path = package_dir / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        raise RuntimeError(f"Could not load Purrse interface from {qml_path}")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
