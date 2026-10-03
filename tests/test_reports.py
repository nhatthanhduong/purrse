from datetime import date
from zipfile import ZipFile

import pytest

pytest.importorskip("docx")
pytest.importorskip("reportlab")

from purrse.database import Database
from purrse.reports import export_docx, export_pdf
from PIL import Image


def test_docx_and_pdf_exports(tmp_path):
    db = Database(tmp_path / "purrse.db", tmp_path / "attachments")
    month_id = db.ensure_month(2026, 9, 1_000_000, 0, 500_000)
    db.add_transaction(month_id, date(2026, 9, 1), "income", "Salary", 2_000_000, "Thưởng tháng")
    expense_id = db.add_transaction(month_id, date(2026, 9, 2), "expense", "Groceries", 750_000, "Đi chợ")
    receipt = tmp_path / "receipt.png"
    Image.new("RGB", (120, 80), "pink").save(receipt)
    db.add_attachment(expense_id, receipt)
    balance = tmp_path / "balance.webp"
    Image.new("RGB", (180, 100), "lavender").save(balance)
    db.add_month_attachment(month_id, balance, "Confirmed closing bank balance")
    db.save_note(month_id, "A useful month — cố gắng tiếp.")

    docx_path = export_docx(db, month_id, tmp_path / "report.docx")
    pdf_path = export_pdf(db, month_id, tmp_path / "report.pdf")

    assert docx_path.stat().st_size > 1_000
    with ZipFile(docx_path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
        assert "Thưởng tháng" in xml
        assert "Monthly evidence gallery" in xml
        assert "Confirmed closing bank balance" in xml
        assert any(name.startswith("word/media/") for name in archive.namelist())
    assert pdf_path.read_bytes().startswith(b"%PDF")
    assert pdf_path.stat().st_size > 1_000
