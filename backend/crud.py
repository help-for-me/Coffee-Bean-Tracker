import difflib
import sqlite3
from typing import Optional

from .models import EntryCreate, RatingCreate

# Auto-merge cutoff for extraction-resolved identity (0.8.0) - conservative,
# matching the 0.84 cutoff claude_extractor.py already uses for vocab
# correction, since a false-positive merge here silently combines two
# roasters' entries with no undo. Autocomplete suggestions use a looser
# cutoff since the user still picks explicitly - no merge risk there.
_FUZZY_MERGE_CUTOFF = 0.85
_FUZZY_SUGGEST_CUTOFF = 0.6


def _fuzzy_match_profile(
    conn: sqlite3.Connection, roaster: str, bean_name: str, exclude_id: Optional[int], cutoff: float, limit: int
) -> list[dict]:
    # Ranks every non-provisional profile (never suggest/merge into an
    # "Unidentified #N" placeholder) by similarity of "roaster bean_name"
    # against the target, using stdlib difflib rather than adding a fuzzy-
    # matching dependency.
    target = f"{roaster} {bean_name}".strip().lower()
    rows = conn.execute(
        "SELECT id, roaster, bean_name FROM bean_profiles WHERE is_provisional = 0" + (" AND id != ?" if exclude_id else ""),
        (exclude_id,) if exclude_id else (),
    ).fetchall()
    scored = []
    for row in rows:
        candidate = f"{row['roaster']} {row['bean_name']}".strip().lower()
        ratio = difflib.SequenceMatcher(None, target, candidate).ratio()
        if ratio >= cutoff:
            scored.append((ratio, dict(row)))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [profile for _, profile in scored[:limit]]

_UPDATABLE_ENTRY_FIELDS = {
    "cafe_name", "entry_date", "price_paid", "currency",
    "origin_country", "region", "farm_producer", "altitude_m", "variety", "process",
    "co_ferment_status", "co_ferment_ingredient", "certifications", "roast_level",
    "printed_tasting_notes", "roast_date", "bag_weight_g", "batch_number", "roast_location",
}

_UPDATABLE_RATING_FIELDS = {
    "score", "narrative_notes", "acidity_score", "body_score", "sweetness_score",
    "brew_style", "repurchase",
}


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


def create_provisional_bean_profile(conn: sqlite3.Connection) -> int:
    # Always inserts a brand-new row - never reused across entries, unlike
    # resolve_bean_profile's find-or-create - since two different
    # unidentified bags shouldn't accidentally merge just because both are
    # nameless yet. bean_name embeds the row's own id so it's guaranteed
    # unique and each provisional row is instantly recognizable.
    cursor = conn.execute("INSERT INTO bean_profiles (roaster, bean_name, is_provisional) VALUES (?, ?, 1)", ("Unidentified", ""))
    profile_id = cursor.lastrowid
    conn.execute("UPDATE bean_profiles SET bean_name = ? WHERE id = ?", (f"#{profile_id}", profile_id))
    return profile_id


def resolve_provisional_profile(conn: sqlite3.Connection, provisional_id: int, roaster: str, bean_name: str) -> int:
    # Called once extraction resolves a real identity for a provisional
    # profile. Tries an exact/case-insensitive match first (same as
    # resolve_bean_profile for typed entries); since 0.8.0, falls back to a
    # conservative fuzzy match to catch OCR typos (e.g. "Jario Arcila" vs
    # "Jairo Aroila") that would otherwise create a duplicate profile. In
    # either case, every entry on the placeholder gets re-linked to the
    # matched profile and the placeholder is discarded; with no match at
    # all, the placeholder itself becomes the real profile, renamed in
    # place.
    roaster = roaster.strip()
    bean_name = bean_name.strip()
    existing = conn.execute(
        "SELECT id FROM bean_profiles WHERE roaster = ? COLLATE NOCASE AND bean_name = ? COLLATE NOCASE AND id != ?",
        (roaster, bean_name, provisional_id),
    ).fetchone()
    existing_id = existing["id"] if existing else None
    if existing_id is None:
        fuzzy = _fuzzy_match_profile(
            conn, roaster, bean_name, exclude_id=provisional_id, cutoff=_FUZZY_MERGE_CUTOFF, limit=1
        )
        if fuzzy:
            existing_id = fuzzy[0]["id"]
    if existing_id is not None:
        conn.execute(
            "UPDATE entries SET bean_profile_id = ? WHERE bean_profile_id = ?", (existing_id, provisional_id)
        )
        conn.execute("DELETE FROM bean_profiles WHERE id = ?", (provisional_id,))
        return existing_id
    conn.execute(
        "UPDATE bean_profiles SET roaster = ?, bean_name = ?, is_provisional = 0 WHERE id = ?",
        (roaster, bean_name, provisional_id),
    )
    return provisional_id


