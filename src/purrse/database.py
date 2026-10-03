from __future__ import annotations

import shutil
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterator


KINDS = ("income", "expense", "borrowed", "repayment")


@dataclass(frozen=True)
class MonthSummary:
    month_id: int
    year: int
    month: int
    status: str
    opening_bank: int
    opening_debt: int
    target_savings: int
    income: int
    expenses: int
    borrowed: int
    repayments: int
    expected_bank: int
    expected_debt: int
    savings: int
    actual_bank: int | None
    actual_debt: int | None
    bank_adjustment: int
    debt_adjustment: int
    note: str


class Database:
    def __init__(self, db_path: Path, attachment_dir: Path):
        self.db_path = Path(db_path)
        self.attachment_dir = Path(attachment_dir)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.attachment_dir.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_info (
                    version INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS months (
                    id INTEGER PRIMARY KEY,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
                    status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','closed')),
                    opening_bank INTEGER NOT NULL DEFAULT 0,
                    opening_debt INTEGER NOT NULL DEFAULT 0 CHECK(opening_debt >= 0),
                    target_savings INTEGER NOT NULL DEFAULT 0 CHECK(target_savings >= 0),
                    actual_bank INTEGER,
                    actual_debt INTEGER CHECK(actual_debt IS NULL OR actual_debt >= 0),
                    note TEXT NOT NULL DEFAULT '',
                    closed_at TEXT,
                    UNIQUE(year, month)
                );
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL COLLATE NOCASE,
                    kind TEXT NOT NULL CHECK(kind IN ('income','expense','borrowed','repayment')),
                    active INTEGER NOT NULL DEFAULT 1,
                    UNIQUE(name, kind)
                );
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY,
                    month_id INTEGER NOT NULL REFERENCES months(id) ON DELETE CASCADE,
                    tx_date TEXT NOT NULL,
                    kind TEXT NOT NULL CHECK(kind IN ('income','expense','borrowed','repayment')),
                    category TEXT NOT NULL,
                    amount_vnd INTEGER NOT NULL CHECK(amount_vnd >= 0),
                    description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_transactions_month ON transactions(month_id, tx_date);
                CREATE TABLE IF NOT EXISTS attachments (
                    id INTEGER PRIMARY KEY,
                    transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
                    original_name TEXT NOT NULL,
                    stored_name TEXT NOT NULL UNIQUE,
                    mime_type TEXT NOT NULL DEFAULT 'application/octet-stream',
                    caption TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS month_attachments (
                    id INTEGER PRIMARY KEY,
                    month_id INTEGER NOT NULL REFERENCES months(id) ON DELETE CASCADE,
                    original_name TEXT NOT NULL,
                    stored_name TEXT NOT NULL UNIQUE,
                    mime_type TEXT NOT NULL,
                    caption TEXT NOT NULL DEFAULT '',
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_month_attachments_order
                    ON month_attachments(month_id, sort_order, id);
                """
            )
            if db.execute("SELECT COUNT(*) FROM schema_info").fetchone()[0] == 0:
                db.execute("INSERT INTO schema_info(version) VALUES (2)")
            else:
                db.execute("UPDATE schema_info SET version=2")
            defaults = {
                "income": ["Salary", "Bonus", "Gift", "Refund", "Other income"],
                "expense": ["Groceries", "Bills", "Transport", "Healthcare", "Dining", "Entertainment", "Shopping", "Other expense"],
                "borrowed": ["Loan", "Credit", "Family/Friend"],
                "repayment": ["Loan repayment", "Credit repayment", "Family/Friend repayment"],
            }
            for kind, names in defaults.items():
                db.executemany(
                    "INSERT OR IGNORE INTO categories(name, kind) VALUES (?, ?)",
                    [(name, kind) for name in names],
                )

    def setting(self, key: str, default: str | None = None) -> str | None:
        with self.connect() as db:
            row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return row[0] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    def ensure_month(self, year: int, month: int, opening_bank: int = 0, opening_debt: int = 0, target: int = 0) -> int:
        with self.connect() as db:
            row = db.execute("SELECT id FROM months WHERE year=? AND month=?", (year, month)).fetchone()
            if row:
                return int(row[0])
            db.execute(
                "INSERT INTO months(year,month,opening_bank,opening_debt,target_savings) VALUES(?,?,?,?,?)",
                (year, month, opening_bank, opening_debt, target),
            )
            return int(db.execute("SELECT last_insert_rowid()").fetchone()[0])

    def get_month(self, year: int, month: int) -> sqlite3.Row | None:
        with self.connect() as db:
            return db.execute("SELECT * FROM months WHERE year=? AND month=?", (year, month)).fetchone()

    def list_months(self) -> list[sqlite3.Row]:
        with self.connect() as db:
            return db.execute("SELECT * FROM months ORDER BY year DESC, month DESC").fetchall()

    def categories(self, kind: str) -> list[str]:
        with self.connect() as db:
            return [r[0] for r in db.execute("SELECT name FROM categories WHERE kind=? AND active=1 ORDER BY name", (kind,))]

    def add_category(self, name: str, kind: str) -> None:
        name = name.strip()
        if not name:
            raise ValueError("Category cannot be empty.")
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO categories(name,kind) VALUES(?,?)", (name, kind))

    def add_transaction(self, month_id: int, tx_date: date, kind: str, category: str, amount_vnd: int, description: str = "") -> int:
        if kind not in KINDS:
            raise ValueError("Unknown entry type.")
        self._assert_open_month(month_id)
        self._assert_date_in_month(month_id, tx_date)
        if kind == "repayment" and amount_vnd > self.summary(month_id).expected_debt:
            raise ValueError("This repayment is larger than the remaining debt.")
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as db:
            db.execute(
                "INSERT INTO transactions(month_id,tx_date,kind,category,amount_vnd,description,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                (month_id, tx_date.isoformat(), kind, category.strip(), amount_vnd, description.strip(), now, now),
            )
            return int(db.execute("SELECT last_insert_rowid()").fetchone()[0])

    def update_transaction(self, transaction_id: int, tx_date: date, kind: str, category: str, amount_vnd: int, description: str) -> None:
        with self.connect() as db:
            row = db.execute("SELECT month_id,kind,amount_vnd FROM transactions WHERE id=?", (transaction_id,)).fetchone()
        if not row:
            raise ValueError("Entry no longer exists.")
        self._assert_open_month(row[0])
        self._assert_date_in_month(row[0], tx_date)
        current_debt = self.summary(row[0]).expected_debt
        if row["kind"] == "borrowed":
            current_debt -= row["amount_vnd"]
        elif row["kind"] == "repayment":
            current_debt += row["amount_vnd"]
        projected_debt = current_debt + (amount_vnd if kind == "borrowed" else -amount_vnd if kind == "repayment" else 0)
        if projected_debt < 0:
            raise ValueError("This repayment is larger than the remaining debt.")
        with self.connect() as db:
            db.execute(
                "UPDATE transactions SET tx_date=?,kind=?,category=?,amount_vnd=?,description=?,updated_at=? WHERE id=?",
                (tx_date.isoformat(), kind, category.strip(), amount_vnd, description.strip(), datetime.now().isoformat(timespec="seconds"), transaction_id),
            )

    def delete_transaction(self, transaction_id: int) -> None:
        with self.connect() as db:
            row = db.execute("SELECT month_id,kind,amount_vnd FROM transactions WHERE id=?", (transaction_id,)).fetchone()
            attachments = db.execute("SELECT stored_name FROM attachments WHERE transaction_id=?", (transaction_id,)).fetchall()
        if not row:
            return
        self._assert_open_month(row[0])
        if row["kind"] == "borrowed" and self.summary(row["month_id"]).expected_debt < row["amount_vnd"]:
            raise ValueError("This borrowing entry cannot be deleted because later repayments depend on it.")
        with self.connect() as db:
            db.execute("DELETE FROM transactions WHERE id=?", (transaction_id,))
        for item in attachments:
            (self.attachment_dir / item[0]).unlink(missing_ok=True)

    def list_transactions(self, month_id: int, search: str = "") -> list[sqlite3.Row]:
        with self.connect() as db:
            if search.strip():
                token = f"%{search.strip()}%"
                return db.execute(
                    "SELECT * FROM transactions WHERE month_id=? AND (category LIKE ? OR description LIKE ?) ORDER BY tx_date,id",
                    (month_id, token, token),
                ).fetchall()
            return db.execute("SELECT * FROM transactions WHERE month_id=? ORDER BY tx_date,id", (month_id,)).fetchall()

    def transaction(self, transaction_id: int) -> sqlite3.Row | None:
        with self.connect() as db:
            return db.execute("SELECT * FROM transactions WHERE id=?", (transaction_id,)).fetchone()

    def add_attachment(self, transaction_id: int, source: Path, caption: str = "") -> int:
        source = Path(source)
        if not source.is_file():
            raise ValueError("Attachment could not be found.")
        suffix = source.suffix.lower()
        stored_name = f"{uuid.uuid4().hex}{suffix}"
        shutil.copy2(source, self.attachment_dir / stored_name)
        import mimetypes
        mime = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
        try:
            with self.connect() as db:
                db.execute(
                    "INSERT INTO attachments(transaction_id,original_name,stored_name,mime_type,caption,created_at) VALUES(?,?,?,?,?,?)",
                    (transaction_id, source.name, stored_name, mime, caption.strip(), datetime.now().isoformat(timespec="seconds")),
                )
                return int(db.execute("SELECT last_insert_rowid()").fetchone()[0])
        except Exception:
            (self.attachment_dir / stored_name).unlink(missing_ok=True)
            raise

    def attachments_for_transaction(self, transaction_id: int) -> list[sqlite3.Row]:
        with self.connect() as db:
            return db.execute("SELECT * FROM attachments WHERE transaction_id=? ORDER BY id", (transaction_id,)).fetchall()

    def attachments_for_month(self, month_id: int) -> list[sqlite3.Row]:
        with self.connect() as db:
            return db.execute(
                "SELECT a.*,t.tx_date,t.description,t.category FROM attachments a JOIN transactions t ON t.id=a.transaction_id WHERE t.month_id=? ORDER BY t.tx_date,a.id",
                (month_id,),
            ).fetchall()

    def add_month_attachment(self, month_id: int, source: Path, caption: str = "") -> int:
        """Copy a validated image into the managed store and attach it to a month."""
        source = Path(source)
        if not source.is_file():
            raise ValueError("Image could not be found.")
        try:
            from PIL import Image
            with Image.open(source) as image:
                image.verify()
                detected_format = (image.format or "").upper()
        except Exception as exc:
            raise ValueError(f"{source.name} is not a readable image.") from exc
        allowed = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp", "BMP": "image/bmp", "TIFF": "image/tiff", "GIF": "image/gif"}
        if detected_format not in allowed:
            raise ValueError("Use a JPEG, PNG, WebP, BMP, TIFF, or GIF image.")
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM months WHERE id=?", (month_id,)).fetchone():
                raise ValueError("Month not found.")
            order = db.execute("SELECT COALESCE(MAX(sort_order),-1)+1 FROM month_attachments WHERE month_id=?", (month_id,)).fetchone()[0]
        stored_name = f"{uuid.uuid4().hex}{source.suffix.lower()}"
        shutil.copy2(source, self.attachment_dir / stored_name)
        now = datetime.now().isoformat(timespec="seconds")
        try:
            with self.connect() as db:
                db.execute(
                    "INSERT INTO month_attachments(month_id,original_name,stored_name,mime_type,caption,sort_order,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                    (month_id, source.name, stored_name, allowed[detected_format], caption.strip(), order, now, now),
                )
                return int(db.execute("SELECT last_insert_rowid()").fetchone()[0])
        except Exception:
            (self.attachment_dir / stored_name).unlink(missing_ok=True)
            raise

    def month_attachments(self, month_id: int) -> list[sqlite3.Row]:
        with self.connect() as db:
            return db.execute(
                "SELECT * FROM month_attachments WHERE month_id=? ORDER BY sort_order,id", (month_id,)
            ).fetchall()

    def update_month_attachment_caption(self, attachment_id: int, caption: str) -> None:
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM month_attachments WHERE id=?", (attachment_id,)).fetchone():
                raise ValueError("Monthly image not found.")
            db.execute(
                "UPDATE month_attachments SET caption=?,updated_at=? WHERE id=?",
                (caption.strip(), datetime.now().isoformat(timespec="seconds"), attachment_id),
            )

    def reorder_month_attachment(self, month_id: int, attachment_id: int, new_index: int) -> None:
        rows = self.month_attachments(month_id)
        ids = [int(row["id"]) for row in rows]
        if attachment_id not in ids:
            raise ValueError("Monthly image not found.")
        ids.remove(attachment_id)
        ids.insert(max(0, min(new_index, len(ids))), attachment_id)
        with self.connect() as db:
            db.executemany("UPDATE month_attachments SET sort_order=? WHERE id=?", [(index, item_id) for index, item_id in enumerate(ids)])

    def delete_month_attachment(self, attachment_id: int) -> None:
        with self.connect() as db:
            row = db.execute("SELECT stored_name FROM month_attachments WHERE id=?", (attachment_id,)).fetchone()
            if not row:
                return
            db.execute("DELETE FROM month_attachments WHERE id=?", (attachment_id,))
        (self.attachment_dir / row["stored_name"]).unlink(missing_ok=True)

    def save_note(self, month_id: int, note: str) -> None:
        self._assert_open_month(month_id)
        with self.connect() as db:
            db.execute("UPDATE months SET note=? WHERE id=?", (note.strip(), month_id))

    def set_target(self, month_id: int, target_savings: int) -> None:
        self._assert_open_month(month_id)
        if target_savings < 0:
            raise ValueError("Savings target cannot be negative.")
        with self.connect() as db:
            db.execute("UPDATE months SET target_savings=? WHERE id=?", (target_savings, month_id))

    def summary(self, month_id: int) -> MonthSummary:
        with self.connect() as db:
            month = db.execute("SELECT * FROM months WHERE id=?", (month_id,)).fetchone()
            if not month:
                raise ValueError("Month not found.")
            totals = {kind: 0 for kind in KINDS}
            for row in db.execute("SELECT kind,COALESCE(SUM(amount_vnd),0) total FROM transactions WHERE month_id=? GROUP BY kind", (month_id,)):
                totals[row[0]] = int(row[1])
        expected_bank = month["opening_bank"] + totals["income"] - totals["expense"] + totals["borrowed"] - totals["repayment"]
        expected_debt = max(0, month["opening_debt"] + totals["borrowed"] - totals["repayment"])
        bank_adjustment = 0 if month["actual_bank"] is None else month["actual_bank"] - expected_bank
        debt_adjustment = 0 if month["actual_debt"] is None else month["actual_debt"] - expected_debt
        return MonthSummary(
            month["id"], month["year"], month["month"], month["status"], month["opening_bank"], month["opening_debt"],
            month["target_savings"], totals["income"], totals["expense"], totals["borrowed"], totals["repayment"],
            expected_bank, expected_debt, totals["income"] - totals["expense"], month["actual_bank"], month["actual_debt"],
            bank_adjustment, debt_adjustment, month["note"],
        )

    def category_totals(self, month_id: int, kind: str = "expense") -> list[tuple[str, int]]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT category,SUM(amount_vnd) total FROM transactions WHERE month_id=? AND kind=? GROUP BY category ORDER BY total DESC",
                (month_id, kind),
            ).fetchall()
            return [(r[0], int(r[1])) for r in rows]

    def previous_summary(self, year: int, month: int) -> MonthSummary | None:
        if month == 1:
            year, month = year - 1, 12
        else:
            month -= 1
        row = self.get_month(year, month)
        return self.summary(row["id"]) if row else None

    def close_month(self, month_id: int, actual_bank: int, actual_debt: int) -> int:
        self._assert_open_month(month_id)
        if actual_debt < 0:
            raise ValueError("Debt cannot be negative.")
        with self.connect() as db:
            month = db.execute("SELECT * FROM months WHERE id=?", (month_id,)).fetchone()
            db.execute(
                "UPDATE months SET status='closed',actual_bank=?,actual_debt=?,closed_at=? WHERE id=?",
                (actual_bank, actual_debt, datetime.now().isoformat(timespec="seconds"), month_id),
            )
            next_year, next_month = (month["year"] + 1, 1) if month["month"] == 12 else (month["year"], month["month"] + 1)
            existing = db.execute("SELECT id FROM months WHERE year=? AND month=?", (next_year, next_month)).fetchone()
            if existing:
                return int(existing[0])
            db.execute(
                "INSERT INTO months(year,month,opening_bank,opening_debt,target_savings) VALUES(?,?,?,?,?)",
                (next_year, next_month, actual_bank, actual_debt, month["target_savings"]),
            )
            return int(db.execute("SELECT last_insert_rowid()").fetchone()[0])

    def reopen_month(self, month_id: int) -> None:
        with self.connect() as db:
            month = db.execute("SELECT * FROM months WHERE id=?", (month_id,)).fetchone()
            if not month or month["status"] != "closed":
                raise ValueError("This month is not closed.")
            later = db.execute(
                "SELECT m.id,(SELECT COUNT(*) FROM transactions t WHERE t.month_id=m.id) count FROM months m WHERE (m.year>? OR (m.year=? AND m.month>?)) ORDER BY m.year,m.month LIMIT 1",
                (month["year"], month["year"], month["month"]),
            ).fetchone()
            if later and later["count"] > 0:
                raise ValueError("A later month already has entries. Add a correction there instead.")
            db.execute("UPDATE months SET status='open',actual_bank=NULL,actual_debt=NULL,closed_at=NULL WHERE id=?", (month_id,))
            if later:
                db.execute("DELETE FROM months WHERE id=?", (later["id"],))

    def _assert_open_month(self, month_id: int) -> None:
        with self.connect() as db:
            row = db.execute("SELECT status FROM months WHERE id=?", (month_id,)).fetchone()
        if not row:
            raise ValueError("Month not found.")
        if row[0] != "open":
            raise ValueError("Closed months are read-only.")

    def _assert_date_in_month(self, month_id: int, tx_date: date) -> None:
        with self.connect() as db:
            row = db.execute("SELECT year,month FROM months WHERE id=?", (month_id,)).fetchone()
        if not row or (tx_date.year, tx_date.month) != (row[0], row[1]):
            raise ValueError("The entry date must be inside the selected month.")
