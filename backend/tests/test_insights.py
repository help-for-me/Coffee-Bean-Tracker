from datetime import date

from backend import crud
from backend.insights.stats import (
    _months_ago,
    _trend_direction,
    average_score_by_process,
    compute_recent_cutoff,
    get_insights,
    monthly_rating_trend,
    most_repurchased,
)
from backend.models import EntryCreate


def _rate_at(conn, roaster, bean_name, score, when, process=None):
    # Bypasses the normal create_entry/add_rating flow so date_entered can
    # be backdated precisely - real inserts always stamp "now".
    data = EntryCreate(entry_type="bag", roaster=roaster, bean_name=bean_name, score=score, process=process)
    entry_id = crud.create_entry(conn, data)
    with conn:
        conn.execute("UPDATE ratings SET date_entered = ? WHERE entry_id = ?", (when.isoformat(), entry_id))
        conn.execute("UPDATE entries SET date_entered = ? WHERE id = ?", (when.isoformat(), entry_id))
    return entry_id


# --- _months_ago ---


def test_months_ago_basic():
    assert _months_ago(4, date(2026, 8, 4)) == date(2026, 4, 4)


def test_months_ago_clamps_to_shorter_month():
    # Feb 2026 has 28 days (not a leap year) - March 31st minus 1 month
    # can't land on Feb 31st.
    assert _months_ago(1, date(2026, 3, 31)) == date(2026, 2, 28)


def test_months_ago_crosses_year_boundary():
    assert _months_ago(4, date(2026, 1, 15)) == date(2025, 9, 15)


# --- compute_recent_cutoff ---


def test_compute_recent_cutoff_empty():
    assert compute_recent_cutoff([], date(2026, 8, 4)) == {"applicable": False, "cutoff_date": None}


def test_compute_recent_cutoff_not_applicable_not_enough_entries():
    dates = [date(2025, 1, 1)] + [date(2026, 7, d) for d in range(1, 6)]  # 6 total, old + recent
    result = compute_recent_cutoff(dates, date(2026, 8, 4))
    assert result == {"applicable": False, "cutoff_date": None}


def test_compute_recent_cutoff_not_applicable_not_enough_months():
    # 12 entries (enough count), but the oldest is only 2 months back.
    dates = [date(2026, 6, 4 + i) for i in range(12)]
    result = compute_recent_cutoff(dates, date(2026, 8, 4))
    assert result == {"applicable": False, "cutoff_date": None}


def test_compute_recent_cutoff_picks_by_months_when_larger():
    old = [date(2025, 1, 1)]
    # 12 entries within the last 4 months (after 2026-04-04)
    recent = [date(2026, 4, 10 + i) for i in range(12)]
    result = compute_recent_cutoff(old + recent, date(2026, 8, 4))
    assert result["applicable"] is True
    assert result["cutoff_date"] == min(recent)


def test_compute_recent_cutoff_picks_by_count_when_larger():
    # 10 total entries, oldest well past 4 months back, only 3 within the
    # last 4 months - the last-10-entries window is bigger than the
    # last-4-months window, so it wins.
    old = [date(2025, 6, d) for d in range(1, 8)]  # 7 old entries
    recent = [date(2026, 7, d) for d in range(1, 4)]  # 3 recent entries
    dates = old + recent
    result = compute_recent_cutoff(dates, date(2026, 8, 4))
    assert result["applicable"] is True
    assert result["cutoff_date"] == min(dates)  # by-count window = all 10


# --- _trend_direction ---


def test_trend_direction_empty():
    assert _trend_direction([]) == "flat"


def test_trend_direction_single_score():
    assert _trend_direction([7]) == "flat"


def test_trend_direction_up():
    assert _trend_direction([5, 6, 8]) == "up"


def test_trend_direction_down():
    assert _trend_direction([8, 6, 5]) == "down"


def test_trend_direction_flat_when_first_equals_last():
    assert _trend_direction([7, 9, 7]) == "flat"


# --- average_score_by_process ---


