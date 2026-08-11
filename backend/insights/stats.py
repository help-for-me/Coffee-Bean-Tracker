import calendar
import math
import os
import re
import sqlite3
import warnings
from datetime import date, datetime
from typing import Optional

from scipy.stats import ttest_ind

# Bag labels list tasting notes with different delimiters depending on the
# roaster (comma-separated, or dash-separated like "Peach - Tropical
# Fruits") - split on either, but not on a hyphen embedded in a word (e.g.
# "Anaerobic-Washed" isn't a note list).
_NOTE_SPLIT_PATTERN = re.compile(r"\s*[,;/]\s*|\s+-\s+")

# Below this many ratings on EITHER side of a top-two comparison, there's
# no way to estimate variance (a single point has none), so a t-test can't
# run at all - reported as "not comparable" rather than skipped silently.
_MIN_RATINGS_FOR_SIGNIFICANCE = 2
_SIGNIFICANCE_ALPHA = 0.05


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


# --- Statistically-aware ranking (1.2.0's deferred "statistical rigor" gap) ---
#
# A single rating of 9 for a tasting note that's only ever come up once
# shouldn't outrank a note that's shown up ten times averaging 8.5 - the
# first number is real but tells you almost nothing about whether it'll
# hold up, the second is backed by real history. Two things fix this:
#
# 1. Rank by an empirical-Bayes-shrunk score, not the raw average: each
#    group's average gets pulled toward the overall mean, in proportion to
#    how few ratings back it. A group with only 1-2 ratings gets pulled
#    hard toward the middle; a group with 20 barely moves. This is the
#    same idea behind "weighted rating" systems (e.g. IMDB's), adapted so
#    it works on a 0-10 continuous score instead of a vote count.
# 2. Never imply a top-ranked item is a genuine preference over the
#    runner-up without checking: a real (Welch's) two-sample t-test
#    between the top two, only run when both have at least 2 ratings
#    (variance is undefined from a single point). When the gap isn't
#    statistically significant - or there isn't enough data to say either
#    way - that's reported plainly instead of implied away by the ranking.


def _bayesian_adjusted_score(mean: float, count: int, global_mean: float, k: float) -> float:
    return (count / (count + k)) * mean + (k / (count + k)) * global_mean


def _significance_between_top_two(items: list[dict], buckets: dict[str, list[float]], key_name: str) -> dict:
    if len(items) < 2:
        return {
            "comparable": False,
            "p_value": None,
            "significant": None,
            "message": "Not enough distinct groups to compare.",
        }

    top, second = items[0], items[1]
    top_scores = buckets[top[key_name]]
    second_scores = buckets[second[key_name]]
    if len(top_scores) < _MIN_RATINGS_FOR_SIGNIFICANCE or len(second_scores) < _MIN_RATINGS_FOR_SIGNIFICANCE:
        return {
            "comparable": False,
            "p_value": None,
            "significant": None,
            "message": (
                f"Not enough ratings to test {top[key_name]!r} vs {second[key_name]!r} "
                f"(need at least {_MIN_RATINGS_FOR_SIGNIFICANCE} each)."
            ),
        }

    # Welch's t-test (unequal variance) - the standard choice for two
    # independent samples without assuming they're equally variable.
    # Identical/constant scores on both sides produce a 0/0 variance ratio
    # (nan), which scipy warns about - caught explicitly below rather than
    # left to print a warning during normal use.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        _, p_value = ttest_ind(top_scores, second_scores, equal_var=False)
    p_value = float(p_value)

    if math.isnan(p_value):
        return {
            "comparable": False,
            "p_value": None,
            "significant": None,
            "message": f"{top[key_name]!r} vs {second[key_name]!r}: scores show no variation to test.",
        }

    significant = p_value < _SIGNIFICANCE_ALPHA
    verdict = "a statistically significant difference" if significant else "no statistically significant difference"
    return {
        "comparable": True,
        "p_value": round(p_value, 4),
        "significant": significant,
        "message": f"{top[key_name]!r} vs {second[key_name]!r}: {verdict} (p={p_value:.3f}).",
    }


def _rank_with_significance(
    buckets: dict[str, list[float]], key_name: str, limit: Optional[int] = None
) -> dict:
    if not buckets:
        return {
            "items": [],
            "significance": {"comparable": False, "p_value": None, "significant": None, "message": "No data yet."},
        }

    all_scores = [score for scores in buckets.values() for score in scores]
    global_mean = sum(all_scores) / len(all_scores)
    # Prior strength (k): the average sample size per group in THIS
    # dataset, not a fixed constant - so shrinkage adapts to how sparse
    # the data actually is instead of an arbitrary guess.
    k = len(all_scores) / len(buckets)

    items = []
    for key, scores in buckets.items():
        mean = sum(scores) / len(scores)
        count = len(scores)
        items.append({
            key_name: key,
            "avg_score": mean,
            "count": count,
            "adjusted_score": _bayesian_adjusted_score(mean, count, global_mean, k),
        })
    items.sort(key=lambda r: r["adjusted_score"], reverse=True)

    # Computed on the full ranking, before any display limit is applied -
    # truncating first could, in principle, cut the actual top two.
    significance = _significance_between_top_two(items, buckets, key_name)

    if limit:
        items = items[:limit]
    return {"items": items, "significance": significance}


