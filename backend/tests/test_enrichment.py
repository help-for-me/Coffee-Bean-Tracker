from pathlib import Path

import pytest

from backend import crud, enrichment_sources
from backend.enrichment import run_enrichment_confirm, run_enrichment_lookup
from backend.matcher.base import RoasterMatcher
from backend.models import EntryCreate


@pytest.fixture(autouse=True)
def _sources_path(tmp_path, monkeypatch):
    # These jobs save fetched page text to disk (enrichment_sources.py) -
    # without this, tests would write into the repo's real data/ directory.
    monkeypatch.setattr(enrichment_sources, "SOURCES_PATH", tmp_path / "enrichment_sources")


class FakeMatcher(RoasterMatcher):
    def __init__(self, find_result=None, extract_result=None, find_error=None, extract_error=None):
        self.find_result = find_result
        self.extract_result = extract_result
        self.find_error = find_error
        self.extract_error = extract_error
        self.find_calls = []
        self.extract_calls = []

    def find_candidates(self, roaster, bean_name, extra_context=None):
        self.find_calls.append((roaster, bean_name, extra_context))
        if self.find_error:
            raise self.find_error
        return self.find_result

    def fetch_and_extract(self, url):
        self.extract_calls.append(url)
        if self.extract_error:
            raise self.extract_error
        return self.extract_result


def _create_entry(conn, roaster="Funk Coffee", bean_name="Here Comes the Flood", **fields):
    data = EntryCreate(entry_type="bag", roaster=roaster, bean_name=bean_name, score=8, **fields)
    return crud.create_entry(conn, data)


def _bean_profile_id(conn, entry_id):
    return crud.get_entry(conn, entry_id)["bean_profile"]["id"]


# --- crud.maybe_start_enrichment ---


def test_maybe_start_enrichment_true_for_new_non_provisional_profile(conn):
    entry_id = _create_entry(conn)
    assert crud.maybe_start_enrichment(conn, _bean_profile_id(conn, entry_id)) is True


def test_maybe_start_enrichment_false_once_already_attempted(conn):
    entry_id = _create_entry(conn)
    bean_profile_id = _bean_profile_id(conn, entry_id)
    assert crud.maybe_start_enrichment(conn, bean_profile_id) is True
    assert crud.maybe_start_enrichment(conn, bean_profile_id) is False


def test_maybe_start_enrichment_false_for_provisional_profile(conn):
    data = EntryCreate(entry_type="bag", roaster=None, bean_name=None, score=7)
    entry_id = crud.create_entry(conn, data, has_photos=True)
    assert crud.maybe_start_enrichment(conn, _bean_profile_id(conn, entry_id)) is False


def test_maybe_start_enrichment_false_for_unknown_profile(conn):
    assert crud.maybe_start_enrichment(conn, 999) is False


# --- run_enrichment_lookup outcomes ---


def test_confident_match_auto_confirms_and_fills_gaps(conn):
    entry_id = _create_entry(conn)
    bean_profile_id = _bean_profile_id(conn, entry_id)
    matcher = FakeMatcher(
        find_result={
            "confident_match": {"url": "https://funkcoffee.ca/here-comes-the-flood", "title": "Here Comes the Flood"},
            "candidates": [],
        },
        extract_result={
            "fields": {"origin_country": "Kenya", "process": "Washed", "roast_level": "Light"},
            "source_text": "full page text",
        },
    )

    run_enrichment_lookup(bean_profile_id, matcher=matcher)

    enrichment = crud.get_enrichment(conn, bean_profile_id)
    assert enrichment["status"] == "confirmed"
    assert enrichment["source_url"] == "https://funkcoffee.ca/here-comes-the-flood"
    assert enrichment["candidates"] == []
    entry = crud.get_entry(conn, entry_id)
    assert entry["origin_country"] == "Kenya"
    assert entry["process"] == "Washed"
    assert entry["roast_level"] == "Light"


def test_confident_match_never_overwrites_label_data(conn):
    entry_id = _create_entry(conn, origin_country="Colombia")
    bean_profile_id = _bean_profile_id(conn, entry_id)
    matcher = FakeMatcher(
        find_result={"confident_match": {"url": "https://x.com/y", "title": "Y"}, "candidates": []},
        extract_result={"fields": {"origin_country": "Kenya"}, "source_text": None},
    )

    run_enrichment_lookup(bean_profile_id, matcher=matcher)

    assert crud.get_entry(conn, entry_id)["origin_country"] == "Colombia"


