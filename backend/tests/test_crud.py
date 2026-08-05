from backend import crud
from backend.models import EntryCreate, RatingCreate


def test_resolve_bean_profile_creates_new(conn):
    profile_id = crud.resolve_bean_profile(conn, "Stumptown", "Hair Bender")
    row = conn.execute(
        "SELECT roaster, bean_name FROM bean_profiles WHERE id = ?", (profile_id,)
    ).fetchone()
    assert row["roaster"] == "Stumptown"
    assert row["bean_name"] == "Hair Bender"


def test_resolve_bean_profile_reuses_existing_case_insensitive(conn):
    first_id = crud.resolve_bean_profile(conn, "Stumptown", "Hair Bender")
    second_id = crud.resolve_bean_profile(conn, "stumptown", "HAIR BENDER")
    assert first_id == second_id
    count = conn.execute("SELECT COUNT(*) AS n FROM bean_profiles").fetchone()["n"]
    assert count == 1


def test_search_bean_profiles_prefix_match(conn):
    crud.resolve_bean_profile(conn, "Stumptown", "Hair Bender")
    crud.resolve_bean_profile(conn, "Intelligentsia", "Black Cat")
    results = crud.search_bean_profiles(conn, "Stump")
    assert len(results) == 1
    assert results[0]["roaster"] == "Stumptown"


def test_search_bean_profiles_no_match_returns_empty(conn):
    crud.resolve_bean_profile(conn, "Stumptown", "Hair Bender")
    assert crud.search_bean_profiles(conn, "Zzz") == []


def test_search_bean_profiles_excludes_provisional(conn):
    crud.create_provisional_bean_profile(conn)
    assert crud.search_bean_profiles(conn, "Unidentified") == []


# --- provisional bean profiles (0.5.0 photo-first identity) ---


def test_create_provisional_bean_profile_has_unique_placeholder_name(conn):
    first_id = crud.create_provisional_bean_profile(conn)
    second_id = crud.create_provisional_bean_profile(conn)
    first = conn.execute("SELECT roaster, bean_name, is_provisional FROM bean_profiles WHERE id = ?", (first_id,)).fetchone()
    second = conn.execute("SELECT bean_name FROM bean_profiles WHERE id = ?", (second_id,)).fetchone()
    assert first["roaster"] == "Unidentified"
    assert first["bean_name"] == f"#{first_id}"
    assert first["is_provisional"] == 1
    assert second["bean_name"] != first["bean_name"]


def test_create_provisional_bean_profile_never_reuses_a_row(conn):
    first_id = crud.create_provisional_bean_profile(conn)
    second_id = crud.create_provisional_bean_profile(conn)
    assert first_id != second_id
    count = conn.execute("SELECT COUNT(*) AS n FROM bean_profiles").fetchone()["n"]
    assert count == 2


def test_resolve_provisional_profile_renames_in_place_when_no_match(conn):
    provisional_id = crud.create_provisional_bean_profile(conn)
    resolved_id = crud.resolve_provisional_profile(conn, provisional_id, "Monogram", "Mango")
    assert resolved_id == provisional_id
    row = conn.execute(
        "SELECT roaster, bean_name, is_provisional FROM bean_profiles WHERE id = ?", (provisional_id,)
    ).fetchone()
    assert row["roaster"] == "Monogram"
    assert row["bean_name"] == "Mango"
    assert row["is_provisional"] == 0


def test_resolve_provisional_profile_merges_into_existing_match(conn):
    existing_id = crud.resolve_bean_profile(conn, "Monogram", "Mango")
    provisional_id = crud.create_provisional_bean_profile(conn)
    entry_id = crud.create_entry(
        conn, EntryCreate(entry_type="bag", roaster=None, bean_name=None, score=7), has_photos=True
    )
    conn.execute("UPDATE entries SET bean_profile_id = ? WHERE id = ?", (provisional_id, entry_id))

    resolved_id = crud.resolve_provisional_profile(conn, provisional_id, "monogram", "MANGO")

    assert resolved_id == existing_id
    entry = conn.execute("SELECT bean_profile_id FROM entries WHERE id = ?", (entry_id,)).fetchone()
    assert entry["bean_profile_id"] == existing_id
    remaining = conn.execute("SELECT id FROM bean_profiles WHERE id = ?", (provisional_id,)).fetchone()
    assert remaining is None  # placeholder discarded


