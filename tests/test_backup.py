from datetime import date

from purrse.backup import create_backup, restore_backup, validate_backup
from purrse.database import Database
from PIL import Image


def test_backup_round_trip(tmp_path):
    source_dir = tmp_path / "source"
    db = Database(source_dir / "purrse.db", source_dir / "attachments")
    month_id = db.ensure_month(2026, 9)
    tx_id = db.add_transaction(month_id, date(2026, 9, 1), "expense", "Groceries", 50_000)
    receipt = tmp_path / "receipt.txt"
    receipt.write_text("receipt", encoding="utf-8")
    db.add_attachment(tx_id, receipt)
    balance = tmp_path / "balance.png"
    Image.new("RGB", (40, 30), "white").save(balance)
    db.add_month_attachment(month_id, balance, "Closing balance")
    archive = create_backup(db.db_path, db.attachment_dir, tmp_path / "backup.zip")
    assert validate_backup(archive)["format"] == "purrse-backup"

    target_dir = tmp_path / "target"
    restore_backup(archive, target_dir / "purrse.db", target_dir / "attachments")
    restored = Database(target_dir / "purrse.db", target_dir / "attachments")
    assert restored.summary(month_id).expenses == 50_000
    assert len(list((target_dir / "attachments").iterdir())) == 2
    assert restored.month_attachments(month_id)[0]["caption"] == "Closing balance"
