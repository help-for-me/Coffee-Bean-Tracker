import sqlite3

from backend import database


def _create_legacy_db(path):
    # Simulates a database created before the roast_location/entry_farms
    # migration existed - what the real Iron deployment's database looks
    # like right now. init_db() must bring this up to date without losing
    # the existing row.
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE bean_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roaster TEXT NOT NULL,
            bean_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bean_profile_id INTEGER NOT NULL REFERENCES bean_profiles(id),
            entry_type TEXT NOT NULL,
            farm_producer TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.execute("INSERT INTO bean_profiles (roaster, bean_name) VALUES ('Stumptown', 'Hair Bender')")
    conn.execute("INSERT INTO entries (bean_profile_id, entry_type, farm_producer) VALUES (1, 'bag', 'Existing Farm')")
    conn.commit()
    conn.close()


def test_init_db_migrates_existing_database_without_data_loss(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy.db"
    _create_legacy_db(db_path)
    monkeypatch.setattr(database, "DB_PATH", db_path)

    database.init_db()

    conn = database.get_connection()
    try:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(entries)")}
        assert "roast_location" in columns
        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "entry_farms" in tables
        row = conn.execute("SELECT farm_producer FROM entries WHERE id = 1").fetchone()
        assert row["farm_producer"] == "Existing Farm"
        assert conn.execute("PRAGMA user_version").fetchone()[0] == database.SCHEMA_VERSION
    finally:
        conn.close()


def test_init_db_is_idempotent_on_already_migrated_database(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    database.init_db()

    database.init_db()  # must not raise (e.g. duplicate column/table errors)

    conn = database.get_connection()
    try:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == database.SCHEMA_VERSION
    finally:
        conn.close()


def test_init_db_fresh_database_sets_schema_version(tmp_path, monkeypatch):
    db_path = tmp_path / "fresh.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)

    database.init_db()

    conn = database.get_connection()
    try:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == database.SCHEMA_VERSION
        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "entry_farms" in tables
    finally:
        conn.close()
