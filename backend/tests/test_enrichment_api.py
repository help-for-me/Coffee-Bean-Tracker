import json

from backend import enrichment
from backend.matcher.base import RoasterMatcher


class FakeMatcher(RoasterMatcher):
    def __init__(self, find_result=None, extract_result=None):
        self.find_result = find_result
        self.extract_result = extract_result
        self.find_calls = []

    def find_candidates(self, roaster, bean_name, extra_context=None):
        self.find_calls.append(extra_context)
        return self.find_result

    def fetch_and_extract(self, url):
        return self.extract_result


def _create_entry(client, roaster="Funk Coffee", bean_name="Here Comes the Flood", score=8):
    response = client.post(
        "/api/entries",
        data={"data": json.dumps({"entry_type": "bag", "roaster": roaster, "bean_name": bean_name, "score": score})},
    )
    return response.json()


def test_typed_identity_entry_triggers_lookup_and_needs_review_surfaces_on_entry(client, monkeypatch):
    # The create-entry response is built before the background lookup runs
    # (it always finishes after the response is sent, even against a real
    # server - a web search takes seconds) so it can only ever show
    # 'pending' here; the eventual needs_review/confirmed/no_match outcome
    # is what a client re-fetching the entry afterwards would see. TestClient
    # happens to run the background task synchronously within client.post(),
    # so by the time that call returns the DB already has the final state,
    # even though this response body was captured before it ran.
    candidates = [{"url": "https://funkcoffee.ca/a", "title": "A", "snippet": "maybe this one"}]
    monkeypatch.setattr(
        enrichment, "get_matcher", lambda: FakeMatcher(find_result={"confident_match": None, "candidates": candidates})
    )

    entry = _create_entry(client)
    assert entry["bean_profile"]["enrichment"]["status"] == "pending"

    refetched = client.get(f"/api/entries/{entry['id']}").json()
    assert refetched["bean_profile"]["enrichment"]["status"] == "needs_review"
    assert refetched["bean_profile"]["enrichment"]["candidates"] == candidates


def test_confident_match_auto_confirms_and_fills_entry(client, monkeypatch):
    monkeypatch.setattr(
        enrichment,
        "get_matcher",
        lambda: FakeMatcher(
            find_result={"confident_match": {"url": "https://funkcoffee.ca/a", "title": "A"}, "candidates": []},
            extract_result={"fields": {"origin_country": "Kenya"}, "source_text": "page text"},
        ),
    )

    entry = _create_entry(client)

    refetched = client.get(f"/api/entries/{entry['id']}").json()
    assert refetched["bean_profile"]["enrichment"]["status"] == "confirmed"
    assert refetched["bean_profile"]["enrichment"]["source_url"] == "https://funkcoffee.ca/a"
    assert refetched["origin_country"] == "Kenya"


def test_provisional_identity_entry_never_triggers_lookup(client):
    response = client.post(
        "/api/entries",
        data={"data": json.dumps({"entry_type": "bag", "score": 7})},
        files=[("photos", ("bag.jpg", b"\xff\xd8\xff" + b"fake-image-bytes", "image/jpeg"))],
    )
    entry = response.json()
    assert entry["bean_profile"]["is_provisional"] is True
    assert entry["bean_profile"]["enrichment"] is None


def test_confirm_candidate_rejects_a_url_not_offered(client, monkeypatch):
    monkeypatch.setattr(
        enrichment,
        "get_matcher",
        lambda: FakeMatcher(
            find_result={"confident_match": None, "candidates": [{"url": "https://a.com", "title": "A", "snippet": "s"}]}
        ),
    )
    entry = _create_entry(client)
    bean_profile_id = entry["bean_profile"]["id"]

    response = client.post(
        f"/api/bean-profiles/{bean_profile_id}/enrichment/confirm", json={"url": "https://not-offered.com", "title": "X"}
    )
    assert response.status_code == 422


def test_confirm_candidate_success(client, monkeypatch):
    monkeypatch.setattr(
        enrichment,
        "get_matcher",
        lambda: FakeMatcher(
            find_result={"confident_match": None, "candidates": [{"url": "https://a.com", "title": "A", "snippet": "s"}]},
            extract_result={"fields": {"process": "Washed"}, "source_text": "page text"},
        ),
    )
    entry = _create_entry(client)
    bean_profile_id = entry["bean_profile"]["id"]

    response = client.post(
        f"/api/bean-profiles/{bean_profile_id}/enrichment/confirm", json={"url": "https://a.com", "title": "A"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "pending"  # background fetch/extract hasn't run yet at response time

    updated_entry = client.get(f"/api/entries/{entry['id']}").json()
    assert updated_entry["bean_profile"]["enrichment"]["status"] == "confirmed"
    assert updated_entry["bean_profile"]["enrichment"]["source_url"] == "https://a.com"
    assert updated_entry["process"] == "Washed"


def test_confirm_candidate_missing_bean_profile_404(client):
    response = client.post("/api/bean-profiles/999/enrichment/confirm", json={"url": "https://a.com", "title": "A"})
    assert response.status_code == 404


def test_confirm_candidate_no_lookup_attempted_yet_404(client):
    entry = _create_entry(client)  # no matcher patched -> real matcher fails, no API key -> status 'failed', not 'needs_review'
    bean_profile_id = entry["bean_profile"]["id"]

    response = client.post(
        f"/api/bean-profiles/{bean_profile_id}/enrichment/confirm", json={"url": "https://a.com", "title": "A"}
    )
    assert response.status_code == 422  # a row exists (status 'failed'), just no candidates to match against


def test_reprocess_none_of_these_reruns_with_context(client, monkeypatch):
    matcher = FakeMatcher(find_result={"confident_match": None, "candidates": []})
    monkeypatch.setattr(enrichment, "get_matcher", lambda: matcher)
    entry = _create_entry(client)
    bean_profile_id = entry["bean_profile"]["id"]

    response = client.post(
        f"/api/bean-profiles/{bean_profile_id}/enrichment/reprocess",
        json={"context": "It's roasted under their subscription-only 'Floodwater' label"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "pending"  # background lookup hasn't run yet at response time

    refetched = client.get(f"/api/entries/{entry['id']}").json()
    assert refetched["bean_profile"]["enrichment"]["status"] == "no_match"
    assert matcher.find_calls[-1] == "It's roasted under their subscription-only 'Floodwater' label"


def test_reprocess_missing_bean_profile_404(client):
    response = client.post("/api/bean-profiles/999/enrichment/reprocess", json={})
    assert response.status_code == 404


def test_reprocess_second_immediate_call_is_cooled_down(client, monkeypatch):
    monkeypatch.setattr(
        enrichment, "get_matcher", lambda: FakeMatcher(find_result={"confident_match": None, "candidates": []})
    )
    entry = _create_entry(client)
    bean_profile_id = entry["bean_profile"]["id"]

    first = client.post(f"/api/bean-profiles/{bean_profile_id}/enrichment/reprocess", json={})
    assert first.status_code == 200

    second = client.post(f"/api/bean-profiles/{bean_profile_id}/enrichment/reprocess", json={})
    assert second.status_code == 429


def test_second_entry_for_same_bean_profile_does_not_retrigger_lookup(client, monkeypatch):
    matcher = FakeMatcher(find_result={"confident_match": None, "candidates": []})
    monkeypatch.setattr(enrichment, "get_matcher", lambda: matcher)

    _create_entry(client)
    assert len(matcher.find_calls) == 1

    _create_entry(client)  # same roaster/bean_name -> same bean_profile, already attempted
    assert len(matcher.find_calls) == 1
