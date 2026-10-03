from __future__ import annotations

import calendar
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, Property, Qt, QUrl, Signal, Slot

from .backup import create_backup, restore_backup, validate_backup
from .database import Database
from .insights import generate_insights, mascot_mood
from .money import format_k, parse_signed_thousand_vnd, parse_thousand_vnd
from .reports import export_docx, export_pdf


def _local_path(value: str) -> Path:
    url = QUrl(value)
    return Path(url.toLocalFile()) if url.isLocalFile() else Path(value)


class EntryListModel(QAbstractListModel):
    IdRole, DateRole, KindRole, CategoryRole, DescriptionRole, AmountRole, AmountRawRole, FilesRole = range(Qt.UserRole + 1, Qt.UserRole + 9)
    roles = {
        IdRole: b"entryId", DateRole: b"entryDate", KindRole: b"entryKind", CategoryRole: b"category",
        DescriptionRole: b"description", AmountRole: b"amount", AmountRawRole: b"amountRaw", FilesRole: b"fileCount",
    }

    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.rows: list[dict[str, Any]] = []

    def roleNames(self):  # noqa: N802 - Qt API
        return self.roles

    def rowCount(self, parent=QModelIndex()):  # noqa: N802 - Qt API
        return 0 if parent.isValid() else len(self.rows)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self.rows):
            return None
        row = self.rows[index.row()]
        keys = {self.IdRole: "id", self.DateRole: "date", self.KindRole: "kind", self.CategoryRole: "category", self.DescriptionRole: "description", self.AmountRole: "amount", self.AmountRawRole: "amount_raw", self.FilesRole: "files"}
        return row.get(keys.get(role, ""))

    def refresh(self, month_id: int | None, search: str = "") -> None:
        self.beginResetModel()
        self.rows = []
        if month_id:
            for tx in self.db.list_transactions(month_id, search):
                self.rows.append({
                    "id": tx["id"],
                    "date": datetime.strptime(tx["tx_date"], "%Y-%m-%d").strftime("%d-%m-%Y"),
                    "kind": tx["kind"], "category": tx["category"], "description": tx["description"],
                    "amount": format_k(tx["amount_vnd"]), "amount_raw": format_k(tx["amount_vnd"], False),
                    "files": len(self.db.attachments_for_transaction(tx["id"])),
                })
        self.endResetModel()

    @Slot(int, result="QVariantMap")
    def get(self, index: int) -> dict[str, Any]:
        return self.rows[index] if 0 <= index < len(self.rows) else {}


class MonthImageListModel(QAbstractListModel):
    IdRole, NameRole, CaptionRole, ImageRole, OrderRole = range(Qt.UserRole + 1, Qt.UserRole + 6)
    roles = {IdRole: b"imageId", NameRole: b"originalName", CaptionRole: b"caption", ImageRole: b"imageUrl", OrderRole: b"sortOrder"}

    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.rows: list[dict[str, Any]] = []

    def roleNames(self):  # noqa: N802
        return self.roles

    def rowCount(self, parent=QModelIndex()):  # noqa: N802
        return 0 if parent.isValid() else len(self.rows)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self.rows):
            return None
        keys = {self.IdRole: "id", self.NameRole: "name", self.CaptionRole: "caption", self.ImageRole: "url", self.OrderRole: "order"}
        return self.rows[index.row()].get(keys.get(role, ""))

    def refresh(self, month_id: int | None) -> None:
        self.beginResetModel()
        self.rows = []
        if month_id:
            for item in self.db.month_attachments(month_id):
                path = self.db.attachment_dir / item["stored_name"]
                self.rows.append({"id": item["id"], "name": item["original_name"], "caption": item["caption"], "url": QUrl.fromLocalFile(str(path)).toString(), "order": item["sort_order"]})
        self.endResetModel()

    @Slot(int, result="QVariantMap")
    def get(self, index: int) -> dict[str, Any]:
        return self.rows[index] if 0 <= index < len(self.rows) else {}


