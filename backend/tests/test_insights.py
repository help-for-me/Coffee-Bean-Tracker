from datetime import date

from backend import crud
from backend.insights.stats import (
    _bayesian_adjusted_score,
    _months_ago,
    _rank_with_significance,
    _significance_between_top_two,
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


NOT_COMPARABLE = {"comparable": False, "p_value": None, "significant": None}


def _sig(result, **overrides):
    # Compares comparable/significant while ignoring "message" (free text)
    # and "p_value" (exact float, asserted separately by range where it
    # matters) - both would make this helper overly brittle to check here.
    trimmed = {k: v for k, v in result.items() if k not in ("message", "p_value")}
    expected = {k: v for k, v in {**NOT_COMPARABLE, **overrides}.items() if k != "p_value"}
    assert trimmed == expected, result


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


# --- _bayesian_adjusted_score (statistical rigor: 1.2.0's deferred gap) ---


def test_bayesian_adjusted_score_single_rating_pulled_hard_toward_global_mean():
    # A single 9 with a global mean of 7 and a typical sample size (k) of 5
    # should land much closer to 7 than to 9 - one data point isn't enough
    # to trust on its own.
    adjusted = _bayesian_adjusted_score(mean=9, count=1, global_mean=7, k=5)
    assert 7 < adjusted < 8


def test_bayesian_adjusted_score_large_sample_barely_moves():
    adjusted = _bayesian_adjusted_score(mean=8.5, count=100, global_mean=7, k=5)
    assert adjusted == 8.5 * (100 / 105) + 7 * (5 / 105)
    assert adjusted > 8.4  # barely pulled at all


def test_bayesian_adjusted_score_equals_mean_when_k_is_zero():
    assert _bayesian_adjusted_score(mean=9, count=1, global_mean=5, k=0) == 9


def test_bayesian_adjusted_score_equals_global_mean_when_count_is_zero():
    assert _bayesian_adjusted_score(mean=9, count=0, global_mean=5, k=5) == 5


# --- _significance_between_top_two ---


def test_significance_not_comparable_with_fewer_than_two_groups():
    items = [{"process": "Washed", "avg_score": 8, "count": 3, "adjusted_score": 8}]
    result = _significance_between_top_two(items, {"Washed": [8, 8, 8]}, "process")
    _sig(result)


def test_significance_not_comparable_with_single_rating_on_either_side():
    items = [
        {"process": "Washed", "avg_score": 9, "count": 1, "adjusted_score": 7.5},
        {"process": "Honey", "avg_score": 8.5, "count": 10, "adjusted_score": 8.4},
    ]
    buckets = {"Washed": [9], "Honey": [8.5] * 10}
    result = _significance_between_top_two(items, buckets, "process")
    _sig(result)


def test_significance_detects_a_real_difference():
    items = [
        {"process": "A", "avg_score": 8.6, "count": 5, "adjusted_score": 8.6},
        {"process": "B", "avg_score": 4.6, "count": 5, "adjusted_score": 4.6},
    ]
    buckets = {"A": [9, 8, 9, 9, 8], "B": [5, 4, 5, 4, 5]}
    result = _significance_between_top_two(items, buckets, "process")
    _sig(result, comparable=True, significant=True)
    assert result["p_value"] < 0.05


def test_significance_reports_no_difference_when_not_significant():
    items = [
        {"process": "A", "avg_score": 7.33, "count": 3, "adjusted_score": 7.33},
        {"process": "B", "avg_score": 7.67, "count": 3, "adjusted_score": 7.67},
    ]
    buckets = {"A": [7, 7, 8], "B": [7, 8, 8]}
    result = _significance_between_top_two(items, buckets, "process")
    _sig(result, comparable=True, significant=False)
    assert result["p_value"] >= 0.05


def test_significance_handles_zero_variance_on_both_sides():
    # Identical constant scores on both sides make the test statistic 0/0
    # (undefined), not a real "no difference" result - must be reported as
    # not comparable, never silently treated as p=1.
    items = [
        {"process": "A", "avg_score": 8, "count": 2, "adjusted_score": 8},
        {"process": "B", "avg_score": 8, "count": 2, "adjusted_score": 8},
    ]
    buckets = {"A": [8, 8], "B": [8, 8]}
    result = _significance_between_top_two(items, buckets, "process")
    _sig(result)


# --- _rank_with_significance ---


def test_rank_with_significance_empty_buckets():
    result = _rank_with_significance({}, "process")
    assert result["items"] == []
    assert result["significance"]["comparable"] is False


def test_rank_with_significance_sorts_by_adjusted_score_not_raw_average():
    # The exact motivating example from ROADMAP.md's 1.2.0 gap: a note that
    # appears once at a 9 must NOT outrank one that appears ten times
    # averaging 8.5 once sample size is accounted for. Needs a realistic
    # spread of other groups too - with only these two groups in play, the
    # "global mean" shrinkage pulls toward is itself defined entirely by
    # the pair being compared, which understates the effect; a real coffee
    # log has many other notes anchoring that average lower.
    buckets = {
        "Rare Note": [9],
        "Common Note": [8.5] * 10,
        "Berry": [6, 6, 6, 6, 6],
        "Nutty": [6.5, 6.5, 6.5, 6.5, 6.5],
        "Floral": [7, 7, 7],
    }
    result = _rank_with_significance(buckets, "note")
    assert result["items"][0]["note"] == "Common Note"
    assert result["items"][0]["avg_score"] == 8.5
    assert result["items"][1]["note"] == "Rare Note"


def test_rank_with_significance_respects_limit():
    buckets = {f"Note {i}": [8] for i in range(15)}
    result = _rank_with_significance(buckets, "note", limit=10)
    assert len(result["items"]) == 10


def test_rank_with_significance_limit_does_not_change_significance_verdict():
    # Significance is computed on the top two of the FULL ranking, before
    # any display limit truncates the list - confirmed by checking the
    # verdict is identical with and without a limit that cuts the list
    # down, not just eyeballing one hardcoded expectation.
    buckets = {"A": [9, 8], "B": [6, 7], **{f"Filler {i}": [2] for i in range(3)}}
    full = _rank_with_significance(buckets, "process")
    limited = _rank_with_significance(buckets, "process", limit=3)
    assert len(full["items"]) == 5
    assert len(limited["items"]) == 3
    assert limited["significance"] == full["significance"]
    assert full["significance"]["comparable"] is True


# --- average_score_by_process ---


def test_average_score_by_process_groups_and_averages(conn):
    _rate_at(conn, "Stumptown", "Hair Bender", 8, date(2026, 7, 1), process="Washed")
    _rate_at(conn, "Intelligentsia", "Black Cat", 6, date(2026, 7, 2), process="Washed")
    _rate_at(conn, "Monogram", "Mango", 9, date(2026, 7, 3), process="Honey")

    results = {r["process"]: r for r in average_score_by_process(conn)["items"]}
    assert results["Washed"]["avg_score"] == 7
    assert results["Washed"]["count"] == 2
    assert results["Honey"]["avg_score"] == 9
    assert "adjusted_score" in results["Washed"]


def test_average_score_by_process_excludes_null_process(conn):
    _rate_at(conn, "Stumptown", "Hair Bender", 8, date(2026, 7, 1), process=None)
    assert average_score_by_process(conn)["items"] == []


def test_average_score_by_process_since_filters_by_date(conn):
    _rate_at(conn, "Stumptown", "Hair Bender", 5, date(2026, 1, 1), process="Washed")
    _rate_at(conn, "Intelligentsia", "Black Cat", 9, date(2026, 7, 1), process="Washed")

    all_time = average_score_by_process(conn)["items"]
    recent = average_score_by_process(conn, since=date(2026, 4, 1))["items"]
    assert all_time[0]["count"] == 2
    assert recent[0]["count"] == 1
    assert recent[0]["avg_score"] == 9


def test_average_score_by_process_filters_by_brew_style(conn):
    _rate_at(conn, "Stumptown", "Hair Bender", 5, date(2026, 7, 1), process="Washed", brew_style="Espresso")
    _rate_at(conn, "Intelligentsia", "Black Cat", 9, date(2026, 7, 2), process="Washed", brew_style="Pour Over")

    espresso_only = average_score_by_process(conn, brew_style="Espresso")["items"]
    assert len(espresso_only) == 1
    assert espresso_only[0]["process"] == "Washed"
    assert espresso_only[0]["avg_score"] == 5
    assert espresso_only[0]["count"] == 1


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

    results = {r["origin_country"]: r for r in average_score_by_origin_country(conn)["items"]}
    assert results["Colombia"]["avg_score"] == 7
    assert results["Colombia"]["count"] == 2
    assert results["Ethiopia"]["avg_score"] == 9


def test_average_score_by_origin_country_sorted_best_first(conn):
    # Both countries get several ratings each so the ranking reflects real
    # separation rather than being swamped by shrinkage toward the mean.
    for i in range(5):
        _rate_at(conn, "Stumptown", "Hair Bender", 5, date(2026, 7, 1 + i), origin_country="Brazil")
    for i in range(5):
        _rate_at(conn, "Monogram", "Mango", 9, date(2026, 7, 6 + i), origin_country="Ethiopia")
    results = average_score_by_origin_country(conn)["items"]
    assert [r["origin_country"] for r in results] == ["Ethiopia", "Brazil"]


# --- average_score_by_tasting_note ---


def test_average_score_by_tasting_note_splits_and_dedups_case(conn):
    _rate_at(conn, "Stumptown", "A", 8, date(2026, 7, 1), printed_tasting_notes="Mango, Papaya")
    _rate_at(conn, "Monogram", "B", 6, date(2026, 7, 2), printed_tasting_notes="mango")

    results = {r["note"]: r for r in average_score_by_tasting_note(conn)["items"]}
    assert results["Mango"]["count"] == 2
    assert results["Mango"]["avg_score"] == 7
    assert results["Papaya"]["count"] == 1


def test_average_score_by_tasting_note_handles_dash_delimited_bag(conn):
    _rate_at(conn, "Pallet Coffee", "Elkin Guzman", 9, date(2026, 7, 1), printed_tasting_notes="Hibiscus - Peach - Tropical Fruits")
    results = {r["note"] for r in average_score_by_tasting_note(conn)["items"]}
    assert results == {"Hibiscus", "Peach", "Tropical Fruits"}


def test_average_score_by_tasting_note_ranked_best_first(conn):
    # Several ratings each, so a real gap survives shrinkage rather than
    # both single-sample notes collapsing toward the same adjusted score.
    for i in range(5):
        _rate_at(conn, "A", "A", 5, date(2026, 7, 1 + i), printed_tasting_notes="Citrus")
    for i in range(5):
        _rate_at(conn, "B", "B", 9, date(2026, 7, 6 + i), printed_tasting_notes="Chocolate")
    results = average_score_by_tasting_note(conn)["items"]
    assert results[0]["note"] == "Chocolate"


def test_average_score_by_tasting_note_sample_size_beats_a_lone_outlier(conn):
    # The literal ROADMAP.md example: a note rated once at 9 must not
    # outrank a note rated ten times averaging 8.5. A few other notes at
    # more typical scores are included so the shrinkage prior reflects a
    # realistic coffee log, not just the two notes being compared.
    _rate_at(conn, "A", "A", 9, date(2026, 7, 1), printed_tasting_notes="Rare Note")
    for i in range(10):
        _rate_at(conn, "B", "B", 8.5, date(2026, 7, 2 + i), printed_tasting_notes="Common Note")
    for i in range(5):
        _rate_at(conn, "C", "C", 6, date(2026, 6, 1 + i), printed_tasting_notes="Nutty")
    for i in range(5):
        _rate_at(conn, "D", "D", 6.5, date(2026, 6, 10 + i), printed_tasting_notes="Berry")

    results = average_score_by_tasting_note(conn)["items"]
    assert results[0]["note"] == "Common Note"


# --- average_score_by_brew_style ---


def test_average_score_by_brew_style_groups_and_averages(conn):
    _rate_at(conn, "Stumptown", "Hair Bender", 8, date(2026, 7, 1), brew_style="Espresso")
    _rate_at(conn, "Intelligentsia", "Black Cat", 6, date(2026, 7, 2), brew_style="Espresso")
    _rate_at(conn, "Monogram", "Mango", 9, date(2026, 7, 3), brew_style="Pour Over")

    results = {r["brew_style"]: r for r in average_score_by_brew_style(conn)["items"]}
    assert results["Espresso"]["avg_score"] == 7
    assert results["Espresso"]["count"] == 2
    assert results["Pour Over"]["avg_score"] == 9


def test_average_score_by_brew_style_excludes_null(conn):
    _rate_at(conn, "Stumptown", "Hair Bender", 8, date(2026, 7, 1), brew_style=None)
    assert average_score_by_brew_style(conn)["items"] == []


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
    assert result["by_process"]["recent"]["items"] == []
    assert result["by_origin_country"]["recent"]["items"] == []
    assert result["by_tasting_note"]["recent"]["items"] == []
    assert result["by_brew_style"]["recent"]["items"] == []
    assert result["most_repurchased"]["recent"] == []


def test_get_insights_includes_brew_style_breakdown(conn):
    _rate_at(conn, "Stumptown", "Hair Bender", 8, date(2026, 7, 1), brew_style="Espresso")
    result = get_insights(conn, today=date(2026, 8, 4))
    items = result["by_brew_style"]["all_time"]["items"]
    assert len(items) == 1
    assert items[0]["brew_style"] == "Espresso"
    assert items[0]["avg_score"] == 8


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
    assert [r["process"] for r in result["by_process"]["all_time"]["items"]] == ["Washed"]
    assert result["by_process"]["all_time"]["items"][0]["avg_score"] == 8
    assert result["by_origin_country"]["all_time"]["items"][0]["avg_score"] == 8
    assert result["by_tasting_note"]["all_time"]["items"][0]["avg_score"] == 8
    # by_brew_style itself is never sliced by the brew_style filter - it's
    # the dimension being filtered on, not one more thing to filter.
    brew_styles = {r["brew_style"] for r in result["by_brew_style"]["all_time"]["items"]}
    assert brew_styles == {"Espresso", "Pour Over"}


def test_get_insights_includes_origin_and_tasting_note_breakdowns(conn):
    _rate_at(conn, "Stumptown", "Hair Bender", 8, date(2026, 7, 1), origin_country="Colombia", printed_tasting_notes="Chocolate")
    result = get_insights(conn, today=date(2026, 8, 4))
    assert result["by_origin_country"]["all_time"]["items"][0]["origin_country"] == "Colombia"
    assert result["by_tasting_note"]["all_time"]["items"][0]["note"] == "Chocolate"


def test_get_insights_respects_recent_window_setting_override(conn):
    # 1.4.0: a settings-table override (set via the Settings UI) beats the
    # RECENT_WINDOW_COUNT env var default of 10.
    crud.set_setting(conn, "recent_window_count", "1")
    crud.set_setting(conn, "recent_window_months", "1")
    for i in range(3):
        _rate_at(conn, f"Roaster {i}", "Bean", 7, date(2026, 7, 1 + i))

    result = get_insights(conn, today=date(2026, 8, 4))
    assert result["recent_window"]["applicable"] is True


def test_get_insights_empty_database(conn):
    result = get_insights(conn, today=date(2026, 8, 4))
    assert result["monthly_trend"] == []
    assert result["by_process"]["all_time"]["items"] == []
    assert result["by_origin_country"]["all_time"]["items"] == []
    assert result["by_tasting_note"]["all_time"]["items"] == []
    assert result["most_repurchased"]["all_time"] == []
    assert result["recent_window"]["applicable"] is False


# --- insights_for_window (0.9.0 AI narrative insights) ---


def test_insights_for_window_flattens_all_time():
    ranking = {"items": [{"process": "Washed", "avg_score": 8, "count": 1, "adjusted_score": 7.5}], "significance": NOT_COMPARABLE}
    empty_ranking = {"items": [], "significance": NOT_COMPARABLE}
    all_insights = {
        "monthly_trend": [{"month": "2026-07", "avg_score": 8, "count": 1}],
        "by_process": {"all_time": ranking, "recent": empty_ranking},
        "by_origin_country": {"all_time": empty_ranking, "recent": empty_ranking},
        "by_tasting_note": {"all_time": empty_ranking, "recent": empty_ranking},
        "most_repurchased": {"all_time": [], "recent": []},
        "recent_window": {"applicable": False, "cutoff_date": None},
    }
    windowed = insights_for_window(all_insights, "all_time")
    assert windowed == {
        "monthly_trend": [{"month": "2026-07", "avg_score": 8, "count": 1}],
        "by_process": ranking,
        "by_origin_country": empty_ranking,
        "by_tasting_note": empty_ranking,
        "most_repurchased": [],
    }
    assert "recent_window" not in windowed


def test_insights_for_window_picks_recent_slice():
    all_time_ranking = {"items": [{"process": "Washed"}], "significance": NOT_COMPARABLE}
    recent_ranking = {"items": [{"process": "Natural"}], "significance": NOT_COMPARABLE}
    empty_ranking = {"items": [], "significance": NOT_COMPARABLE}
    all_insights = {
        "monthly_trend": [],
        "by_process": {"all_time": all_time_ranking, "recent": recent_ranking},
        "by_origin_country": {"all_time": empty_ranking, "recent": empty_ranking},
        "by_tasting_note": {"all_time": empty_ranking, "recent": empty_ranking},
        "most_repurchased": {"all_time": [], "recent": []},
        "recent_window": {"applicable": True, "cutoff_date": date(2026, 7, 1)},
    }
    windowed = insights_for_window(all_insights, "recent")
    assert windowed["by_process"] == recent_ranking
