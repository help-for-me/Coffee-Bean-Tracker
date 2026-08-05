from datetime import date

from backend import crud
from backend.insights.stats import (
    _months_ago,
    _split_notes,
    _trend_direction,
    average_score_by_brew_style,
    average_score_by_origin_country,
    average_score_by_process,
    average_score_by_tasting_note,
    compute_recent_cutoff,
    get_insights,
    insights_for_window,
    monthly_rating_trend,
    most_repurchased,
)
from backend.models import EntryCreate


def _rate_at(
    conn, roaster, bean_name, score, when,
    process=None, origin_country=None, printed_tasting_notes=None, brew_style=None,
):
    # Bypasses the normal create_entry/add_rating flow so date_entered can
    # be backdated precisely - real inserts always stamp "now".
    data = EntryCreate(
        entry_type="bag",
        roaster=roaster,
        bean_name=bean_name,
        score=score,
        process=process,
        origin_country=origin_country,
        printed_tasting_notes=printed_tasting_notes,
        brew_style=brew_style,
    )
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


def test_average_score_by_process_filters_by_brew_style(conn):
    _rate_at(conn, "Stumptown", "Hair Bender", 5, date(2026, 7, 1), process="Washed", brew_style="Espresso")
    _rate_at(conn, "Intelligentsia", "Black Cat", 9, date(2026, 7, 2), process="Washed", brew_style="Pour Over")

    espresso_only = average_score_by_process(conn, brew_style="Espresso")
    assert espresso_only == [{"process": "Washed", "avg_score": 5, "count": 1}]


# --- _split_notes ---


def test_split_notes_comma_separated():
    assert _split_notes("Mango, Papaya, Floral") == ["Mango", "Papaya", "Floral"]


def test_split_notes_dash_separated():
    assert _split_notes("Hibiscus - Peach - Tropical Fruits") == ["Hibiscus", "Peach", "Tropical Fruits"]


def test_split_notes_does_not_split_hyphenated_word():
    assert _split_notes("Anaerobic-Washed") == ["Anaerobic-Washed"]


def test_split_notes_single_note():
    assert _split_notes("Chocolate") == ["Chocolate"]


# --- average_score_by_origin_country ---


def test_average_score_by_origin_country_groups_and_averages(conn):
    _rate_at(conn, "Stumptown", "Hair Bender", 8, date(2026, 7, 1), origin_country="Colombia")
    _rate_at(conn, "Intelligentsia", "Black Cat", 6, date(2026, 7, 2), origin_country="Colombia")
    _rate_at(conn, "Monogram", "Mango", 9, date(2026, 7, 3), origin_country="Ethiopia")

    results = {r["origin_country"]: r for r in average_score_by_origin_country(conn)}
    assert results["Colombia"]["avg_score"] == 7
    assert results["Colombia"]["count"] == 2
    assert results["Ethiopia"]["avg_score"] == 9


def test_average_score_by_origin_country_sorted_best_first(conn):
    _rate_at(conn, "Stumptown", "Hair Bender", 5, date(2026, 7, 1), origin_country="Brazil")
    _rate_at(conn, "Monogram", "Mango", 9, date(2026, 7, 2), origin_country="Ethiopia")
    results = average_score_by_origin_country(conn)
    assert [r["origin_country"] for r in results] == ["Ethiopia", "Brazil"]


# --- average_score_by_tasting_note ---


def test_average_score_by_tasting_note_splits_and_dedups_case(conn):
    _rate_at(conn, "Stumptown", "A", 8, date(2026, 7, 1), printed_tasting_notes="Mango, Papaya")
    _rate_at(conn, "Monogram", "B", 6, date(2026, 7, 2), printed_tasting_notes="mango")

    results = {r["note"]: r for r in average_score_by_tasting_note(conn)}
    assert results["Mango"]["count"] == 2
    assert results["Mango"]["avg_score"] == 7
    assert results["Papaya"]["count"] == 1


def test_average_score_by_tasting_note_handles_dash_delimited_bag(conn):
    _rate_at(conn, "Pallet Coffee", "Elkin Guzman", 9, date(2026, 7, 1), printed_tasting_notes="Hibiscus - Peach - Tropical Fruits")
    results = {r["note"] for r in average_score_by_tasting_note(conn)}
    assert results == {"Hibiscus", "Peach", "Tropical Fruits"}


def test_average_score_by_tasting_note_ranked_best_first(conn):
    _rate_at(conn, "A", "A", 5, date(2026, 7, 1), printed_tasting_notes="Citrus")
    _rate_at(conn, "B", "B", 9, date(2026, 7, 2), printed_tasting_notes="Chocolate")
    results = average_score_by_tasting_note(conn)
    assert results[0]["note"] == "Chocolate"


# --- average_score_by_brew_style ---