# --- fuzzy repurchase matching (0.8.0) ---


def test_search_bean_profiles_fuzzy_fallback_catches_typo(conn):
    crud.resolve_bean_profile(conn, "Detour Coffee Roasters", "Ethiopia Guji")
    results = crud.search_bean_profiles(conn, "Detuor Coffee Roasters")
    assert len(results) == 1
    assert results[0]["roaster"] == "Detour Coffee Roasters"


def test_search_bean_profiles_prefix_match_takes_priority_over_fuzzy(conn):
    crud.resolve_bean_profile(conn, "Stumptown", "Hair Bender")
    crud.resolve_bean_profile(conn, "Stumptown", "Hair Blender Blend")
    results = crud.search_bean_profiles(conn, "Stump", limit=1)
    assert len(results) == 1
    assert results[0]["bean_name"] == "Hair Bender"


def test_resolve_provisional_profile_fuzzy_merges_ocr_typo(conn):
    # The real 0.5.1 case: same bag, OCR read the bean name slightly
    # differently on two separate photo submissions.
    existing_id = crud.resolve_bean_profile(conn, "Monogram", "Jairo Aroila")
    provisional_id = crud.create_provisional_bean_profile(conn)

    resolved_id = crud.resolve_provisional_profile(conn, provisional_id, "Monogram", "Jario Arcila")

    assert resolved_id == existing_id
    remaining = conn.execute("SELECT id FROM bean_profiles WHERE id = ?", (provisional_id,)).fetchone()
    assert remaining is None


def test_resolve_provisional_profile_does_not_merge_below_cutoff(conn):
    # A different coffee from a similarly-named roaster ("Detour Coffee"
    # vs "Detour Coffee Roasters") is similar enough to surface as an
    # autocomplete suggestion but not similar enough to auto-merge - a
    # real risk of combining two roasters' entries with no undo.
    existing_id = crud.resolve_bean_profile(conn, "Detour Coffee Roasters", "Ethiopia Guji")
    provisional_id = crud.create_provisional_bean_profile(conn)

    resolved_id = crud.resolve_provisional_profile(conn, provisional_id, "Detour Coffee", "Colombia Huila")

    assert resolved_id == provisional_id
    assert resolved_id != existing_id
    row = conn.execute("SELECT roaster, is_provisional FROM bean_profiles WHERE id = ?", (provisional_id,)).fetchone()
    assert row["roaster"] == "Detour Coffee"
    assert row["is_provisional"] == 0


def test_resolve_provisional_profile_unrelated_name_renames_in_place(conn):
    crud.resolve_bean_profile(conn, "Stumptown", "Hair Bender")
    provisional_id = crud.create_provisional_bean_profile(conn)

    resolved_id = crud.resolve_provisional_profile(conn, provisional_id, "Intelligentsia", "Black Cat")

    assert resolved_id == provisional_id
    count = conn.execute("SELECT COUNT(*) AS n FROM bean_profiles").fetchone()["n"]
    assert count == 2


def test_create_entry_without_identity_creates_provisional_profile(conn):
    data = EntryCreate(entry_type="bag", roaster=None, bean_name=None, score=7)
    entry_id = crud.create_entry(conn, data, has_photos=True)
    entry = crud.get_entry(conn, entry_id)
    assert entry["bean_profile"]["is_provisional"] is True
    assert entry["bean_profile"]["roaster"] == "Unidentified"


def test_create_entry_with_identity_does_not_create_provisional_profile(conn):
    data = EntryCreate(entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8)
    entry_id = crud.create_entry(conn, data)
    entry = crud.get_entry(conn, entry_id)
    assert entry["bean_profile"]["is_provisional"] is False


