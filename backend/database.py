import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("DB_PATH", "data/coffee.db"))
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# Bumped whenever schema.sql changes in a way that needs to reach a database
# that already exists (e.g. the deployed Iron instance) - a brand new DB file
# gets the current schema.sql in full, but init_db() never re-runs schema.sql
# against an existing file, so anything beyond that needs an additive
# migration below. Migrations must never be destructive - by the time most
# of these run, the database already has real entries in it.
SCHEMA_VERSION = 1

MIGRATIONS: dict[int, str] = {
    # 0.2.1: roast_location field + entry_farms table for multi-farm bags.
    1: """
    ALTER TABLE entries ADD COLUMN roast_location TEXT;

    CREATE TABLE entry_farms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_id INTEGER NOT NULL REFERENCES entries(id),
        farm_name TEXT NOT NULL,
        location TEXT
    );
    """,
}


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    is_new = not DB_PATH.exists()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    if is_new:
        conn.executescript(SCHEMA_PATH.read_text())
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.commit()
    else:
        _run_migrations(conn)
    conn.close()


def _run_migrations(conn: sqlite3.Connection) -> None:
    current_version = conn.execute("PRAGMA user_version").fetchone()[0]
    for version in range(current_version + 1, SCHEMA_VERSION + 1):
        conn.executescript(MIGRATIONS[version])
        conn.execute(f"PRAGMA user_version = {version}")
        conn.commit()
