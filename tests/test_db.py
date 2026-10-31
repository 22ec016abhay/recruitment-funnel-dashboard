"""The project reads one database, read-only, and never creates or seeds data."""
import sqlite3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.common.db import DB_PATH, connect_readonly  # noqa: E402


class TestDatabase(unittest.TestCase):
    def test_db_path_is_real_dataset(self):
        self.assertEqual(DB_PATH.name, "recruitment.db")
        self.assertTrue(DB_PATH.exists())

    def test_missing_database_fails_loudly(self):
        with self.assertRaises(FileNotFoundError):
            connect_readonly(ROOT / "sql" / "does_not_exist.db")

    def test_writes_are_refused(self):
        conn = connect_readonly()
        with self.assertRaises(sqlite3.OperationalError):
            conn.execute("DELETE FROM applicants")
        conn.close()

    def test_no_module_points_at_the_fake_database(self):
        for path in (ROOT / "src").rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("recuitment.db", text, f"{path} still references the typo database")
            self.assertNotIn("CREATE TABLE IF NOT EXISTS applicants", text, f"{path} seeds data")

    def test_real_row_count(self):
        conn = connect_readonly()
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM applicants").fetchone()[0], 1500)
        conn.close()


if __name__ == "__main__":
    unittest.main()
