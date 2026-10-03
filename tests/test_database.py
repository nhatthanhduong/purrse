from datetime import date

import pytest

from purrse.database import Database


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "purrse.db", tmp_path / "attachments")


def test_month_summary_and_rollover(db):
    month_id = db.ensure_month(2026, 9, 10_000_000, 3_000_000, 2_000_000)
    db.add_transaction(month_id, date(2026, 9, 1), "income", "Salary", 8_000_000)
    db.add_transaction(month_id, date(2026, 9, 2), "expense", "Groceries", 1_500_000)
    db.add_transaction(month_id, date(2026, 9, 3), "borrowed", "Loan", 500_000)
    db.add_transaction(month_id, date(2026, 9, 4), "repayment", "Loan repayment", 1_000_000)

    summary = db.summary(month_id)
    assert summary.savings == 6_500_000
    assert summary.expected_bank == 16_000_000
    assert summary.expected_debt == 2_500_000

    next_id = db.close_month(month_id, 15_900_000, 2_450_000)
    closed = db.summary(month_id)
    following = db.summary(next_id)
    assert closed.bank_adjustment == -100_000
    assert closed.debt_adjustment == -50_000
    assert following.opening_bank == 15_900_000
    assert following.opening_debt == 2_450_000
    assert following.target_savings == 2_000_000


def test_entries_must_match_month_and_open_status(db):
    month_id = db.ensure_month(2026, 9)
    with pytest.raises(ValueError, match="inside the selected month"):
        db.add_transaction(month_id, date(2026, 10, 1), "expense", "Other", 1_000)
    db.close_month(month_id, 0, 0)
    with pytest.raises(ValueError, match="read-only"):
        db.add_transaction(month_id, date(2026, 9, 1), "expense", "Other", 1_000)


def test_repayment_cannot_make_debt_negative(db):
    month_id = db.ensure_month(2026, 9, opening_debt=100_000)
    with pytest.raises(ValueError, match="larger"):
        db.add_transaction(month_id, date(2026, 9, 1), "repayment", "Repayment", 101_000)


def test_borrowing_cannot_be_deleted_when_repayment_depends_on_it(db):
    month_id = db.ensure_month(2026, 9)
    borrowed_id = db.add_transaction(month_id, date(2026, 9, 1), "borrowed", "Loan", 100_000)
    db.add_transaction(month_id, date(2026, 9, 2), "repayment", "Repayment", 100_000)
    with pytest.raises(ValueError, match="depend"):
        db.delete_transaction(borrowed_id)


def test_reopen_only_before_later_entries(db):
    month_id = db.ensure_month(2026, 9)
    next_id = db.close_month(month_id, 0, 0)
    db.add_transaction(next_id, date(2026, 10, 1), "income", "Salary", 10_000)
    with pytest.raises(ValueError, match="later month"):
        db.reopen_month(month_id)


def test_open_month_target_can_be_changed_and_carries_forward(db):
    month_id = db.ensure_month(2026, 9, target=100_000)
    db.set_target(month_id, 250_000)
    next_id = db.close_month(month_id, 0, 0)
    assert db.summary(next_id).target_savings == 250_000
    with pytest.raises(ValueError, match="read-only"):
        db.set_target(month_id, 300_000)


def test_month_images_are_ordered_and_remain_editable_after_close(db, tmp_path):
    from PIL import Image
    month_id = db.ensure_month(2026, 9)
    first = tmp_path / "bank.png"
    second = tmp_path / "debt.jpg"
    Image.new("RGB", (80, 50), "pink").save(first)
    Image.new("RGB", (60, 90), "skyblue").save(second)
    first_id = db.add_month_attachment(month_id, first, "Opening balance")
    db.close_month(month_id, 0, 0)
    second_id = db.add_month_attachment(month_id, second, "Closing debt")
    db.reorder_month_attachment(month_id, second_id, 0)
    db.update_month_attachment_caption(first_id, "Confirmed bank balance")
    rows = db.month_attachments(month_id)
    assert [row["id"] for row in rows] == [second_id, first_id]
    assert rows[1]["caption"] == "Confirmed bank balance"


def test_month_attachment_rejects_non_image(db, tmp_path):
    month_id = db.ensure_month(2026, 9)
    fake = tmp_path / "not-image.png"
    fake.write_text("not an image", encoding="utf-8")
    with pytest.raises(ValueError, match="readable image"):
        db.add_month_attachment(month_id, fake)