class SoundManager(QObject):
    def __init__(self, data_dir: Path):
        super().__init__()
        self.data_dir = data_dir
        self.enabled = True
        self.volume = 0.22
        self.effects: dict[str, Any] = {}
        self.pending: set[str] = set()
        self.initialized = False

    def _initialize(self) -> None:
        if self.initialized or os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            return
        self.initialized = True
        try:
            from PySide6.QtMultimedia import QSoundEffect
            sound_dir = Path(__file__).resolve().parent / "assets" / "sounds"
            for name in ("click", "pop", "whoosh", "celebrate", "meow"):
                path = sound_dir / f"{name}.wav"
                if not path.exists():
                    continue
                effect = QSoundEffect(self)
                effect.setSource(QUrl.fromLocalFile(str(path)))
                effect.setVolume(self.volume)
                effect.loadedChanged.connect(lambda sound_name=name: self._play_when_loaded(sound_name))
                self.effects[name] = effect
        except Exception:
            self.effects = {}

    def _play_when_loaded(self, name: str) -> None:
        effect = self.effects.get(name)
        if effect and name in self.pending and effect.isLoaded() and self.enabled:
            self.pending.discard(name)
            effect.play()

    def play(self, name: str) -> None:
        if self.enabled:
            self._initialize()
        if self.enabled and name in self.effects:
            effect = self.effects[name]
            if effect.isLoaded():
                effect.stop()
                effect.play()
            else:
                self.pending.add(name)

    def configure(self, enabled: bool, volume: float) -> None:
        self.enabled, self.volume = enabled, max(0.0, min(1.0, volume))
        if enabled:
            self._initialize()
        for effect in self.effects.values():
            effect.setVolume(self.volume)


