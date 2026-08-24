import pytest

from backend import crud
from backend.matcher.base import RoasterMatcher
from backend.models import EntryCreate


class FakeMatcher(RoasterMatcher):
    def __init__(self):
        self.find_calls = []

    def find_candidates(self, roaster, bean_name, extra_context=None):
        self.find_calls.append((roaster, bean_name, extra_context))
        return {"confident_match": None, "candidates": []}

    def fetch_and_extract(self, url):
        return {"fields": {}, "source_text": None}


def _create(conn, roaster="Stumptown", bean_name="Hair Bender", score=7, **fields):
    data = EntryCreate(entry_type="bag", roaster=roaster, bean_name=bean_name, score=score, **fields)
    return crud.create_entry(conn, data)


def _bean_profile_id(conn, entry_id):
    return crud.get_entry(conn, entry_id)["bean_profile"]["id"]


# --- crud.update_entry_identity ---


def test_renames_a_single_entry_profile_in_place(conn):
    entry_id = _create(conn, roaster="Here Comes The Flood", bean_name="Kenya Filter")
    old_profile_id = _bean_profile_id(conn, entry_id)

    new_profile_id = crud.update_entry_identity(conn, entry_id, "Funk Coffee", "Here Comes the Flood")

    assert new_profile_id == old_profile_id  # same profile, renamed in place
    entry = crud.get_entry(conn, entry_id)
    assert entry["bean_profile"]["roaster"] == "Funk Coffee"
    assert entry["bean_profile"]["bean_name"] == "Here Comes the Flood"
    assert entry["bean_profile"]["is_provisional"] is False


def test_resolves_a_provisional_profile(conn):
    data = EntryCreate(entry_type="bag", roaster=None, bean_name=None, score=7)
    entry_id = crud.create_entry(conn, data, has_photos=True)
    assert crud.get_entry(conn, entry_id)["bean_profile"]["is_provisional"] is True

    crud.update_entry_identity(conn, entry_id, "Funk Coffee", "Here Comes the Flood")

    entry = crud.get_entry(conn, entry_id)
    assert entry["bean_profile"]["is_provisional"] is False
    assert entry["bean_profile"]["roaster"] == "Funk Coffee"


def test_merges_into_an_existing_matching_profile_and_removes_the_old_one(conn):
    other_entry_id = _create(conn, roaster="Funk Coffee", bean_name="Here Comes the Flood")
    other_profile_id = _bean_profile_id(conn, other_entry_id)
    wrong_entry_id = _create(conn, roaster="Here Comes The Flood", bean_name="Kenya Filter")
    wrong_profile_id = _bean_profile_id(conn, wrong_entry_id)

    new_profile_id = crud.update_entry_identity(conn, wrong_entry_id, "Funk Coffee", "Here Comes the Flood")

    assert new_profile_id == other_profile_id
    assert crud.get_entry(conn, wrong_entry_id)["bean_profile"]["id"] == other_profile_id
    profile_count = conn.execute(
        "SELECT COUNT(*) AS n FROM bean_profiles WHERE roaster = 'Funk Coffee' AND bean_name = 'Here Comes the Flood'"
    ).fetchone()["n"]
    assert profile_count == 1  # no duplicate left behind
    assert conn.execute("SELECT 1 FROM bean_profiles WHERE id = ?", (wrong_profile_id,)).fetchone() is None


def test_splits_one_entry_off_a_shared_profile_rather_than_renaming_everyone(conn):
    entry_1 = _create(conn, roaster="Here Comes The Flood", bean_name="Kenya Filter")
    shared_profile_id = _bean_profile_id(conn, entry_1)
    entry_2 = crud.create_entry(
        conn, EntryCreate(entry_type="bag", roaster="Here Comes The Flood", bean_name="Kenya Filter", score=6)
    )
    assert _bean_profile_id(conn, entry_2) == shared_profile_id

    new_profile_id = crud.update_entry_identity(conn, entry_1, "Funk Coffee", "Here Comes the Flood")

    assert new_profile_id != shared_profile_id
    assert crud.get_entry(conn, entry_1)["bean_profile"]["roaster"] == "Funk Coffee"
    # entry_2 is untouched - still under the old (unrenamed) shared profile
    entry_2_profile = crud.get_entry(conn, entry_2)["bean_profile"]
    assert entry_2_profile["id"] == shared_profile_id
    assert entry_2_profile["roaster"] == "Here Comes The Flood"


def test_missing_entry_returns_none(conn):
    assert crud.update_entry_identity(conn, 999, "Funk Coffee", "Here Comes the Flood") is None


def test_clears_stale_enrichment_when_renaming_in_place(conn):
    entry_id = _create(conn, roaster="Here Comes The Flood", bean_name="Kenya Filter")
    profile_id = _bean_profile_id(conn, entry_id)
    crud.mark_enrichment_no_match(conn, profile_id)
    assert crud.get_enrichment(conn, profile_id)["status"] == "no_match"

    crud.update_entry_identity(conn, entry_id, "Funk Coffee", "Here Comes the Flood")

    # stale result against the wrong name is gone - a fresh lookup can trigger
    assert crud.get_enrichment(conn, profile_id) is None
    assert crud.maybe_start_enrichment(conn, profile_id) is True


# --- API layer ---


def test_identity_endpoint_corrects_name_and_retriggers_enrichment(client, monkeypatch):
    from backend import enrichment

    matcher = FakeMatcher()
    monkeypatch.setattr(enrichment, "get_matcher", lambda: matcher)

    response = client.post(
        "/api/entries",
        data={
            "data": '{"entry_type": "bag", "roaster": "Here Comes The Flood", "bean_name": "Kenya Filter", "score": 8}'
        },
    )
    entry_id = response.json()["id"]
    assert matcher.find_calls[-1][:2] == ("Here Comes The Flood", "Kenya Filter")

    identity_response = client.patch(
        f"/api/entries/{entry_id}/identity", json={"roaster": "Funk Coffee", "bean_name": "Here Comes the Flood"}
    )
    assert identity_response.status_code == 200
    body = identity_response.json()
    assert body["bean_profile"]["roaster"] == "Funk Coffee"
    assert body["bean_profile"]["bean_name"] == "Here Comes the Flood"
    # the identity fix retriggered a fresh lookup, this time with the
    # corrected name
    assert matcher.find_calls[-1][:2] == ("Funk Coffee", "Here Comes the Flood")


def test_identity_endpoint_rejects_blank_roaster(client):
    response = client.post(
        "/api/entries",
        data={"data": '{"entry_type": "bag", "roaster": "X", "bean_name": "Y", "score": 8}'},
    )
    entry_id = response.json()["id"]

    response = client.patch(f"/api/entries/{entry_id}/identity", json={"roaster": "  ", "bean_name": "Y"})
    assert response.status_code == 422


def test_identity_endpoint_missing_entry_404(client):
    response = client.patch("/api/entries/999/identity", json={"roaster": "X", "bean_name": "Y"})
    assert response.status_code == 404
