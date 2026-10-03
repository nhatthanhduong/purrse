from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path


BACKUP_VERSION = 1


def create_backup(db_path: Path, attachment_dir: Path, destination: Path) -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        temp = Path(temporary)
        snapshot = temp / "purrse.db"
        source = sqlite3.connect(db_path)
        target = sqlite3.connect(snapshot)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        manifest = {
            "format": "purrse-backup",
            "version": BACKUP_VERSION,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        (temp / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(snapshot, "purrse.db")
            archive.write(temp / "manifest.json", "manifest.json")
            if attachment_dir.exists():
                for path in attachment_dir.iterdir():
                    if path.is_file():
                        archive.write(path, f"attachments/{path.name}")
    return destination


def validate_backup(source: Path) -> dict:
    try:
        with zipfile.ZipFile(source) as archive:
            names = set(archive.namelist())
            if "manifest.json" not in names or "purrse.db" not in names:
                raise ValueError("This is not a complete Purrse backup.")
            manifest = json.loads(archive.read("manifest.json"))
            if manifest.get("format") != "purrse-backup" or manifest.get("version") != BACKUP_VERSION:
                raise ValueError("This backup version is not supported.")
            with tempfile.TemporaryDirectory() as temporary:
                db_file = Path(temporary) / "check.db"
                db_file.write_bytes(archive.read("purrse.db"))
                with sqlite3.connect(db_file) as db:
                    result = db.execute("PRAGMA integrity_check").fetchone()[0]
                    if result != "ok":
                        raise ValueError("The database in this backup is damaged.")
                    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    if not {"months", "transactions", "attachments"}.issubset(tables):
                        raise ValueError("The backup database is missing required data.")
            return manifest
    except (zipfile.BadZipFile, json.JSONDecodeError) as exc:
        raise ValueError("The selected file is not a valid Purrse backup.") from exc


def restore_backup(source: Path, db_path: Path, attachment_dir: Path) -> None:
    validate_backup(source)
    with tempfile.TemporaryDirectory() as temporary:
        temp = Path(temporary)
        with zipfile.ZipFile(source) as archive:
            (temp / "purrse.db").write_bytes(archive.read("purrse.db"))
            extracted_attachments = temp / "attachments"
            extracted_attachments.mkdir()
            for name in archive.namelist():
                if name.startswith("attachments/") and not name.endswith("/"):
                    safe_name = Path(name).name
                    if safe_name and name == f"attachments/{safe_name}":
                        (extracted_attachments / safe_name).write_bytes(archive.read(name))
        replacement = temp / "purrse.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        Path(f"{db_path}-wal").unlink(missing_ok=True)
        Path(f"{db_path}-shm").unlink(missing_ok=True)
        shutil.copy2(replacement, db_path)
        if attachment_dir.exists():
            shutil.rmtree(attachment_dir)
        extracted = temp / "attachments"
        if extracted.exists():
            shutil.copytree(extracted, attachment_dir)
        else:
            attachment_dir.mkdir(parents=True, exist_ok=True)