def test_create_entry_creates_profile_entry_and_rating(conn):
    data = EntryCreate(entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8.5)
    entry_id = crud.create_entry(conn, data)

    profile_count = conn.execute("SELECT COUNT(*) AS n FROM bean_profiles").fetchone()["n"]
    entry_count = conn.execute("SELECT COUNT(*) AS n FROM entries").fetchone()["n"]
    rating_count = conn.execute(
        "SELECT COUNT(*) AS n FROM ratings WHERE entry_id = ?", (entry_id,)
    ).fetchone()["n"]

    assert profile_count == 1
    assert entry_count == 1
    assert rating_count == 1


def test_create_entry_reuses_existing_profile(conn):
    crud.resolve_bean_profile(conn, "Stumptown", "Hair Bender")
    data = EntryCreate(entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=7)
    crud.create_entry(conn, data)
    profile_count = conn.execute("SELECT COUNT(*) AS n FROM bean_profiles").fetchone()["n"]
    assert profile_count == 1


def test_get_entry_includes_bean_profile_and_ratings(conn):
    data = EntryCreate(entry_type="cafe_cup", roaster="Local Cafe", bean_name="House Blend", score=6)
    entry_id = crud.create_entry(conn, data)

    entry = crud.get_entry(conn, entry_id)

    assert entry["bean_profile"]["roaster"] == "Local Cafe"
    assert len(entry["ratings"]) == 1
    assert entry["ratings"][0]["score"] == 6


def test_get_entry_missing_returns_none(conn):
    assert crud.get_entry(conn, 999) is None


def test_list_entries_orders_newest_first(conn):
    first_id = crud.create_entry(
        conn, EntryCreate(entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8)
    )
    second_id = crud.create_entry(
        conn, EntryCreate(entry_type="bag", roaster="Intelligentsia", bean_name="Black Cat", score=7)
    )
    results = crud.list_entries(conn)
    assert [r["id"] for r in results] == [second_id, first_id]


def test_list_entries_includes_latest_score(conn):
    entry_id = crud.create_entry(
        conn, EntryCreate(entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=6)
    )
    crud.add_rating(conn, entry_id, RatingCreate(score=9))
    results = crud.list_entries(conn)
    assert results[0]["latest_score"] == 9


def test_list_entries_filters_by_query(conn):
    crud.create_entry(
        conn, EntryCreate(entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8)
    )
    crud.create_entry(
        conn, EntryCreate(entry_type="bag", roaster="Intelligentsia", bean_name="Black Cat", score=7)
    )
    results = crud.list_entries(conn, query="Intelli")
    assert len(results) == 1
    assert results[0]["roaster"] == "Intelligentsia"


def test_list_entries_respects_limit(conn):
    for i in range(3):
        crud.create_entry(
            conn, EntryCreate(entry_type="bag", roaster=f"Roaster {i}", bean_name="Blend", score=5)
        )
    results = crud.list_entries(conn, limit=2)
    assert len(results) == 2


# --- 1.2.0: History filter/sort ---


def test_list_entries_filters_by_entry_type(conn):
    crud.create_entry(
        conn, EntryCreate(entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8)
    )
    crud.create_entry(
        conn, EntryCreate(entry_type="cafe_cup", cafe_name="Local Cafe", roaster="Local Cafe", bean_name="House Blend", score=7)
    )
    results = crud.list_entries(conn, entry_type="cafe_cup")
    assert len(results) == 1
    assert results[0]["entry_type"] == "cafe_cup"


def test_list_entries_sort_date_asc(conn):
    first_id = crud.create_entry(
        conn, EntryCreate(entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8)
    )
    second_id = crud.create_entry(
        conn, EntryCreate(entry_type="bag", roaster="Intelligentsia", bean_name="Black Cat", score=7)
    )
    results = crud.list_entries(conn, sort="date_asc")
    assert [r["id"] for r in results] == [first_id, second_id]


def test_list_entries_sort_score_desc_puts_unrated_last(conn):
    low_id = crud.create_entry(
        conn, EntryCreate(entry_type="bag", roaster="A", bean_name="A", score=5)
    )
    high_id = crud.create_entry(
        conn, EntryCreate(entry_type="bag", roaster="B", bean_name="B", score=9)
    )
    results = crud.list_entries(conn, sort="score_desc")
    assert [r["id"] for r in results] == [high_id, low_id]


