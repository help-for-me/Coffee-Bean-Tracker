import sqlite3
from typing import Optional

from .models import EntryCreate, RatingCreate


def resolve_bean_profile(conn: sqlite3.Connection, roaster: str, bean_name: str) -> int:
    roaster = roaster.strip()
    bean_name = bean_name.strip()
    row = conn.execute(
        "SELECT id FROM bean_profiles WHERE roaster = ? COLLATE NOCASE AND bean_name = ? COLLATE NOCASE",
        (roaster, bean_name),
    ).fetchone()
    if row:
        return row["id"]
    cursor = conn.execute(
        "INSERT INTO bean_profiles (roaster, bean_name) VALUES (?, ?)",
        (roaster, bean_name),
    )
    return cursor.lastrowid


def search_bean_profiles(conn: sqlite3.Connection, query: str, limit: int = 10) -> list[dict]:
    pattern = f"{query.strip()}%"
    rows = conn.execute(
        """
        SELECT id, roaster, bean_name FROM bean_profiles
        WHERE roaster LIKE ? OR bean_name LIKE ? OR (roaster || ' ' || bean_name) LIKE ?
        ORDER BY roaster, bean_name
        LIMIT ?
        """,
        (pattern, pattern, pattern, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def create_entry(conn: sqlite3.Connection, data: EntryCreate) -> int:
    with conn:
        bean_profile_id = resolve_bean_profile(conn, data.roaster, data.bean_name)
        cursor = conn.execute(
            """
            INSERT INTO entries (
                bean_profile_id, entry_type, cafe_name, entry_date, price_paid, currency,
                extraction_status, extraction_source,
                origin_country, region, farm_producer, altitude_m, variety, process,
                co_ferment_status, co_ferment_ingredient, certifications, roast_level,
                printed_tasting_notes, roast_date, bag_weight_g
            ) VALUES (?, ?, ?, ?, ?, ?, 'not_applicable', 'manual', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bean_profile_id,
                data.entry_type,
                data.cafe_name,
                data.entry_date.isoformat() if data.entry_date else None,
                data.price_paid,
                data.currency,
                data.origin_country,
                data.region,
                data.farm_producer,
                data.altitude_m,
                data.variety,
                data.process,
                data.co_ferment_status,
                data.co_ferment_ingredient,
                data.certifications,
                data.roast_level,
                data.printed_tasting_notes,
                data.roast_date.isoformat() if data.roast_date else None,
                data.bag_weight_g,
            ),
        )
        entry_id = cursor.lastrowid
        _insert_rating(conn, entry_id, data)
    return entry_id


def add_rating(conn: sqlite3.Connection, entry_id: int, data: RatingCreate) -> int:
    with conn:
        rating_id = _insert_rating(conn, entry_id, data)
    return rating_id


def _insert_rating(conn: sqlite3.Connection, entry_id: int, data: RatingCreate) -> int:
    cursor = conn.execute(
        """
        INSERT INTO ratings (
            entry_id, score, narrative_notes, acidity_score, body_score, sweetness_score,
            brew_style, repurchase
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entry_id,
            data.score,
            data.narrative_notes,
            data.acidity_score,
            data.body_score,
            data.sweetness_score,
            data.brew_style,
            data.repurchase,
        ),
    )
    return cursor.lastrowid


def get_entry(conn: sqlite3.Connection, entry_id: int) -> Optional[dict]:
    entry_row = conn.execute(
        """
        SELECT e.*, bp.id AS bp_id, bp.roaster AS bp_roaster, bp.bean_name AS bp_bean_name
        FROM entries e
        JOIN bean_profiles bp ON bp.id = e.bean_profile_id
        WHERE e.id = ?
        """,
        (entry_id,),
    ).fetchone()
    if entry_row is None:
        return None
    rating_rows = conn.execute(
        "SELECT * FROM ratings WHERE entry_id = ? ORDER BY date_entered",
        (entry_id,),
    ).fetchall()
    entry = dict(entry_row)
    entry["bean_profile"] = {
        "id": entry.pop("bp_id"),
        "roaster": entry.pop("bp_roaster"),
        "bean_name": entry.pop("bp_bean_name"),
    }
    entry["ratings"] = [dict(r) for r in rating_rows]
    return entry