def test_average_score_by_process_groups_and_averages(conn):
    _rate_at(conn, "Stumptown", "Hair Bender", 8, date(2026, 7, 1), process="Washed")
    _rate_at(conn, "Intelligentsia", "Black Cat", 6, date(2026, 7, 2), process="Washed")
    _rate_at(conn, "Monogram", "Mango", 9, date(2026, 7, 3), process="Honey")

    results = {r["process"]: r for r in average_score_by_process(conn)}
    assert results["Washed"]["avg_score"] == 7
    assert results["Washed"]["count"] == 2
    assert results["Honey"]["avg_score"] == 9


def test_average_score_by_process_excludes_null_process(conn):
    _rate_at(conn, "Stumptown", "Hair Bender", 8, date(2026, 7, 1), process=None)
    assert average_score_by_process(conn) == []


def test_average_score_by_process_since_filters_by_date(conn):
    _rate_at(conn, "Stumptown", "Hair Bender", 5, date(2026, 1, 1), process="Washed")
    _rate_at(conn, "Intelligentsia", "Black Cat", 9, date(2026, 7, 1), process="Washed")

    all_time = average_score_by_process(conn)
    recent = average_score_by_process(conn, since=date(2026, 4, 1))
    assert all_time[0]["count"] == 2
    assert recent[0]["count"] == 1
    assert recent[0]["avg_score"] == 9


# --- monthly_rating_trend ---


def test_monthly_rating_trend_groups_by_month(conn):
    _rate_at(conn, "Stumptown", "Hair Bender", 6, date(2026, 6, 15))
    _rate_at(conn, "Intelligentsia", "Black Cat", 8, date(2026, 6, 20))
    _rate_at(conn, "Monogram", "Mango", 7, date(2026, 7, 1))

    trend = monthly_rating_trend(conn)
    by_month = {row["month"]: row for row in trend}
    assert by_month["2026-06"]["count"] == 2
    assert by_month["2026-06"]["avg_score"] == 7
    assert by_month["2026-07"]["count"] == 1


# --- most_repurchased ---


def test_most_repurchased_requires_at_least_two_entries(conn):
    _rate_at(conn, "Stumptown", "Hair Bender", 7, date(2026, 7, 1))
    assert most_repurchased(conn) == []


def test_most_repurchased_computes_trend_up(conn):
    _rate_at(conn, "Stumptown", "Hair Bender", 5, date(2026, 5, 1))
    _rate_at(conn, "Stumptown", "Hair Bender", 8, date(2026, 7, 1))

    results = most_repurchased(conn)
    assert len(results) == 1
    assert results[0]["entry_count"] == 2
    assert results[0]["trend"] == "up"


def test_most_repurchased_sorted_by_entry_count(conn):
    _rate_at(conn, "Stumptown", "Hair Bender", 7, date(2026, 5, 1))
    _rate_at(conn, "Stumptown", "Hair Bender", 7, date(2026, 6, 1))
    _rate_at(conn, "Stumptown", "Hair Bender", 7, date(2026, 7, 1))
    _rate_at(conn, "Intelligentsia", "Black Cat", 7, date(2026, 5, 1))
    _rate_at(conn, "Intelligentsia", "Black Cat", 7, date(2026, 6, 1))

    results = most_repurchased(conn)
    assert results[0]["roaster"] == "Stumptown"
    assert results[0]["entry_count"] == 3


# --- get_insights ---


def test_get_insights_recent_window_not_applicable_with_sparse_data(conn):
    _rate_at(conn, "Stumptown", "Hair Bender", 7, date(2026, 7, 1))
    result = get_insights(conn, today=date(2026, 8, 4))
    assert result["recent_window"]["applicable"] is False
    assert result["by_process"]["recent"] == []
    assert result["most_repurchased"]["recent"] == []


def test_get_insights_empty_database(conn):
    result = get_insights(conn, today=date(2026, 8, 4))
    assert result["monthly_trend"] == []
    assert result["by_process"]["all_time"] == []
    assert result["most_repurchased"]["all_time"] == []
    assert result["recent_window"]["applicable"] is False
