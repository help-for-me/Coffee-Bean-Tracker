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


def create_entry(conn: sqlite3.Connection, data: EntryCreate, has_photos: bool = False) -> int:
    extraction_status = "pending" if has_photos else "not_applicable"
    extraction_source = "claude" if has_photos else "manual"
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bean_profile_id,
                data.entry_type,
                data.cafe_name,
                data.entry_date.isoformat() if data.entry_date else None,
                data.price_paid,
                data.currency,
                extraction_status,
                extraction_source,
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


def add_entry_photo(conn: sqlite3.Connection, entry_id: int, photo_path: str, upload_order: int) -> int:
    with conn:
        cursor = conn.execute(
            "INSERT INTO entry_photos (entry_id, photo_path, upload_order) VALUES (?, ?, ?)",
            (entry_id, photo_path, upload_order),
        )
    return cursor.lastrowid


def apply_extraction_result(conn: sqlite3.Connection, entry_id: int, result: dict) -> None:
    with conn:
        conn.execute(
            """
            UPDATE entries SET
                extraction_status = 'complete',
                extraction_source = 'claude',
                origin_country = COALESCE(?, origin_country),
                region = COALESCE(?, region),
                farm_producer = COALESCE(?, farm_producer),
                altitude_m = COALESCE(?, altitude_m),
                variety = COALESCE(?, variety),
                process = COALESCE(?, process),
                co_ferment_status = COALESCE(?, co_ferment_status),
                co_ferment_ingredient = COALESCE(?, co_ferment_ingredient),
                certifications = COALESCE(?, certifications),
                roast_level = COALESCE(?, roast_level),
                printed_tasting_notes = COALESCE(?, printed_tasting_notes),
                roast_date = COALESCE(?, roast_date),
                bag_weight_g = COALESCE(?, bag_weight_g),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                result.get("origin_country"),
                result.get("region"),
                result.get("farm_producer"),
                result.get("altitude_m"),
                result.get("variety"),
                result.get("process"),
                result.get("co_ferment_status"),
                result.get("co_ferment_ingredient"),
                result.get("certifications"),
                result.get("roast_level"),
                result.get("printed_tasting_notes"),
                result.get("roast_date"),
                result.get("bag_weight_g"),
                entry_id,
            ),
        )


def mark_extraction_failed(conn: sqlite3.Connection, entry_id: int) -> None:
    with conn:
        conn.execute(
            "UPDATE entries SET extraction_status = 'failed', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (entry_id,),
        )


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


def list_entries(
    conn: sqlite3.Connection, query: Optional[str] = None, limit: Optional[int] = None
) -> list[dict]:
    sql = """
        SELECT e.id, bp.roaster, bp.bean_name, e.entry_type, e.entry_date, e.date_entered,
               e.extraction_status,
               (SELECT r.score FROM ratings r WHERE r.entry_id = e.id ORDER BY r.date_entered DESC, r.id DESC LIMIT 1) AS latest_score
        FROM entries e
        JOIN bean_profiles bp ON bp.id = e.bean_profile_id
    """
    params: list = []
    if query:
        pattern = f"%{query.strip()}%"
        sql += " WHERE bp.roaster LIKE ? OR bp.bean_name LIKE ? OR e.cafe_name LIKE ?"
        params += [pattern, pattern, pattern]
    sql += " ORDER BY e.date_entered DESC, e.id DESC"
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


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