def test_average_score_by_brew_style_groups_and_averages(conn):
    _rate_at(conn, "Stumptown", "Hair Bender", 8, date(2026, 7, 1), brew_style="Espresso")
    _rate_at(conn, "Intelligentsia", "Black Cat", 6, date(2026, 7, 2), brew_style="Espresso")
    _rate_at(conn, "Monogram", "Mango", 9, date(2026, 7, 3), brew_style="Pour Over")

    results = {r["brew_style"]: r for r in average_score_by_brew_style(conn)}
    assert results["Espresso"]["avg_score"] == 7
    assert results["Espresso"]["count"] == 2
    assert results["Pour Over"]["avg_score"] == 9


def test_average_score_by_brew_style_excludes_null(conn):
    _rate_at(conn, "Stumptown", "Hair Bender", 8, date(2026, 7, 1), brew_style=None)
    assert average_score_by_brew_style(conn) == []


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
    assert result["by_origin_country"]["recent"] == []
    assert result["by_tasting_note"]["recent"] == []
    assert result["by_brew_style"]["recent"] == []
    assert result["most_repurchased"]["recent"] == []


def test_get_insights_includes_brew_style_breakdown(conn):
    _rate_at(conn, "Stumptown", "Hair Bender", 8, date(2026, 7, 1), brew_style="Espresso")
    result = get_insights(conn, today=date(2026, 8, 4))
    assert result["by_brew_style"]["all_time"] == [{"brew_style": "Espresso", "avg_score": 8, "count": 1}]


def test_get_insights_brew_style_filter_slices_process_origin_and_notes(conn):
    _rate_at(
        conn, "Stumptown", "Hair Bender", 8, date(2026, 7, 1),
        process="Washed", origin_country="Colombia", printed_tasting_notes="Chocolate", brew_style="Espresso",
    )
    _rate_at(
        conn, "Intelligentsia", "Black Cat", 4, date(2026, 7, 2),
        process="Washed", origin_country="Colombia", printed_tasting_notes="Chocolate", brew_style="Pour Over",
    )

    result = get_insights(conn, today=date(2026, 8, 4), brew_style="Espresso")
    assert result["by_process"]["all_time"] == [{"process": "Washed", "avg_score": 8, "count": 1}]
    assert result["by_origin_country"]["all_time"] == [{"origin_country": "Colombia", "avg_score": 8, "count": 1}]
    assert result["by_tasting_note"]["all_time"] == [{"note": "Chocolate", "avg_score": 8, "count": 1}]
    # by_brew_style itself is never sliced by the brew_style filter - it's
    # the dimension being filtered on, not one more thing to filter.
    assert {r["brew_style"] for r in result["by_brew_style"]["all_time"]} == {"Espresso", "Pour Over"}


def test_get_insights_includes_origin_and_tasting_note_breakdowns(conn):
    _rate_at(conn, "Stumptown", "Hair Bender", 8, date(2026, 7, 1), origin_country="Colombia", printed_tasting_notes="Chocolate")
    result = get_insights(conn, today=date(2026, 8, 4))
    assert result["by_origin_country"]["all_time"] == [{"origin_country": "Colombia", "avg_score": 8, "count": 1}]
    assert result["by_tasting_note"]["all_time"] == [{"note": "Chocolate", "avg_score": 8, "count": 1}]


def test_get_insights_empty_database(conn):
    result = get_insights(conn, today=date(2026, 8, 4))
    assert result["monthly_trend"] == []
    assert result["by_process"]["all_time"] == []
    assert result["by_origin_country"]["all_time"] == []
    assert result["by_tasting_note"]["all_time"] == []
    assert result["most_repurchased"]["all_time"] == []
    assert result["recent_window"]["applicable"] is False


# --- insights_for_window (0.9.0 AI narrative insights) ---


def test_insights_for_window_flattens_all_time():
    all_insights = {
        "monthly_trend": [{"month": "2026-07", "avg_score": 8, "count": 1}],
        "by_process": {"all_time": [{"process": "Washed", "avg_score": 8, "count": 1}], "recent": []},
        "by_origin_country": {"all_time": [], "recent": []},
        "by_tasting_note": {"all_time": [], "recent": []},
        "most_repurchased": {"all_time": [], "recent": []},
        "recent_window": {"applicable": False, "cutoff_date": None},
    }
    windowed = insights_for_window(all_insights, "all_time")
    assert windowed == {
        "monthly_trend": [{"month": "2026-07", "avg_score": 8, "count": 1}],
        "by_process": [{"process": "Washed", "avg_score": 8, "count": 1}],
        "by_origin_country": [],
        "by_tasting_note": [],
        "most_repurchased": [],
    }
    assert "recent_window" not in windowed


def test_insights_for_window_picks_recent_slice():
    all_insights = {
        "monthly_trend": [],
        "by_process": {"all_time": [{"process": "Washed"}], "recent": [{"process": "Natural"}]},
        "by_origin_country": {"all_time": [], "recent": []},
        "by_tasting_note": {"all_time": [], "recent": []},
        "most_repurchased": {"all_time": [], "recent": []},
        "recent_window": {"applicable": True, "cutoff_date": date(2026, 7, 1)},
    }
    windowed = insights_for_window(all_insights, "recent")
    assert windowed["by_process"] == [{"process": "Natural"}]