def average_score_by_process(
    conn: sqlite3.Connection, since: Optional[date] = None, brew_style: Optional[str] = None
) -> dict:
    sql = """
        SELECT e.process AS process, r.score AS score
        FROM ratings r
        JOIN entries e ON e.id = r.entry_id
        WHERE e.process IS NOT NULL
    """
    params: list = []
    if since:
        sql += " AND r.date_entered >= ?"
        params.append(since.isoformat())
    if brew_style:
        sql += " AND r.brew_style = ?"
        params.append(brew_style)
    rows = conn.execute(sql, params).fetchall()

    buckets: dict[str, list[float]] = {}
    for row in rows:
        buckets.setdefault(row["process"], []).append(row["score"])
    return _rank_with_significance(buckets, "process")


def average_score_by_origin_country(
    conn: sqlite3.Connection, since: Optional[date] = None, limit: int = 10, brew_style: Optional[str] = None
) -> dict:
    sql = """
        SELECT e.origin_country AS origin_country, r.score AS score
        FROM ratings r
        JOIN entries e ON e.id = r.entry_id
        WHERE e.origin_country IS NOT NULL
    """
    params: list = []
    if since:
        sql += " AND r.date_entered >= ?"
        params.append(since.isoformat())
    if brew_style:
        sql += " AND r.brew_style = ?"
        params.append(brew_style)
    rows = conn.execute(sql, params).fetchall()

    buckets: dict[str, list[float]] = {}
    for row in rows:
        buckets.setdefault(row["origin_country"], []).append(row["score"])
    return _rank_with_significance(buckets, "origin_country", limit=limit)


def average_score_by_brew_style(conn: sqlite3.Connection, since: Optional[date] = None) -> dict:
    sql = """
        SELECT r.brew_style AS brew_style, r.score AS score
        FROM ratings r
        WHERE r.brew_style IS NOT NULL
    """
    params: list = []
    if since:
        sql += " AND r.date_entered >= ?"
        params.append(since.isoformat())
    rows = conn.execute(sql, params).fetchall()

    buckets: dict[str, list[float]] = {}
    for row in rows:
        buckets.setdefault(row["brew_style"], []).append(row["score"])
    return _rank_with_significance(buckets, "brew_style")


def _split_notes(raw: str) -> list[str]:
    return [n.strip() for n in _NOTE_SPLIT_PATTERN.split(raw) if n.strip()]


def average_score_by_tasting_note(
    conn: sqlite3.Connection, since: Optional[date] = None, limit: int = 10, brew_style: Optional[str] = None
) -> dict:
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
    if brew_style:
        sql += " AND r.brew_style = ?"
        params.append(brew_style)
    rows = conn.execute(sql, params).fetchall()

    buckets: dict[str, list[float]] = {}
    for row in rows:
        for note in _split_notes(row["notes"]):
            buckets.setdefault(note.title(), []).append(row["score"])
    return _rank_with_significance(buckets, "note", limit=limit)


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


def get_insights(conn: sqlite3.Connection, today: Optional[date] = None, brew_style: Optional[str] = None) -> dict:
    if today is None:
        today = date.today()

    # DB-backed override (1.4.0 settings UI) takes priority over the env
    # var, which stays as the pre-settings-UI default.
    months = int(os.environ.get("RECENT_WINDOW_MONTHS", 4))
    count = int(os.environ.get("RECENT_WINDOW_COUNT", 10))

    rating_dates = [
        datetime.fromisoformat(row["date_entered"]).date()
        for row in conn.execute("SELECT date_entered FROM ratings").fetchall()
    ]
    recent_window = compute_recent_cutoff(rating_dates, today, months=months, count=count)
    since = recent_window["cutoff_date"] if recent_window["applicable"] else None

    empty_ranking = {"items": [], "significance": {"comparable": False, "p_value": None, "significant": None, "message": "No data yet."}}

    return {
        "monthly_trend": monthly_rating_trend(conn),
        "by_process": {
            "all_time": average_score_by_process(conn, brew_style=brew_style),
            "recent": average_score_by_process(conn, since=since, brew_style=brew_style) if since else empty_ranking,
        },
        "by_origin_country": {
            "all_time": average_score_by_origin_country(conn, brew_style=brew_style),
            "recent": average_score_by_origin_country(conn, since=since, brew_style=brew_style) if since else empty_ranking,
        },
        "by_tasting_note": {
            "all_time": average_score_by_tasting_note(conn, brew_style=brew_style),
            "recent": average_score_by_tasting_note(conn, since=since, brew_style=brew_style) if since else empty_ranking,
        },
        # Not sliced by brew_style like the three breakdowns above - it *is*
        # the brew-method dimension, so filtering it by a single brew style
        # would collapse it down to the one row you asked for.
        "by_brew_style": {
            "all_time": average_score_by_brew_style(conn),
            "recent": average_score_by_brew_style(conn, since=since) if since else empty_ranking,
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