def search_bean_profiles(conn: sqlite3.Connection, query: str, limit: int = 10) -> list[dict]:
    pattern = f"{query.strip()}%"
    rows = conn.execute(
        """
        SELECT id, roaster, bean_name, is_provisional FROM bean_profiles
        WHERE is_provisional = 0
          AND (roaster LIKE ? OR bean_name LIKE ? OR (roaster || ' ' || bean_name) LIKE ?)
        ORDER BY roaster, bean_name
        LIMIT ?
        """,
        (pattern, pattern, pattern, limit),
    ).fetchall()
    results = [dict(row) for row in rows]

    # 0.8.0: prefix matching alone misses typos (e.g. "Detor" for
    # "Detour") - fill any remaining suggestion slots with fuzzy matches,
    # a looser cutoff than auto-merge since the user still picks
    # explicitly from the list.
    remaining = limit - len(results)
    if remaining > 0:
        seen_ids = {row["id"] for row in results}
        fuzzy = _fuzzy_match_profile(conn, query, "", exclude_id=None, cutoff=_FUZZY_SUGGEST_CUTOFF, limit=limit)
        for profile in fuzzy:
            if profile["id"] not in seen_ids:
                results.append({**profile, "is_provisional": False})
                seen_ids.add(profile["id"])
                if len(results) >= limit:
                    break
    return results