def test_confident_match_fills_across_every_entry_sharing_the_profile(conn):
    entry_id_1 = _create_entry(conn)
    entry_id_2 = crud.create_entry(
        conn, EntryCreate(entry_type="bag", roaster="Funk Coffee", bean_name="Here Comes the Flood", score=7)
    )
    bean_profile_id = _bean_profile_id(conn, entry_id_1)
    assert _bean_profile_id(conn, entry_id_2) == bean_profile_id
    matcher = FakeMatcher(
        find_result={"confident_match": {"url": "https://x.com/y", "title": "Y"}, "candidates": []},
        extract_result={"fields": {"process": "Washed"}, "source_text": None},
    )

    run_enrichment_lookup(bean_profile_id, matcher=matcher)

    assert crud.get_entry(conn, entry_id_1)["process"] == "Washed"
    assert crud.get_entry(conn, entry_id_2)["process"] == "Washed"


def test_fills_website_description(conn):
    entry_id = _create_entry(conn)
    bean_profile_id = _bean_profile_id(conn, entry_id)
    matcher = FakeMatcher(
        find_result={"confident_match": {"url": "https://x.com/y", "title": "Y"}, "candidates": []},
        extract_result={"fields": {"website_description": "A juicy, floral Kenyan filter roast."}, "source_text": None},
    )

    run_enrichment_lookup(bean_profile_id, matcher=matcher)

    assert crud.get_entry(conn, entry_id)["website_description"] == "A juicy, floral Kenyan filter roast."


def test_only_fills_co_ferment_status_when_still_unknown(conn):
    entry_id_unknown = _create_entry(conn)
    entry_id_known = crud.create_entry(
        conn,
        EntryCreate(
            entry_type="bag", roaster="Funk Coffee", bean_name="Here Comes the Flood", score=7, co_ferment_status="no"
        ),
    )
    bean_profile_id = _bean_profile_id(conn, entry_id_unknown)
    matcher = FakeMatcher(
        find_result={"confident_match": {"url": "https://x.com/y", "title": "Y"}, "candidates": []},
        extract_result={"fields": {"co_ferment_status": "yes", "co_ferment_ingredient": "cascara"}, "source_text": None},
    )

    run_enrichment_lookup(bean_profile_id, matcher=matcher)

    assert crud.get_entry(conn, entry_id_unknown)["co_ferment_status"] == "yes"
    assert crud.get_entry(conn, entry_id_known)["co_ferment_status"] == "no"


def test_confident_match_saves_source_text_to_a_file(conn):
    entry_id = _create_entry(conn)
    bean_profile_id = _bean_profile_id(conn, entry_id)
    matcher = FakeMatcher(
        find_result={"confident_match": {"url": "https://x.com/y", "title": "Y"}, "candidates": []},
        extract_result={"fields": {}, "source_text": "the roaster's page, as fetched"},
    )

    run_enrichment_lookup(bean_profile_id, matcher=matcher)

    row = conn.execute(
        "SELECT source_path FROM bean_profile_enrichment WHERE bean_profile_id = ?", (bean_profile_id,)
    ).fetchone()
    saved = Path(row["source_path"])
    assert saved.read_text(encoding="utf-8") == "the roaster's page, as fetched"


def test_candidates_sets_needs_review(conn):
    entry_id = _create_entry(conn)
    bean_profile_id = _bean_profile_id(conn, entry_id)
    candidates = [
        {"url": "https://a.com", "title": "A", "snippet": "current lineup, no exact name match"},
        {"url": "https://b.com", "title": "B", "snippet": "same name, different roaster"},
    ]
    matcher = FakeMatcher(find_result={"confident_match": None, "candidates": candidates})

    run_enrichment_lookup(bean_profile_id, matcher=matcher)

    enrichment = crud.get_enrichment(conn, bean_profile_id)
    assert enrichment["status"] == "needs_review"
    assert enrichment["candidates"] == candidates


def test_no_candidates_marks_no_match(conn):
    entry_id = _create_entry(conn)
    bean_profile_id = _bean_profile_id(conn, entry_id)
    matcher = FakeMatcher(find_result={"confident_match": None, "candidates": []})

    run_enrichment_lookup(bean_profile_id, matcher=matcher)

    enrichment = crud.get_enrichment(conn, bean_profile_id)
    assert enrichment["status"] == "no_match"
    assert enrichment["candidates"] == []


