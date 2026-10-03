# Purrse

Purrse is a vibrant, offline monthly money journal for Windows. Its PySide6/QML interface combines smooth motion, playful feedback and an animated storybook cat with exact local accounting. It records income, spending, borrowing and debt repayments; carries confirmed balances into the next month; and exports complete DOCX or PDF reports.

All everyday amount fields use **thousand VND**. Entering `150` records exactly `150,000 VND`.

## Highlights

- Local SQLite database with no account, cloud service or internet connection
- Editable monthly drafts and a deliberate review-and-close workflow
- Exact bank/debt rollover and visible reconciliation adjustments
- Preset and custom categories, search, notes and multiple attachments per entry
- Independent monthly image gallery for balance screenshots and other evidence
- Smooth transitions, animated totals, progress effects, confetti and reduced-motion support
- Persistent interactive pixel-art Miso with eight poses and contextual reactions
- Bundled click, pop, page, celebration and Miso meow sounds with mute, volume and test controls
- DOCX/PDF reports with charts, a curated monthly gallery and embedded receipts
- Validated ZIP backups with automatic safety backup before restore

## Run from source

Python 3.11 or later is required.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m purrse
```

Application data is stored under `%LOCALAPPDATA%\Purrse` on Windows. Removing or reinstalling the application does not intentionally delete this data. Use **Settings → Create backup** regularly and keep the ZIP somewhere safe.

## Monthly workflow

1. On first launch, enter current bank balance, debt and a monthly savings target.
2. Add dated income, expense, borrowing and repayment entries. Entries save immediately.
3. Add optional receipt images or other files. Purrse keeps managed copies.
4. Add balance screenshots or other month-wide images in **Monthly Gallery**, then caption and order them for the report.
5. Add a personal reflection and export draft reports whenever needed.
6. Select **Review & close month**, compare calculated and actual balances, and confirm them.
7. Purrse records any reconciliation difference and creates the next month with the confirmed bank/debt balances and the same target.

Monthly gallery images remain editable after closing because they do not alter financial calculations. Entries and balances remain read-only unless the month is reopened.

Savings is defined as income minus ordinary expenses. Borrowing and repayment affect cash and debt balances but are presented separately from savings performance.

## Build the Windows installer

1. On 64-bit Windows, run `powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1`.
2. Install [Inno Setup](https://jrsoftware.org/isinfo.php).
3. Compile `installer\Purrse.iss`.
4. Find the installer under `release\Purrse-Setup-2.0.2.exe`.

The PyInstaller build deliberately uses a one-folder bundle wrapped by a normal installer. This launches faster and is typically less likely to trigger false antivirus warnings than a self-extracting single-file executable.

## Tests

```bash
python -m pytest
```

For headless or CI environments, set `QT_QPA_PLATFORM=offscreen` and `QT_QUICK_BACKEND=software`.

The tests cover exact VND parsing, accounting formulas, schema upgrades, monthly and transaction attachments, report embedding, debt safeguards, rollover/reopening rules, QML loading, insights, and backup/restore round trips.