def test_list_entries_sort_score_asc(conn):
    low_id = crud.create_entry(
        conn, EntryCreate(entry_type="bag", roaster="A", bean_name="A", score=5)
    )
    high_id = crud.create_entry(
        conn, EntryCreate(entry_type="bag", roaster="B", bean_name="B", score=9)
    )
    results = crud.list_entries(conn, sort="score_asc")
    assert [r["id"] for r in results] == [low_id, high_id]


def test_create_entry_stores_roast_location(conn):
    data = EntryCreate(
        entry_type="bag", roaster="Pallet Coffee", bean_name="Elkin Guzman", score=7,
        roast_location="Vancouver, BC",
    )
    entry_id = crud.create_entry(conn, data)
    entry = crud.get_entry(conn, entry_id)
    assert entry["roast_location"] == "Vancouver, BC"


def test_get_entry_farms_defaults_to_empty_list(conn):
    data = EntryCreate(entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8)
    entry_id = crud.create_entry(conn, data)
    entry = crud.get_entry(conn, entry_id)
    assert entry["farms"] == []


def test_apply_extraction_result_inserts_multiple_farms(conn):
    data = EntryCreate(entry_type="bag", roaster="Blend Co", bean_name="House Blend", score=7)
    entry_id = crud.create_entry(conn, data)
    crud.apply_extraction_result(
        conn,
        entry_id,
        {
            "farms": [
                {"farm_name": "El Mirador", "location": "Huila, Colombia"},
                {"farm_name": "Finca La Esperanza", "location": "Nariño, Colombia"},
            ]
        },
    )
    entry = crud.get_entry(conn, entry_id)
    assert entry["farms"] == [
        {"farm_name": "El Mirador", "location": "Huila, Colombia"},
        {"farm_name": "Finca La Esperanza", "location": "Nariño, Colombia"},
    ]


def test_apply_extraction_result_skips_farms_without_a_name(conn):
    data = EntryCreate(entry_type="bag", roaster="Blend Co", bean_name="House Blend 2", score=7)
    entry_id = crud.create_entry(conn, data)
    crud.apply_extraction_result(conn, entry_id, {"farms": [{"farm_name": "", "location": "Nowhere"}]})
    entry = crud.get_entry(conn, entry_id)
    assert entry["farms"] == []


def test_add_rating_appends_second_rating(conn):
    entry_id = crud.create_entry(
        conn, EntryCreate(entry_type="cafe_cup", roaster="Local Cafe", bean_name="House Blend", score=6)
    )
    crud.add_rating(conn, entry_id, RatingCreate(score=8, narrative_notes="Better second time"))
    entry = crud.get_entry(conn, entry_id)
    assert len(entry["ratings"]) == 2
    assert entry["ratings"][1]["score"] == 8


# --- AI narrative insights (0.9.0) ---


def test_get_latest_narrative_returns_none_when_absent(conn):
    assert crud.get_latest_narrative(conn, "all_time") is None


def test_save_narrative_then_get_latest_returns_it(conn):
    saved = crud.save_narrative(conn, "all_time", "You lean towards washed Colombian coffees.")
    fetched = crud.get_latest_narrative(conn, "all_time")
    assert fetched["id"] == saved["id"]
    assert fetched["summary_text"] == "You lean towards washed Colombian coffees."
    assert fetched["window_type"] == "all_time"


def test_get_latest_narrative_is_scoped_by_window_type(conn):
    crud.save_narrative(conn, "all_time", "All-time summary")
    assert crud.get_latest_narrative(conn, "recent") is None


def test_save_narrative_twice_returns_most_recent_on_get(conn):
    crud.save_narrative(conn, "all_time", "First summary")
    second = crud.save_narrative(conn, "all_time", "Second summary")
    fetched = crud.get_latest_narrative(conn, "all_time")
    assert fetched["id"] == second["id"]
    assert fetched["summary_text"] == "Second summary"
