import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine

from purrse.database import Database
from purrse.qt_controller import AppController


def test_qml_shell_loads(qapp, tmp_path):
    db = Database(tmp_path / "purrse.db", tmp_path / "attachments")
    db.set_setting("sound_enabled", "0")
    db.ensure_month(2026, 9, target=100_000)
    controller = AppController(db, tmp_path)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("Controller", controller)
    qml = Path(__file__).parents[1] / "src" / "purrse" / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml)))
    assert engine.rootObjects()
    assert controller.summary["targetText"] == "100k"
    engine.deleteLater()
