"""Single entry point for the project database.

Every module reads the real dataset in sql/recruitment.db through a read-only
connection. Nothing in this project creates tables, seeds data or writes views.
"""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "sql" / "recruitment.db"


def connect_readonly(path: Path = DB_PATH) -> sqlite3.Connection:
    """Open the database read-only. Fails loudly if the file is missing."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Database not found at {path}. Build it with sql/load_data.py first."
        )
    # Path.as_uri() percent-encodes spaces and '&' so the SQLite URI parses correctly.
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    conn.execute("PRAGMA query_only = ON")
    return conn