def create_entry(conn: sqlite3.Connection, data: EntryCreate, has_photos: bool = False) -> int:
    extraction_status = "pending" if has_photos else "not_applicable"
    extraction_source = "claude" if has_photos else "manual"
    with conn:
        if data.roaster and data.bean_name:
            bean_profile_id = resolve_bean_profile(conn, data.roaster, data.bean_name)
        else:
            bean_profile_id = create_provisional_bean_profile(conn)
        cursor = conn.execute(
            """
            INSERT INTO entries (
                bean_profile_id, entry_type, cafe_name, entry_date, price_paid, currency,
                extraction_status, extraction_source,
                origin_country, region, farm_producer, altitude_m, variety, process,
                co_ferment_status, co_ferment_ingredient, certifications, roast_level,
                printed_tasting_notes, roast_date, bag_weight_g, batch_number, roast_location
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                data.batch_number,
                data.roast_location,
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


def get_entry_photo_paths(conn: sqlite3.Connection, entry_id: int) -> list[str]:
    rows = conn.execute(
        "SELECT photo_path FROM entry_photos WHERE entry_id = ? ORDER BY upload_order",
        (entry_id,),
    ).fetchall()
    return [row["photo_path"] for row in rows]


def mark_extraction_pending(conn: sqlite3.Connection, entry_id: int) -> None:
    with conn:
        conn.execute(
            "UPDATE entries SET extraction_status = 'pending', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (entry_id,),
        )


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
                batch_number = COALESCE(?, batch_number),
                roast_location = COALESCE(?, roast_location),
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
                result.get("batch_number"),
                result.get("roast_location"),
                entry_id,
            ),
        )
        farms = result.get("farms")
        if farms:
            conn.executemany(
                "INSERT INTO entry_farms (entry_id, farm_name, location) VALUES (?, ?, ?)",
                [(entry_id, farm["farm_name"], farm.get("location")) for farm in farms if farm.get("farm_name")],
            )

        roaster = result.get("roaster")
        bean_name = result.get("bean_name")
        if roaster and bean_name:
            profile_row = conn.execute(
                """
                SELECT bp.id, bp.is_provisional FROM entries e
                JOIN bean_profiles bp ON bp.id = e.bean_profile_id
                WHERE e.id = ?
                """,
                (entry_id,),
            ).fetchone()
            if profile_row and profile_row["is_provisional"]:
                resolve_provisional_profile(conn, profile_row["id"], roaster, bean_name)


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
        SELECT e.id, bp.roaster, bp.bean_name, bp.is_provisional, e.entry_type, e.entry_date, e.date_entered,
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
    entries = [dict(row) for row in rows]
    for entry in entries:
        entry["is_provisional"] = bool(entry["is_provisional"])
    return entries


def get_entry(conn: sqlite3.Connection, entry_id: int) -> Optional[dict]:
    entry_row = conn.execute(
        """
        SELECT e.*, bp.id AS bp_id, bp.roaster AS bp_roaster, bp.bean_name AS bp_bean_name,
               bp.is_provisional AS bp_is_provisional
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
    farm_rows = conn.execute(
        "SELECT farm_name, location FROM entry_farms WHERE entry_id = ? ORDER BY id",
        (entry_id,),
    ).fetchall()
    photo_rows = conn.execute(
        "SELECT id, entry_id, upload_order, date_entered FROM entry_photos WHERE entry_id = ? ORDER BY upload_order",
        (entry_id,),
    ).fetchall()
    entry = dict(entry_row)
    related_photo_rows = conn.execute(
        """
        SELECT ep.id, ep.entry_id, ep.upload_order, ep.date_entered
        FROM entry_photos ep
        JOIN entries e2 ON e2.id = ep.entry_id
        WHERE e2.bean_profile_id = ? AND ep.entry_id != ?
        ORDER BY ep.date_entered DESC
        """,
        (entry["bean_profile_id"], entry_id),
    ).fetchall()
    entry["bean_profile"] = {
        "id": entry.pop("bp_id"),
        "roaster": entry.pop("bp_roaster"),
        "bean_name": entry.pop("bp_bean_name"),
        "is_provisional": bool(entry.pop("bp_is_provisional")),
    }
    entry["ratings"] = [dict(r) for r in rating_rows]
    entry["farms"] = [dict(f) for f in farm_rows]
    entry["photos"] = [dict(p) for p in photo_rows]
    entry["related_photos"] = [dict(p) for p in related_photo_rows]
    return entry


def update_entry(conn: sqlite3.Connection, entry_id: int, fields: dict) -> bool:
    fields = {k: v for k, v in fields.items() if k in _UPDATABLE_ENTRY_FIELDS}
    if "entry_date" in fields and fields["entry_date"] is not None:
        fields["entry_date"] = fields["entry_date"].isoformat()
    if "roast_date" in fields and fields["roast_date"] is not None:
        fields["roast_date"] = fields["roast_date"].isoformat()
    if not fields:
        return conn.execute("SELECT 1 FROM entries WHERE id = ?", (entry_id,)).fetchone() is not None
    set_clause = ", ".join(f"{key} = ?" for key in fields)
    with conn:
        cursor = conn.execute(
            f"UPDATE entries SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (*fields.values(), entry_id),
        )
    return cursor.rowcount > 0


def delete_entry(conn: sqlite3.Connection, entry_id: int) -> Optional[list[str]]:
    # Returns the deleted entry's photo file paths (so the router can
    # remove the actual files) or None if the entry didn't exist. No
    # ON DELETE CASCADE in the schema, so children get removed explicitly,
    # in one transaction, before the entry itself.
    with conn:
        if conn.execute("SELECT 1 FROM entries WHERE id = ?", (entry_id,)).fetchone() is None:
            return None
        photo_rows = conn.execute(
            "SELECT photo_path FROM entry_photos WHERE entry_id = ?", (entry_id,)
        ).fetchall()
        conn.execute("DELETE FROM ratings WHERE entry_id = ?", (entry_id,))
        conn.execute("DELETE FROM entry_photos WHERE entry_id = ?", (entry_id,))
        conn.execute("DELETE FROM entry_farms WHERE entry_id = ?", (entry_id,))
        conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    return [row["photo_path"] for row in photo_rows]


def update_rating(conn: sqlite3.Connection, rating_id: int, fields: dict) -> bool:
    fields = {k: v for k, v in fields.items() if k in _UPDATABLE_RATING_FIELDS}
    if not fields:
        return conn.execute("SELECT 1 FROM ratings WHERE id = ?", (rating_id,)).fetchone() is not None
    set_clause = ", ".join(f"{key} = ?" for key in fields)
    with conn:
        cursor = conn.execute(
            f"UPDATE ratings SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (*fields.values(), rating_id),
        )
    return cursor.rowcount > 0


def delete_rating(conn: sqlite3.Connection, rating_id: int) -> bool:
    with conn:
        cursor = conn.execute("DELETE FROM ratings WHERE id = ?", (rating_id,))
    return cursor.rowcount > 0


def get_latest_narrative(conn: sqlite3.Connection, window_type: str) -> Optional[dict]:
    row = conn.execute(
        """
        SELECT id, window_type, summary_text, generated_at FROM insight_narratives
        WHERE window_type = ? ORDER BY generated_at DESC, id DESC LIMIT 1
        """,
        (window_type,),
    ).fetchone()
    return dict(row) if row else None


def save_narrative(conn: sqlite3.Connection, window_type: str, summary_text: str) -> dict:
    with conn:
        cursor = conn.execute(
            "INSERT INTO insight_narratives (window_type, summary_text) VALUES (?, ?)",
            (window_type, summary_text),
        )
    row = conn.execute(
        "SELECT id, window_type, summary_text, generated_at FROM insight_narratives WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    return dict(row)


def get_counts(conn: sqlite3.Connection) -> dict:
    # Logged on every startup (see main.py) so a container restart's
    # before/after counts can be compared directly from the log file,
    # without having to click through the app to check nothing was lost.
    return {
        "entries": conn.execute("SELECT COUNT(*) AS n FROM entries").fetchone()["n"],
        "ratings": conn.execute("SELECT COUNT(*) AS n FROM ratings").fetchone()["n"],
        "photos": conn.execute("SELECT COUNT(*) AS n FROM entry_photos").fetchone()["n"],
    }


# --- 1.4.0: settings UI ---


def get_setting(conn: sqlite3.Connection, key: str) -> Optional[str]:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    with conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
