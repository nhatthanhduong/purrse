import sqlite3

from purrse.database import Database


def test_version_one_database_upgrades_in_place(tmp_path):
    path = tmp_path / "purrse.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE schema_info(version INTEGER NOT NULL)")
        connection.execute("INSERT INTO schema_info(version) VALUES(1)")
    Database(path, tmp_path / "attachments")
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT version FROM schema_info").fetchone()[0] == 2
        assert connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='month_attachments'").fetchone()[0] == "month_attachments"
