from backend import crud
from backend.extraction import run_extraction
from backend.extractor.base import BeanExtractor
from backend.models import EntryCreate


class FakeExtractor(BeanExtractor):
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    def extract(self, image_bytes_list):
        if self.error:
            raise self.error
        return self.result


def _create_pending_entry(conn):
    data = EntryCreate(entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8)
    return crud.create_entry(conn, data, has_photos=True)


def test_run_extraction_success_marks_complete_and_files_fields(conn, tmp_path):
    entry_id = _create_pending_entry(conn)
    photo = tmp_path / "bag.jpg"
    photo.write_bytes(b"fake-image-bytes")

    extractor = FakeExtractor(
        result={
            "origin_country": "Colombia",
            "region": "Huila",
            "farm_producer": None,
            "altitude_m": 1800,
            "variety": None,
            "process": "washed",
            "co_ferment_status": "no",
            "co_ferment_ingredient": None,
            "certifications": None,
            "roast_level": "light",
            "printed_tasting_notes": "Cherry, brown sugar",
            "roast_date": None,
            "bag_weight_g": 340,
            "batch_number": "L-2024-08",
        }
    )

    run_extraction(entry_id, [str(photo)], extractor=extractor)

    entry = crud.get_entry(conn, entry_id)
    assert entry["extraction_status"] == "complete"
    assert entry["extraction_source"] == "claude"
    assert entry["origin_country"] == "Colombia"
    assert entry["process"] == "washed"
    assert entry["printed_tasting_notes"] == "Cherry, brown sugar"
    assert entry["bag_weight_g"] == 340
    assert entry["batch_number"] == "L-2024-08"


def test_run_extraction_failure_marks_failed_not_stuck_pending(conn, tmp_path):
    entry_id = _create_pending_entry(conn)
    photo = tmp_path / "bag.jpg"
    photo.write_bytes(b"fake-image-bytes")

    run_extraction(entry_id, [str(photo)], extractor=FakeExtractor(error=RuntimeError("simulated failure")))

    entry = crud.get_entry(conn, entry_id)
    assert entry["extraction_status"] == "failed"
    assert entry["origin_country"] is None


def test_run_extraction_missing_photo_file_marks_failed(conn):
    entry_id = _create_pending_entry(conn)

    run_extraction(entry_id, ["/nonexistent/path.jpg"], extractor=FakeExtractor(result={}))

    entry = crud.get_entry(conn, entry_id)
    assert entry["extraction_status"] == "failed"


def test_run_extraction_no_api_key_marks_failed(conn, tmp_path):
    # No extractor override, no ANTHROPIC_API_KEY (guaranteed by the
    # autouse fixture) -> the real ClaudeExtractor fails to construct,
    # and that must resolve to 'failed', not crash or stay pending.
    entry_id = _create_pending_entry(conn)
    photo = tmp_path / "bag.jpg"
    photo.write_bytes(b"fake-image-bytes")

    run_extraction(entry_id, [str(photo)])

    entry = crud.get_entry(conn, entry_id)
    assert entry["extraction_status"] == "failed"


def test_apply_extraction_result_preserves_manual_fields_when_extraction_returns_null(conn):
    data = EntryCreate(
        entry_type="bag",
        roaster="Stumptown",
        bean_name="Hair Bender",
        score=8,
        roast_level="dark",
    )
    entry_id = crud.create_entry(conn, data, has_photos=True)

    crud.apply_extraction_result(conn, entry_id, {"origin_country": "Colombia", "roast_level": None})

    entry = crud.get_entry(conn, entry_id)
    assert entry["origin_country"] == "Colombia"
    assert entry["roast_level"] == "dark"


def test_manual_entry_without_photos_stays_not_applicable(conn):
    data = EntryCreate(entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8)
    entry_id = crud.create_entry(conn, data, has_photos=False)

    entry = crud.get_entry(conn, entry_id)
    assert entry["extraction_status"] == "not_applicable"
    assert entry["extraction_source"] == "manual"


# --- 0.5.0: extraction resolving a provisional bean profile ---


def test_apply_extraction_result_resolves_provisional_profile(conn):
    data = EntryCreate(entry_type="bag", roaster=None, bean_name=None, score=7)
    entry_id = crud.create_entry(conn, data, has_photos=True)

    crud.apply_extraction_result(conn, entry_id, {"roaster": "Monogram", "bean_name": "Mango"})

    entry = crud.get_entry(conn, entry_id)
    assert entry["bean_profile"]["roaster"] == "Monogram"
    assert entry["bean_profile"]["bean_name"] == "Mango"
    assert entry["bean_profile"]["is_provisional"] is False


def test_apply_extraction_result_merges_provisional_into_existing_profile(conn):
    crud.resolve_bean_profile(conn, "Monogram", "Mango")
    data = EntryCreate(entry_type="bag", roaster=None, bean_name=None, score=9)
    entry_id = crud.create_entry(conn, data, has_photos=True)

    crud.apply_extraction_result(conn, entry_id, {"roaster": "Monogram", "bean_name": "Mango"})

    entry = crud.get_entry(conn, entry_id)
    assert entry["bean_profile"]["roaster"] == "Monogram"
    profile_count = conn.execute(
        "SELECT COUNT(*) AS n FROM bean_profiles WHERE roaster = 'Monogram' AND bean_name = 'Mango'"
    ).fetchone()["n"]
    assert profile_count == 1  # no duplicate profile left behind


def test_apply_extraction_result_never_overwrites_a_typed_identity(conn):
    data = EntryCreate(entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8)
    entry_id = crud.create_entry(conn, data, has_photos=True)

    # Extraction returning a (wrong) identity must never rename an already-
    # resolved, manually-typed bean profile.
    crud.apply_extraction_result(conn, entry_id, {"roaster": "Some Other Roaster", "bean_name": "Other Bean"})

    entry = crud.get_entry(conn, entry_id)
    assert entry["bean_profile"]["roaster"] == "Stumptown"
    assert entry["bean_profile"]["bean_name"] == "Hair Bender"


def test_apply_extraction_result_leaves_profile_provisional_when_identity_not_found(conn):
    data = EntryCreate(entry_type="bag", roaster=None, bean_name=None, score=7)
    entry_id = crud.create_entry(conn, data, has_photos=True)

    # A blurry photo or one with no visible identity text - extraction
    # completes but returns nothing usable for roaster/bean_name.
    crud.apply_extraction_result(conn, entry_id, {"origin_country": "Colombia"})

    entry = crud.get_entry(conn, entry_id)
    assert entry["bean_profile"]["is_provisional"] is True
