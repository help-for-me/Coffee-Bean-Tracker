import json

from backend import logging_config
from backend.extraction import run_extraction
from backend.extractor.base import BeanExtractor


def post_entry(client, **fields):
    return client.post("/api/entries", data={"data": json.dumps(fields)})


def test_create_entry_endpoint(client):
    response = post_entry(
        client,
        entry_type="bag",
        roaster="Stumptown",
        bean_name="Hair Bender",
        score=8.5,
        narrative_notes="Chocolatey, bright finish",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["bean_profile"]["roaster"] == "Stumptown"
    assert len(body["ratings"]) == 1
    assert body["ratings"][0]["score"] == 8.5
    assert body["extraction_status"] == "not_applicable"


def test_create_entry_rejects_out_of_range_score(client):
    response = post_entry(client, entry_type="bag", roaster="X", bean_name="Y", score=15)
    assert response.status_code == 422


# --- "log it now, rate later" ---


def test_create_entry_without_score_succeeds(client):
    response = post_entry(client, entry_type="bag", roaster="Stumptown", bean_name="Hair Bender")
    assert response.status_code == 201
    body = response.json()
    assert body["ratings"] == []


def test_create_entry_without_score_shows_null_latest_score_in_history(client):
    post_entry(client, entry_type="bag", roaster="Stumptown", bean_name="Hair Bender")
    response = client.get("/api/entries")
    assert response.json()[0]["latest_score"] is None


def test_rate_a_previously_unrated_entry(client):
    create_response = post_entry(client, entry_type="bag", roaster="Stumptown", bean_name="Hair Bender")
    entry_id = create_response.json()["id"]

    response = client.post(f"/api/entries/{entry_id}/ratings", json={"score": 8})
    assert response.status_code == 201
    body = response.json()
    assert len(body["ratings"]) == 1
    assert body["ratings"][0]["score"] == 8


def test_autocomplete_returns_prefix_matches(client):
    post_entry(client, entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8)
    response = client.get("/api/bean-profiles/autocomplete", params={"q": "Stump"})
    assert response.status_code == 200
    assert response.json()[0]["roaster"] == "Stumptown"


def test_autocomplete_empty_query_returns_empty_list(client):
    response = client.get("/api/bean-profiles/autocomplete", params={"q": ""})
    assert response.status_code == 200
    assert response.json() == []


def test_list_entries_endpoint_newest_first(client):
    post_entry(client, entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8)
    post_entry(client, entry_type="bag", roaster="Intelligentsia", bean_name="Black Cat", score=7)
    response = client.get("/api/entries")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["roaster"] == "Intelligentsia"


def test_list_entries_search_query(client):
    post_entry(client, entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8)
    post_entry(client, entry_type="bag", roaster="Intelligentsia", bean_name="Black Cat", score=7)
    response = client.get("/api/entries", params={"q": "Intelli"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["roaster"] == "Intelligentsia"


def test_add_rating_endpoint_appends_rating(client):
    create_response = post_entry(
        client, entry_type="cafe_cup", roaster="Local Cafe", bean_name="House Blend", score=6
    )
    entry_id = create_response.json()["id"]

    response = client.post(f"/api/entries/{entry_id}/ratings", json={"score": 9})
    assert response.status_code == 201
    body = response.json()
    assert len(body["ratings"]) == 2
    assert body["ratings"][1]["score"] == 9


def test_add_rating_for_missing_entry_returns_404(client):
    response = client.post("/api/entries/999/ratings", json={"score": 9})
    assert response.status_code == 404


def test_create_entry_with_photo_creates_entry_photo_row(client, conn):
    response = client.post(
        "/api/entries",
        data={
            "data": json.dumps(
                {"entry_type": "bag", "roaster": "Stumptown", "bean_name": "Hair Bender", "score": 8}
            )
        },
        files=[("photos", ("bag.jpg", b"\xff\xd8\xff" + b"fake-image-bytes", "image/jpeg"))],
    )
    assert response.status_code == 201
    entry_id = response.json()["id"]
    count = conn.execute(
        "SELECT COUNT(*) AS n FROM entry_photos WHERE entry_id = ?", (entry_id,)
    ).fetchone()["n"]
    assert count == 1


def test_create_entry_with_photo_resolves_to_failed_without_api_key(client):
    # No ANTHROPIC_API_KEY (guaranteed by the autouse fixture). The response
    # itself must show 'pending' immediately (the whole point of running
    # extraction in the background: instant save, no waiting screen).
    response = client.post(
        "/api/entries",
        data={
            "data": json.dumps(
                {"entry_type": "bag", "roaster": "Stumptown", "bean_name": "Hair Bender", "score": 8}
            )
        },
        files=[("photos", ("bag.jpg", b"\xff\xd8\xff" + b"fake-image-bytes", "image/jpeg"))],
    )
    assert response.status_code == 201
    entry_id = response.json()["id"]
    assert response.json()["extraction_status"] == "pending"

    # TestClient runs the background task synchronously after building the
    # response, so by now it's already been attempted and resolved. This
    # proves the app never crashes and never leaves an entry stuck 'pending'
    # when the key is missing or bad.
    follow_up = client.get(f"/api/entries/{entry_id}")
    assert follow_up.json()["extraction_status"] == "failed"


def test_create_entry_without_photo_is_not_applicable(client):
    response = post_entry(client, entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8)
    assert response.json()["extraction_status"] == "not_applicable"


# --- 0.5.0: photo-first identity ---


def test_create_bag_entry_with_photo_and_no_identity_succeeds(client):
    response = client.post(
        "/api/entries",
        data={"data": json.dumps({"entry_type": "bag", "score": 7})},
        files=[("photos", ("bag.jpg", b"\xff\xd8\xff" + b"fake-image-bytes", "image/jpeg"))],
    )
    assert response.status_code == 201
    body = response.json()
    assert body["bean_profile"]["is_provisional"] is True
    assert body["bean_profile"]["roaster"] == "Unidentified"


def test_create_bag_entry_with_no_identity_and_no_photo_rejected(client):
    response = client.post("/api/entries", data={"data": json.dumps({"entry_type": "bag", "score": 7})})
    assert response.status_code == 422


def test_create_cafe_cup_with_photo_and_no_identity_rejected(client):
    # Cafe cups have nothing printed to photograph for identity, unlike
    # bags - typed identity is always required for them.
    response = client.post(
        "/api/entries",
        data={"data": json.dumps({"entry_type": "cafe_cup", "score": 7})},
        files=[("photos", ("menu.jpg", b"\xff\xd8\xff" + b"fake-image-bytes", "image/jpeg"))],
    )
    assert response.status_code == 422


class _FakeIdentityExtractor(BeanExtractor):
    def extract(self, image_bytes_list):
        return {"roaster": "Monogram", "bean_name": "Mango"}


def test_create_bag_entry_with_photo_no_identity_extraction_resolves_it(client):
    response = client.post(
        "/api/entries",
        data={"data": json.dumps({"entry_type": "bag", "score": 7})},
        files=[("photos", ("bag.jpg", b"\xff\xd8\xff" + b"fake-image-bytes", "image/jpeg"))],
    )
    entry_id = response.json()["id"]
    assert response.json()["bean_profile"]["is_provisional"] is True

    # TestClient runs the background extraction task synchronously, but
    # against the real ClaudeExtractor (no API key here) - re-run it here
    # with a fake extractor to verify the resolution path itself.
    run_extraction(entry_id, [], extractor=_FakeIdentityExtractor())

    follow_up = client.get(f"/api/entries/{entry_id}")
    body = follow_up.json()
    assert body["bean_profile"]["roaster"] == "Monogram"
    assert body["bean_profile"]["is_provisional"] is False


# --- 0.7.0: fixing wrong data ---


def test_patch_entry_updates_field(client):
    entry_id = post_entry(client, entry_type="bag", roaster="X", bean_name="Y", score=7).json()["id"]
    response = client.patch(f"/api/entries/{entry_id}", json={"roast_level": "Medium"})
    assert response.status_code == 200
    assert response.json()["roast_level"] == "Medium"


def test_patch_entry_can_clear_field_to_null(client):
    entry_id = post_entry(
        client, entry_type="bag", roaster="X", bean_name="Y", score=7, batch_number="L-1"
    ).json()["id"]
    response = client.patch(f"/api/entries/{entry_id}", json={"batch_number": None})
    assert response.status_code == 200
    assert response.json()["batch_number"] is None


def test_patch_entry_missing_returns_404(client):
    response = client.patch("/api/entries/999", json={"roast_level": "Medium"})
    assert response.status_code == 404


def test_delete_entry_removes_it(client):
    entry_id = post_entry(client, entry_type="bag", roaster="X", bean_name="Y", score=7).json()["id"]
    response = client.delete(f"/api/entries/{entry_id}")
    assert response.status_code == 204
    assert client.get(f"/api/entries/{entry_id}").status_code == 404


def test_delete_entry_removes_photo_file_from_disk(client, tmp_path):
    response = client.post(
        "/api/entries",
        data={"data": json.dumps({"entry_type": "bag", "roaster": "X", "bean_name": "Y", "score": 7})},
        files=[("photos", ("bag.jpg", b"\xff\xd8\xff" + b"fake-image-bytes", "image/jpeg"))],
    )
    entry_id = response.json()["id"]
    photo_id = response.json()["photos"][0]["id"]
    assert client.get(f"/api/photos/{photo_id}").status_code == 200

    client.delete(f"/api/entries/{entry_id}")

    assert client.get(f"/api/photos/{photo_id}").status_code == 404


def test_delete_entry_missing_returns_404(client):
    assert client.delete("/api/entries/999").status_code == 404


def test_reextract_entry_resets_to_pending(client):
    response = client.post(
        "/api/entries",
        data={"data": json.dumps({"entry_type": "bag", "roaster": "X", "bean_name": "Y", "score": 7})},
        files=[("photos", ("bag.jpg", b"\xff\xd8\xff" + b"fake-image-bytes", "image/jpeg"))],
    )
    entry_id = response.json()["id"]
    assert client.get(f"/api/entries/{entry_id}").json()["extraction_status"] == "failed"

    reextract_response = client.post(f"/api/entries/{entry_id}/reextract")
    assert reextract_response.status_code == 200
    # TestClient runs the background task synchronously again, so by the
    # time this returns it's already flipped back to failed (no real key) -
    # the important thing is it went through 'pending' and didn't error.
    assert reextract_response.json()["extraction_status"] in ("pending", "failed")


def test_reextract_entry_without_photos_rejected(client):
    entry_id = post_entry(client, entry_type="bag", roaster="X", bean_name="Y", score=7).json()["id"]
    response = client.post(f"/api/entries/{entry_id}/reextract")
    assert response.status_code == 422


def test_reextract_missing_entry_404(client):
    assert client.post("/api/entries/999/reextract").status_code == 404


def test_patch_rating_updates_score(client):
    entry_response = post_entry(client, entry_type="bag", roaster="X", bean_name="Y", score=6)
    entry_id = entry_response.json()["id"]
    rating_id = entry_response.json()["ratings"][0]["id"]

    response = client.patch(f"/api/entries/{entry_id}/ratings/{rating_id}", json={"score": 9})
    assert response.status_code == 200
    assert response.json()["ratings"][0]["score"] == 9


def test_patch_rating_missing_returns_404(client):
    entry_id = post_entry(client, entry_type="bag", roaster="X", bean_name="Y", score=6).json()["id"]
    response = client.patch(f"/api/entries/{entry_id}/ratings/999", json={"score": 9})
    assert response.status_code == 404


def test_delete_rating_endpoint_removes_it(client):
    entry_response = post_entry(client, entry_type="bag", roaster="X", bean_name="Y", score=6)
    entry_id = entry_response.json()["id"]
    second_rating_id = client.post(f"/api/entries/{entry_id}/ratings", json={"score": 8}).json()["ratings"][1]["id"]

    response = client.delete(f"/api/entries/{entry_id}/ratings/{second_rating_id}")
    assert response.status_code == 200
    assert len(response.json()["ratings"]) == 1


def test_delete_rating_endpoint_missing_returns_404(client):
    entry_id = post_entry(client, entry_type="bag", roaster="X", bean_name="Y", score=6).json()["id"]
    assert client.delete(f"/api/entries/{entry_id}/ratings/999").status_code == 404


def test_get_photo_serves_file(client):
    response = client.post(
        "/api/entries",
        data={"data": json.dumps({"entry_type": "bag", "roaster": "X", "bean_name": "Y", "score": 7})},
        files=[("photos", ("bag.jpg", b"\xff\xd8\xff" + b"fake-image-bytes", "image/jpeg"))],
    )
    photo_id = response.json()["photos"][0]["id"]
    photo_response = client.get(f"/api/photos/{photo_id}")
    assert photo_response.status_code == 200
    assert photo_response.content == b"\xff\xd8\xff" + b"fake-image-bytes"


def test_get_photo_missing_returns_404(client):
    assert client.get("/api/photos/999").status_code == 404


def test_entry_detail_includes_related_photos(client):
    first = client.post(
        "/api/entries",
        data={"data": json.dumps({"entry_type": "bag", "roaster": "Monogram", "bean_name": "Mango", "score": 7})},
        files=[("photos", ("bag1.jpg", b"\xff\xd8\xff" + b"fake-image-bytes-1", "image/jpeg"))],
    ).json()
    second = client.post(
        "/api/entries",
        data={"data": json.dumps({"entry_type": "bag", "roaster": "Monogram", "bean_name": "Mango", "score": 8})},
        files=[("photos", ("bag2.jpg", b"\xff\xd8\xff" + b"fake-image-bytes-2", "image/jpeg"))],
    ).json()

    follow_up = client.get(f"/api/entries/{second['id']}")
    body = follow_up.json()
    assert len(body["photos"]) == 1
    assert len(body["related_photos"]) == 1
    assert body["related_photos"][0]["entry_id"] == first["id"]


# --- security hardening: upload validation + AI-endpoint cooldowns ---


def test_create_entry_rejects_non_image_upload(client):
    response = client.post(
        "/api/entries",
        data={"data": json.dumps({"entry_type": "bag", "roaster": "X", "bean_name": "Y", "score": 7})},
        files=[("photos", ("bag.jpg", b"this is not an image, just text", "image/jpeg"))],
    )
    assert response.status_code == 422


def test_create_entry_rejects_oversized_photo(client):
    from backend.routers.entries import MAX_PHOTO_BYTES

    oversized = b"\xff\xd8\xff" + b"0" * MAX_PHOTO_BYTES
    response = client.post(
        "/api/entries",
        data={"data": json.dumps({"entry_type": "bag", "roaster": "X", "bean_name": "Y", "score": 7})},
        files=[("photos", ("bag.jpg", oversized, "image/jpeg"))],
    )
    assert response.status_code == 422


def test_create_entry_rejects_too_many_photos(client):
    from backend.routers.entries import MAX_PHOTOS_PER_ENTRY

    photo = ("photos", ("bag.jpg", b"\xff\xd8\xff" + b"fake", "image/jpeg"))
    response = client.post(
        "/api/entries",
        data={"data": json.dumps({"entry_type": "bag", "roaster": "X", "bean_name": "Y", "score": 7})},
        files=[photo] * (MAX_PHOTOS_PER_ENTRY + 1),
    )
    assert response.status_code == 422


def test_create_entry_rejecting_a_photo_leaves_no_entry_behind(client, conn):
    client.post(
        "/api/entries",
        data={"data": json.dumps({"entry_type": "bag", "roaster": "X", "bean_name": "Y", "score": 7})},
        files=[("photos", ("bag.jpg", b"not an image", "image/jpeg"))],
    )
    count = conn.execute("SELECT COUNT(*) AS n FROM entries").fetchone()["n"]
    assert count == 0


def test_reextract_second_immediate_call_is_cooled_down(client):
    response = client.post(
        "/api/entries",
        data={"data": json.dumps({"entry_type": "bag", "roaster": "X", "bean_name": "Y", "score": 7})},
        files=[("photos", ("bag.jpg", b"\xff\xd8\xff" + b"fake-image-bytes", "image/jpeg"))],
    )
    entry_id = response.json()["id"]

    first = client.post(f"/api/entries/{entry_id}/reextract")
    assert first.status_code == 200

    second = client.post(f"/api/entries/{entry_id}/reextract")
    assert second.status_code == 429


# --- domain-event logging (supports 1.0.1's real-world-use checklist) ---


def test_create_entry_logs_typed_identity(client):
    post_entry(client, entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8)
    log_contents = logging_config.LOG_PATH.read_text()
    assert "Entry created: id=1 type=bag identity=typed bean='Stumptown — Hair Bender' score=8.0" in log_contents


def test_create_entry_logs_photo_derived_identity(client):
    client.post(
        "/api/entries",
        data={"data": json.dumps({"entry_type": "bag", "score": 7})},
        files=[("photos", ("bag.jpg", b"\xff\xd8\xff" + b"fake-image-bytes", "image/jpeg"))],
    )
    log_contents = logging_config.LOG_PATH.read_text()
    assert "identity=photo (identity pending extraction)" in log_contents
    assert "has_photos=True" in log_contents


def test_create_entry_logs_cafe_cup(client):
    post_entry(client, entry_type="cafe_cup", roaster="Blue Bottle", bean_name="Bella Donovan", score=7)
    log_contents = logging_config.LOG_PATH.read_text()
    assert "type=cafe_cup" in log_contents


def test_create_rating_logs_score_and_bean_for_repeat_tracking(client):
    # The initial score is logged by "Entry created"; a later rating on the
    # same entry - the "Rate a Previous Bean" flow - logs "Rating added"
    # separately, so a repeat shows up as two log lines for the same bean.
    entry_id = post_entry(client, entry_type="bag", roaster="X", bean_name="Y", score=6).json()["id"]
    client.post(f"/api/entries/{entry_id}/ratings", json={"score": 8})

    log_contents = logging_config.LOG_PATH.read_text()
    assert f"Entry created: id={entry_id}" in log_contents and "score=6.0" in log_contents
    assert f"Rating added: entry_id={entry_id} score=8.0 bean='X — Y'" in log_contents
