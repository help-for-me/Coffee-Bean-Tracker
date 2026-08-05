import calendar
import os
import re
import sqlite3
from datetime import date, datetime
from typing import Optional

from .. import crud

# Bag labels list tasting notes with different delimiters depending on the
# roaster (comma-separated, or dash-separated like "Peach - Tropical
# Fruits") - split on either, but not on a hyphen embedded in a word (e.g.
# "Anaerobic-Washed" isn't a note list).
_NOTE_SPLIT_PATTERN = re.compile(r"\s*[,;/]\s*|\s+-\s+")


def _months_ago(months: int, from_date: date) -> date:
    total_months = from_date.year * 12 + (from_date.month - 1) - months
    year, month = divmod(total_months, 12)
    month += 1
    day = min(from_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def compute_recent_cutoff(
    entry_dates: list[date], today: date, months: int = 4, count: int = 10
) -> dict:
    sorted_dates = sorted(entry_dates)
    total = len(sorted_dates)
    if total == 0:
        return {"applicable": False, "cutoff_date": None}

    months_cutoff = _months_ago(months, today)
    has_enough_months = sorted_dates[0] <= months_cutoff
    has_enough_count = total >= count

    if not (has_enough_months and has_enough_count):
        return {"applicable": False, "cutoff_date": None}

    by_months = [d for d in sorted_dates if d >= months_cutoff]
    by_count = sorted_dates[-count:]
    chosen = by_months if len(by_months) >= len(by_count) else by_count
    return {"applicable": True, "cutoff_date": chosen[0]}


def _trend_direction(scores: list[float]) -> str:
    if len(scores) < 2:
        return "flat"
    if scores[-1] > scores[0]:
        return "up"
    if scores[-1] < scores[0]:
        return "down"
    return "flat"


def average_score_by_process(conn: sqlite3.Connection, since: Optional[date] = None) -> list[dict]:
    sql = """
        SELECT e.process AS process, AVG(r.score) AS avg_score, COUNT(*) AS count
        FROM ratings r
        JOIN entries e ON e.id = r.entry_id
        WHERE e.process IS NOT NULL
    """
    params: list = []
    if since:
        sql += " AND r.date_entered >= ?"
        params.append(since.isoformat())
    sql += " GROUP BY e.process ORDER BY avg_score DESC"
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def average_score_by_origin_country(
    conn: sqlite3.Connection, since: Optional[date] = None, limit: int = 10
) -> list[dict]:
    sql = """
        SELECT e.origin_country AS origin_country, AVG(r.score) AS avg_score, COUNT(*) AS count
        FROM ratings r
        JOIN entries e ON e.id = r.entry_id
        WHERE e.origin_country IS NOT NULL
    """
    params: list = []
    if since:
        sql += " AND r.date_entered >= ?"
        params.append(since.isoformat())
    sql += " GROUP BY e.origin_country ORDER BY avg_score DESC LIMIT ?"
    params.append(limit)
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def _split_notes(raw: str) -> list[str]:
    return [n.strip() for n in _NOTE_SPLIT_PATTERN.split(raw) if n.strip()]


def average_score_by_tasting_note(
    conn: sqlite3.Connection, since: Optional[date] = None, limit: int = 10
) -> list[dict]:
    sql = """
        SELECT e.printed_tasting_notes AS notes, r.score AS score
        FROM ratings r
        JOIN entries e ON e.id = r.entry_id
        WHERE e.printed_tasting_notes IS NOT NULL
    """
    params: list = []
    if since:
        sql += " AND r.date_entered >= ?"
        params.append(since.isoformat())
    rows = conn.execute(sql, params).fetchall()

    buckets: dict[str, list[float]] = {}
    for row in rows:
        for note in _split_notes(row["notes"]):
            buckets.setdefault(note.title(), []).append(row["score"])

    results = [
        {"note": note, "avg_score": sum(scores) / len(scores), "count": len(scores)}
        for note, scores in buckets.items()
    ]
    results.sort(key=lambda r: r["avg_score"], reverse=True)
    return results[:limit]


def monthly_rating_trend(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT strftime('%Y-%m', date_entered) AS month, AVG(score) AS avg_score, COUNT(*) AS count
        FROM ratings
        GROUP BY month
        ORDER BY month
        """
    ).fetchall()
    return [dict(row) for row in rows]


def most_repurchased(conn: sqlite3.Connection, since: Optional[date] = None, limit: int = 10) -> list[dict]:
    sql = """
        SELECT bp.id AS bean_profile_id, bp.roaster, bp.bean_name,
               e.id AS entry_id, COALESCE(e.entry_date, e.date_entered) AS sort_date,
               AVG(r.score) AS entry_avg_score
        FROM entries e
        JOIN bean_profiles bp ON bp.id = e.bean_profile_id
        JOIN ratings r ON r.entry_id = e.id
    """
    params: list = []
    if since:
        sql += " WHERE r.date_entered >= ?"
        params.append(since.isoformat())
    sql += " GROUP BY e.id ORDER BY bp.id, sort_date"
    rows = conn.execute(sql, params).fetchall()

    by_profile: dict[int, dict] = {}
    for row in rows:
        pid = row["bean_profile_id"]
        profile = by_profile.setdefault(
            pid, {"roaster": row["roaster"], "bean_name": row["bean_name"], "scores": []}
        )
        profile["scores"].append(row["entry_avg_score"])

    results = [
        {
            "roaster": data["roaster"],
            "bean_name": data["bean_name"],
            "entry_count": len(data["scores"]),
            "avg_score": sum(data["scores"]) / len(data["scores"]),
            "trend": _trend_direction(data["scores"]),
        }
        for data in by_profile.values()
        if len(data["scores"]) >= 2
    ]
    results.sort(key=lambda r: r["entry_count"], reverse=True)
    return results[:limit]


def get_insights(conn: sqlite3.Connection, today: Optional[date] = None) -> dict:
    if today is None:
        today = date.today()

    # DB-backed override (1.4.0 settings UI) takes priority over the env
    # var, which stays as the pre-settings-UI default.
    months = int(crud.get_setting(conn, "recent_window_months") or os.environ.get("RECENT_WINDOW_MONTHS", 4))
    count = int(crud.get_setting(conn, "recent_window_count") or os.environ.get("RECENT_WINDOW_COUNT", 10))

    rating_dates = [
        datetime.fromisoformat(row["date_entered"]).date()
        for row in conn.execute("SELECT date_entered FROM ratings").fetchall()
    ]
    recent_window = compute_recent_cutoff(rating_dates, today, months=months, count=count)
    since = recent_window["cutoff_date"] if recent_window["applicable"] else None

    return {
        "monthly_trend": monthly_rating_trend(conn),
        "by_process": {
            "all_time": average_score_by_process(conn),
            "recent": average_score_by_process(conn, since=since) if since else [],
        },
        "by_origin_country": {
            "all_time": average_score_by_origin_country(conn),
            "recent": average_score_by_origin_country(conn, since=since) if since else [],
        },
        "by_tasting_note": {
            "all_time": average_score_by_tasting_note(conn),
            "recent": average_score_by_tasting_note(conn, since=since) if since else [],
        },
        "most_repurchased": {
            "all_time": most_repurchased(conn),
            "recent": most_repurchased(conn, since=since) if since else [],
        },
        "recent_window": recent_window,
    }


def insights_for_window(all_insights: dict, window_type: str) -> dict:
    # Narrows get_insights()'s all_time/recent split down to a single
    # window - the flat shape InsightGenerator.generate() interprets.
    return {
        "monthly_trend": all_insights["monthly_trend"],
        "by_process": all_insights["by_process"][window_type],
        "by_origin_country": all_insights["by_origin_country"][window_type],
        "by_tasting_note": all_insights["by_tasting_note"][window_type],
        "most_repurchased": all_insights["most_repurchased"][window_type],
    }