def test_lookup_error_marks_failed_not_stuck_pending(conn):
    entry_id = _create_entry(conn)
    bean_profile_id = _bean_profile_id(conn, entry_id)
    matcher = FakeMatcher(find_error=RuntimeError("simulated search failure"))

    run_enrichment_lookup(bean_profile_id, matcher=matcher)

    assert crud.get_enrichment(conn, bean_profile_id)["status"] == "failed"


def test_lookup_passes_extra_context_through_to_the_matcher(conn):
    entry_id = _create_entry(conn)
    bean_profile_id = _bean_profile_id(conn, entry_id)
    matcher = FakeMatcher(find_result={"confident_match": None, "candidates": []})

    run_enrichment_lookup(bean_profile_id, extra_context="It's their 2024 Kenya lot, not last year's", matcher=matcher)

    assert matcher.find_calls[0] == ("Funk Coffee", "Here Comes the Flood", "It's their 2024 Kenya lot, not last year's")


def test_lookup_for_unknown_bean_profile_is_a_noop(conn):
    matcher = FakeMatcher(find_result={"confident_match": None, "candidates": []})

    run_enrichment_lookup(999, matcher=matcher)

    assert matcher.find_calls == []
    assert crud.get_enrichment(conn, 999) is None


# --- run_enrichment_confirm (the "user picked one of the 3 candidates" path) ---


def test_confirm_extracts_fields_and_saves_source(conn):
    entry_id = _create_entry(conn)
    bean_profile_id = _bean_profile_id(conn, entry_id)
    crud.mark_enrichment_pending(conn, bean_profile_id)
    matcher = FakeMatcher(extract_result={"fields": {"process": "Washed"}, "source_text": "fetched text"})

    run_enrichment_confirm(bean_profile_id, "https://funkcoffee.ca/x", "X", matcher=matcher)

    enrichment = crud.get_enrichment(conn, bean_profile_id)
    assert enrichment["status"] == "confirmed"
    assert enrichment["source_url"] == "https://funkcoffee.ca/x"
    assert crud.get_entry(conn, entry_id)["process"] == "Washed"
    assert matcher.extract_calls == ["https://funkcoffee.ca/x"]


def test_confirm_error_marks_failed(conn):
    entry_id = _create_entry(conn)
    bean_profile_id = _bean_profile_id(conn, entry_id)
    crud.mark_enrichment_pending(conn, bean_profile_id)
    matcher = FakeMatcher(extract_error=RuntimeError("simulated fetch failure"))

    run_enrichment_confirm(bean_profile_id, "https://funkcoffee.ca/x", "X", matcher=matcher)

    assert crud.get_enrichment(conn, bean_profile_id)["status"] == "failed"


# --- crud.mark_enrichment_pending (reprocess reset) ---


def test_mark_enrichment_pending_resets_candidates_and_sets_context(conn):
    entry_id = _create_entry(conn)
    bean_profile_id = _bean_profile_id(conn, entry_id)
    crud.save_enrichment_candidates(conn, bean_profile_id, [{"url": "https://a.com", "title": "A", "snippet": "s"}])

    crud.mark_enrichment_pending(conn, bean_profile_id, extra_context="Try their retail site, not the wholesale one")

    enrichment = crud.get_enrichment(conn, bean_profile_id)
    assert enrichment["status"] == "pending"
    assert enrichment["candidates"] == []


def test_mark_enrichment_pending_works_even_with_no_existing_row(conn):
    # A manual reprocess on a profile that's never had a lookup attempted
    # (the row-absence == "not started yet" case) - should upsert cleanly.
    entry_id = _create_entry(conn)
    bean_profile_id = _bean_profile_id(conn, entry_id)
    assert crud.get_enrichment(conn, bean_profile_id) is None

    crud.mark_enrichment_pending(conn, bean_profile_id, extra_context=None)

    assert crud.get_enrichment(conn, bean_profile_id)["status"] == "pending"


# --- website_description is a normal editable field ---


def test_website_description_round_trips_through_update_entry(conn):
    entry_id = _create_entry(conn)
    crud.update_entry(conn, entry_id, {"website_description": "A juicy Kenyan filter roast."})
    assert crud.get_entry(conn, entry_id)["website_description"] == "A juicy Kenyan filter roast."