class AppController(QObject):
    monthLabelsChanged = Signal()
    currentMonthIndexChanged = Signal()
    summaryChanged = Signal()
    settingsChanged = Signal()
    busyChanged = Signal()
    notice = Signal(str, str)
    mascotEvent = Signal(str, str, str)
    taskFinished = Signal(str, bool, str)

    def __init__(self, db: Database, data_dir: Path):
        super().__init__()
        self.db, self.data_dir = db, data_dir
        self.entries = EntryListModel(db)
        self.gallery = MonthImageListModel(db)
        self._months: list[Any] = []
        self._current_index = 0
        self._summary: dict[str, Any] = {}
        self._busy = False
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="purrse")
        self._sound_enabled = db.setting("sound_enabled", "1") == "1"
        self._volume = float(db.setting("sound_volume", "0.38") or 0.38)
        if db.setting("sound_asset_version", "1") != "2":
            if self._volume <= 0.22:
                self._volume = 0.38
                db.set_setting("sound_volume", str(self._volume))
            db.set_setting("sound_asset_version", "2")
        self._reduced_motion = db.setting("reduced_motion", "0") == "1"
        self.sounds = SoundManager(data_dir)
        self.sounds.configure(self._sound_enabled, self._volume)
        self.taskFinished.connect(self._finish_task)
        self.reload_months()

    @Property("QStringList", notify=monthLabelsChanged)
    def monthLabels(self):
        return [f"{calendar.month_name[row['month']]} {row['year']}" for row in self._months]

    @Property(int, notify=currentMonthIndexChanged)
    def currentMonthIndex(self):
        return self._current_index

    @currentMonthIndex.setter
    def currentMonthIndex(self, value: int):
        if 0 <= value < len(self._months) and value != self._current_index:
            self._current_index = value
            self.currentMonthIndexChanged.emit()
            self.refresh()

    @Property("QVariantMap", notify=summaryChanged)
    def summary(self):
        return self._summary

    @Property(QObject, constant=True)
    def entryModel(self):
        return self.entries

    @Property(QObject, constant=True)
    def galleryModel(self):
        return self.gallery

    @Property(bool, notify=busyChanged)
    def busy(self):
        return self._busy

    @Property(bool, notify=settingsChanged)
    def soundEnabled(self):
        return self._sound_enabled

    @Property(float, notify=settingsChanged)
    def soundVolume(self):
        return self._volume

    @Property(bool, notify=settingsChanged)
    def reducedMotion(self):
        return self._reduced_motion

    @Property(bool, notify=monthLabelsChanged)
    def needsSetup(self):
        return not self._months

    def current_month_id(self) -> int | None:
        return int(self._months[self._current_index]["id"]) if self._months else None

    def reload_months(self, select_id: int | None = None) -> None:
        self._months = self.db.list_months()
        if select_id is not None:
            self._current_index = next((i for i, row in enumerate(self._months) if row["id"] == select_id), 0)
        else:
            self._current_index = min(self._current_index, max(0, len(self._months) - 1))
        self.monthLabelsChanged.emit(); self.currentMonthIndexChanged.emit(); self.refresh()

    @Slot()
    def refresh(self) -> None:
        month_id = self.current_month_id()
        self.entries.refresh(month_id)
        self.gallery.refresh(month_id)
        if not month_id:
            self._summary = {}
            self.summaryChanged.emit()
            return
        summary = self.db.summary(month_id)
        categories = self.db.category_totals(month_id)
        insights = generate_insights(summary, self.db.previous_summary(summary.year, summary.month), categories)
        mood, message = mascot_mood(summary)
        closing_bank = summary.actual_bank if summary.actual_bank is not None else summary.expected_bank
        closing_debt = summary.actual_debt if summary.actual_debt is not None else summary.expected_debt
        target_percent = max(0, min(100, summary.savings * 100 / summary.target_savings)) if summary.target_savings else (100 if summary.savings > 0 else 0)
        self._summary = {
            "year": summary.year, "month": summary.month, "monthName": calendar.month_name[summary.month], "status": summary.status,
            "income": summary.income, "expenses": summary.expenses, "savings": summary.savings, "bank": closing_bank, "debt": closing_debt,
            "incomeText": format_k(summary.income), "expensesText": format_k(summary.expenses), "savingsText": format_k(summary.savings),
            "bankText": format_k(closing_bank), "debtText": format_k(closing_debt), "targetText": format_k(summary.target_savings),
            "target": summary.target_savings, "targetPercent": target_percent, "note": summary.note, "insights": insights,
            "categories": [{"label": name, "value": value, "text": format_k(value)} for name, value in categories],
            "mood": mood, "mascotMessage": message, "expectedBankText": format_k(summary.expected_bank), "expectedDebtText": format_k(summary.expected_debt),
            "actualBankInput": format_k(summary.expected_bank, False), "actualDebtInput": format_k(summary.expected_debt, False),
        }
        self.summaryChanged.emit()

    @Slot(str, str, str)
    def setup(self, bank: str, debt: str, target: str) -> None:
        try:
            today = date.today()
            month_id = self.db.ensure_month(today.year, today.month, parse_signed_thousand_vnd(bank), parse_thousand_vnd(debt), parse_thousand_vnd(target))
            self.reload_months(month_id)
            self._react("wave", "Welcome! Let’s make this month sparkle.", "celebrate")
        except ValueError as exc:
            self.notice.emit("Check the amounts", str(exc))

    @Slot(str, result="QStringList")
    def categoriesFor(self, kind: str):
        return self.db.categories(kind)

    @Slot(result=str)
    def suggestedDate(self):
        if not self._months:
            return date.today().strftime("%d-%m-%Y")
        row = self._months[self._current_index]
        day = min(date.today().day, calendar.monthrange(row["year"], row["month"])[1])
        return date(row["year"], row["month"], day).strftime("%d-%m-%Y")

    @staticmethod
    def _parse_date(text: str) -> date:
        try:
            return datetime.strptime(text.strip(), "%d-%m-%Y").date()
        except ValueError as exc:
            raise ValueError("Use a date in DD-MM-YYYY format.") from exc

    @Slot(str, str, str, str, str, "QVariantList")
    def addEntry(self, date_text: str, kind: str, category: str, amount: str, description: str, files: list) -> None:
        try:
            month_id = self.current_month_id()
            if not month_id:
                return
            self.db.add_category(category, kind)
            tx_id = self.db.add_transaction(month_id, self._parse_date(date_text), kind, category, parse_thousand_vnd(amount), description)
            for file in files:
                self.db.add_attachment(tx_id, _local_path(str(file)))
            self.refresh(); self._react("coin", "Saved! Every number makes the picture clearer.", "pop")
        except (ValueError, OSError) as exc:
            self.notice.emit("Could not save entry", str(exc))

    @Slot(int, str, str, str, str, str, "QVariantList")
    def updateEntry(self, entry_id: int, date_text: str, kind: str, category: str, amount: str, description: str, files: list) -> None:
        try:
            self.db.add_category(category, kind)
            self.db.update_transaction(entry_id, self._parse_date(date_text), kind, category, parse_thousand_vnd(amount), description)
            for file in files:
                self.db.add_attachment(entry_id, _local_path(str(file)))
            self.refresh(); self._react("wave", "Entry updated—nice and tidy!", "pop")
        except (ValueError, OSError) as exc:
            self.notice.emit("Could not update entry", str(exc))

    @Slot(int)
    def deleteEntry(self, entry_id: int) -> None:
        try:
            self.db.delete_transaction(entry_id); self.refresh(); self.notice.emit("Entry removed", "The entry and its managed attachment copies were deleted.")
        except ValueError as exc:
            self.notice.emit("Could not delete entry", str(exc))

    @Slot(str)
    def searchEntries(self, text: str) -> None:
        self.entries.refresh(self.current_month_id(), text)

    @Slot(str)
    def saveNote(self, note: str) -> None:
        try:
            self.db.save_note(self.current_month_id(), note); self.refresh(); self._react("comfort", "Reflection tucked safely into this month.", "meow")
        except ValueError as exc:
            self.notice.emit("Could not save reflection", str(exc))

    @Slot(str)
    def setTarget(self, value: str) -> None:
        try:
            self.db.set_target(self.current_month_id(), parse_thousand_vnd(value)); self.refresh(); self._react("think", "New target set. I’ll cheer you on!", "pop")
        except ValueError as exc:
            self.notice.emit("Could not update target", str(exc))

    @Slot(str, str)
    def closeMonth(self, bank: str, debt: str) -> None:
        try:
            next_id = self.db.close_month(self.current_month_id(), parse_signed_thousand_vnd(bank), parse_thousand_vnd(debt))
            self.reload_months(next_id); self._react("celebrate", "Month closed and rolled forward—pawsome!", "celebrate")
        except ValueError as exc:
            self.notice.emit("Could not close month", str(exc))

    @Slot()
    def reopenMonth(self) -> None:
        try:
            month_id = self.current_month_id(); self.db.reopen_month(month_id); self.reload_months(month_id); self._react("wave", "This month is open for edits again.", "pop")
        except ValueError as exc:
            self.notice.emit("Could not reopen month", str(exc))

    @Slot("QVariantList")
    def addMonthImages(self, files: list) -> None:
        successes, errors = 0, []
        for value in files:
            try:
                self.db.add_month_attachment(self.current_month_id(), _local_path(str(value))); successes += 1
            except (ValueError, OSError) as exc:
                errors.append(str(exc))
        self.gallery.refresh(self.current_month_id())
        if successes:
            self._react("wave", f"Added {successes} image{'s' if successes != 1 else ''} to the month gallery!", "pop")
        if errors:
            self.notice.emit("Some images were skipped", "\n".join(errors[:5]))

    @Slot(int, str)
    def setMonthImageCaption(self, image_id: int, caption: str) -> None:
        try:
            self.db.update_month_attachment_caption(image_id, caption); self.gallery.refresh(self.current_month_id())
        except ValueError as exc:
            self.notice.emit("Could not save caption", str(exc))

    @Slot(int, int)
    def moveMonthImage(self, image_id: int, new_index: int) -> None:
        try:
            self.db.reorder_month_attachment(self.current_month_id(), image_id, new_index); self.gallery.refresh(self.current_month_id())
        except ValueError as exc:
            self.notice.emit("Could not reorder image", str(exc))

    @Slot(int)
    def deleteMonthImage(self, image_id: int) -> None:
        self.db.delete_month_attachment(image_id); self.gallery.refresh(self.current_month_id()); self.notice.emit("Image removed", "The managed gallery copy was deleted.")

    @Slot(str, str)
    def exportReport(self, kind: str, destination: str) -> None:
        path, month_id = _local_path(destination), self.current_month_id()
        self._run_task("Report exported", lambda: (export_docx if kind == "docx" else export_pdf)(self.db, month_id, path))
        self._react("think", "I’m polishing the report now…", "pop")

    @Slot(str)
    def createBackup(self, destination: str) -> None:
        path = _local_path(destination)
        self._run_task("Backup complete", lambda: create_backup(self.db.db_path, self.db.attachment_dir, path))

    @Slot(str)
    def restoreBackup(self, source: str) -> None:
        try:
            path = _local_path(source); validate_backup(path)
            safety = self.data_dir / "safety_backups" / f"before_restore_{datetime.now():%Y%m%d_%H%M%S}.zip"
            safety.parent.mkdir(parents=True, exist_ok=True)
            create_backup(self.db.db_path, self.db.attachment_dir, safety)
            restore_backup(path, self.db.db_path, self.db.attachment_dir)
            self.db = Database(self.db.db_path, self.db.attachment_dir)
            self.entries.db = self.gallery.db = self.db
            self.reload_months(); self.notice.emit("Restore complete", "The backup was restored. A safety backup of the previous data was kept.")
        except Exception as exc:
            self.notice.emit("Restore failed", str(exc))

    @Slot(bool, float, bool)
    def saveSettings(self, sound_enabled: bool, volume: float, reduced_motion: bool) -> None:
        self._sound_enabled, self._volume, self._reduced_motion = sound_enabled, volume, reduced_motion
        self.db.set_setting("sound_enabled", "1" if sound_enabled else "0")
        self.db.set_setting("sound_volume", str(volume))
        self.db.set_setting("reduced_motion", "1" if reduced_motion else "0")
        self.sounds.configure(sound_enabled, volume); self.settingsChanged.emit()

    @Slot()
    def petMiso(self) -> None:
        self._react("comfort", "Meow! That was lovely!", "meow")

    @Slot(str)
    def playSound(self, name: str) -> None:
        if name in {"click", "pop", "whoosh", "celebrate", "meow"}:
            self.sounds.play(name)

    @Slot()
    def openDataFolder(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32": os.startfile(self.data_dir)  # type: ignore[attr-defined]
        elif sys.platform == "darwin": subprocess.Popen(["open", self.data_dir])
        else: subprocess.Popen(["xdg-open", self.data_dir])

    def _react(self, state: str, message: str, sound: str) -> None:
        self.sounds.play(sound); self.mascotEvent.emit(state, message, sound)

    def _run_task(self, title: str, work) -> None:
        if self._busy:
            self.notice.emit("Please wait", "Another export or backup is still running."); return
        self._busy = True; self.busyChanged.emit()
        def runner():
            try:
                result = work(); self.taskFinished.emit(title, True, str(result))
            except Exception as exc:
                self.taskFinished.emit(title, False, str(exc))
        self._executor.submit(runner)

    @Slot(str, bool, str)
    def _finish_task(self, title: str, success: bool, detail: str) -> None:
        self._busy = False; self.busyChanged.emit()
        self.notice.emit(title if success else f"{title} failed", detail)
        if success: self._react("celebrate", "All done! Your file is ready.", "celebrate")
