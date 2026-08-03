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


def test_add_rating_appends_second_rating(conn):
    entry_id = crud.create_entry(
        conn, EntryCreate(entry_type="cafe_cup", roaster="Local Cafe", bean_name="House Blend", score=6)
    )
    crud.add_rating(conn, entry_id, RatingCreate(score=8, narrative_notes="Better second time"))
    entry = crud.get_entry(conn, entry_id)
    assert len(entry["ratings"]) == 2
    assert entry["ratings"][1]["score"] == 8
