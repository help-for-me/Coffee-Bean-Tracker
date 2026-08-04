from backend import crud
from backend.models import EntryCreate, RatingCreate


def _create(conn, roaster="Stumptown", bean_name="Hair Bender", score=7, **fields):
    data = EntryCreate(entry_type="bag", roaster=roaster, bean_name=bean_name, score=score, **fields)
    return crud.create_entry(conn, data)


# --- update_entry ---


def test_update_entry_updates_provided_fields(conn):
    entry_id = _create(conn)
    updated = crud.update_entry(conn, entry_id, {"origin_country": "Colombia", "roast_level": "Medium"})
    assert updated is True
    entry = crud.get_entry(conn, entry_id)
    assert entry["origin_country"] == "Colombia"
    assert entry["roast_level"] == "Medium"


def test_update_entry_leaves_unprovided_fields_alone(conn):
    entry_id = _create(conn, origin_country="Colombia")
    crud.update_entry(conn, entry_id, {"roast_level": "Dark"})
    entry = crud.get_entry(conn, entry_id)
    assert entry["origin_country"] == "Colombia"
    assert entry["roast_level"] == "Dark"


def test_update_entry_can_clear_a_field_to_null(conn):
    entry_id = _create(conn, batch_number="L-2024-08")
    crud.update_entry(conn, entry_id, {"batch_number": None})
    entry = crud.get_entry(conn, entry_id)
    assert entry["batch_number"] is None


def test_update_entry_ignores_non_updatable_keys(conn):
    entry_id = _create(conn)
    # entry_type/roaster aren't in _UPDATABLE_ENTRY_FIELDS - identity and
    # entry type aren't editable through this path.
    updated = crud.update_entry(conn, entry_id, {"entry_type": "cafe_cup", "roast_level": "Light"})
    assert updated is True
    entry = crud.get_entry(conn, entry_id)
    assert entry["entry_type"] == "bag"
    assert entry["roast_level"] == "Light"


def test_update_entry_missing_entry_returns_false(conn):
    assert crud.update_entry(conn, 999, {"roast_level": "Light"}) is False


def test_update_entry_no_fields_but_entry_exists_returns_true(conn):
    entry_id = _create(conn)
    assert crud.update_entry(conn, entry_id, {}) is True


def test_update_entry_serializes_dates(conn):
    import datetime

    entry_id = _create(conn)
    crud.update_entry(conn, entry_id, {"roast_date": datetime.date(2026, 6, 1)})
    entry = crud.get_entry(conn, entry_id)
    assert entry["roast_date"] == "2026-06-01"


# --- delete_entry ---


def test_delete_entry_cascades_ratings_farms(conn):
    entry_id = _create(conn)
    crud.add_rating(conn, entry_id, RatingCreate(score=8))
    crud.apply_extraction_result(conn, entry_id, {"farms": [{"farm_name": "Finca X", "location": None}]})

    crud.delete_entry(conn, entry_id)

    assert conn.execute("SELECT COUNT(*) AS n FROM ratings WHERE entry_id = ?", (entry_id,)).fetchone()["n"] == 0
    assert conn.execute("SELECT COUNT(*) AS n FROM entry_farms WHERE entry_id = ?", (entry_id,)).fetchone()["n"] == 0
    assert crud.get_entry(conn, entry_id) is None


def test_delete_entry_returns_photo_paths(conn):
    entry_id = _create(conn)
    crud.add_entry_photo(conn, entry_id, "data/photos/1_test_0.jpg", 0)
    crud.add_entry_photo(conn, entry_id, "data/photos/1_test_1.jpg", 1)

    paths = crud.delete_entry(conn, entry_id)

    assert sorted(paths) == ["data/photos/1_test_0.jpg", "data/photos/1_test_1.jpg"]
    assert conn.execute("SELECT COUNT(*) AS n FROM entry_photos WHERE entry_id = ?", (entry_id,)).fetchone()["n"] == 0


def test_delete_entry_missing_returns_none(conn):
    assert crud.delete_entry(conn, 999) is None


def test_delete_entry_does_not_touch_other_entries(conn):
    keep_id = _create(conn, roaster="Keep Me", bean_name="X")
    delete_id = _create(conn, roaster="Delete Me", bean_name="Y")
    crud.delete_entry(conn, delete_id)
    assert crud.get_entry(conn, keep_id) is not None


# --- update_rating / delete_rating ---


def test_update_rating_updates_fields(conn):
    entry_id = _create(conn, score=6)
    rating_id = crud.add_rating(conn, entry_id, RatingCreate(score=8, narrative_notes="Great"))
    crud.update_rating(conn, rating_id, {"score": 9, "narrative_notes": "Even better"})
    entry = crud.get_entry(conn, entry_id)
    updated_rating = next(r for r in entry["ratings"] if r["id"] == rating_id)
    assert updated_rating["score"] == 9
    assert updated_rating["narrative_notes"] == "Even better"


def test_update_rating_missing_returns_false(conn):
    assert crud.update_rating(conn, 999, {"score": 9}) is False


def test_delete_rating_removes_it(conn):
    entry_id = _create(conn, score=6)
    rating_id = crud.add_rating(conn, entry_id, RatingCreate(score=8))
    assert crud.delete_rating(conn, rating_id) is True
    entry = crud.get_entry(conn, entry_id)
    assert all(r["id"] != rating_id for r in entry["ratings"])


def test_delete_rating_missing_returns_false(conn):
    assert crud.delete_rating(conn, 999) is False


# --- photos on get_entry ---


def test_get_entry_includes_own_photos(conn):
    entry_id = _create(conn)
    crud.add_entry_photo(conn, entry_id, "data/photos/1_test_0.jpg", 0)
    entry = crud.get_entry(conn, entry_id)
    assert len(entry["photos"]) == 1
    assert entry["photos"][0]["entry_id"] == entry_id


def test_get_entry_related_photos_from_same_bean_profile(conn):
    first_id = _create(conn, roaster="Monogram", bean_name="Mango")
    crud.add_entry_photo(conn, first_id, "data/photos/first.jpg", 0)
    second_id = _create(conn, roaster="Monogram", bean_name="Mango")
    crud.add_entry_photo(conn, second_id, "data/photos/second.jpg", 0)

    entry = crud.get_entry(conn, second_id)

    assert len(entry["photos"]) == 1
    assert len(entry["related_photos"]) == 1
    assert entry["related_photos"][0]["entry_id"] == first_id


def test_get_entry_related_photos_excludes_unrelated_beans(conn):
    entry_id = _create(conn, roaster="Monogram", bean_name="Mango")
    other_id = _create(conn, roaster="Stumptown", bean_name="Hair Bender")
    crud.add_entry_photo(conn, other_id, "data/photos/other.jpg", 0)

    entry = crud.get_entry(conn, entry_id)

    assert entry["related_photos"] == []


def test_get_entry_photo_paths_ordered(conn):
    entry_id = _create(conn)
    crud.add_entry_photo(conn, entry_id, "data/photos/1_test_1.jpg", 1)
    crud.add_entry_photo(conn, entry_id, "data/photos/1_test_0.jpg", 0)
    assert crud.get_entry_photo_paths(conn, entry_id) == ["data/photos/1_test_0.jpg", "data/photos/1_test_1.jpg"]


def test_mark_extraction_pending(conn):
    entry_id = _create(conn)
    crud.mark_extraction_failed(conn, entry_id)
    crud.mark_extraction_pending(conn, entry_id)
    entry = crud.get_entry(conn, entry_id)
    assert entry["extraction_status"] == "pending"
