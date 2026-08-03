import json


def post_entry(client, **fields):
    return client.post("/entries", data={"data": json.dumps(fields)})


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


def test_autocomplete_returns_prefix_matches(client):
    post_entry(client, entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8)
    response = client.get("/bean-profiles/autocomplete", params={"q": "Stump"})
    assert response.status_code == 200
    assert response.json()[0]["roaster"] == "Stumptown"


def test_autocomplete_empty_query_returns_empty_list(client):
    response = client.get("/bean-profiles/autocomplete", params={"q": ""})
    assert response.status_code == 200
    assert response.json() == []


def test_list_entries_endpoint_newest_first(client):
    post_entry(client, entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8)
    post_entry(client, entry_type="bag", roaster="Intelligentsia", bean_name="Black Cat", score=7)
    response = client.get("/entries")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["roaster"] == "Intelligentsia"


def test_list_entries_search_query(client):
    post_entry(client, entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8)
    post_entry(client, entry_type="bag", roaster="Intelligentsia", bean_name="Black Cat", score=7)
    response = client.get("/entries", params={"q": "Intelli"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["roaster"] == "Intelligentsia"


def test_add_rating_endpoint_appends_rating(client):
    create_response = post_entry(
        client, entry_type="cafe_cup", roaster="Local Cafe", bean_name="House Blend", score=6
    )
    entry_id = create_response.json()["id"]

    response = client.post(f"/entries/{entry_id}/ratings", json={"score": 9})
    assert response.status_code == 201
    body = response.json()
    assert len(body["ratings"]) == 2
    assert body["ratings"][1]["score"] == 9


def test_add_rating_for_missing_entry_returns_404(client):
    response = client.post("/entries/999/ratings", json={"score": 9})
    assert response.status_code == 404


def test_create_entry_with_photo_creates_entry_photo_row(client, conn):
    response = client.post(
        "/entries",
        data={
            "data": json.dumps(
                {"entry_type": "bag", "roaster": "Stumptown", "bean_name": "Hair Bender", "score": 8}
            )
        },
        files=[("photos", ("bag.jpg", b"fake-image-bytes", "image/jpeg"))],
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
        "/entries",
        data={
            "data": json.dumps(
                {"entry_type": "bag", "roaster": "Stumptown", "bean_name": "Hair Bender", "score": 8}
            )
        },
        files=[("photos", ("bag.jpg", b"fake-image-bytes", "image/jpeg"))],
    )
    assert response.status_code == 201
    entry_id = response.json()["id"]
    assert response.json()["extraction_status"] == "pending"

    # TestClient runs the background task synchronously after building the
    # response, so by now it's already been attempted and resolved. This
    # proves the app never crashes and never leaves an entry stuck 'pending'
    # when the key is missing or bad.
    follow_up = client.get(f"/entries/{entry_id}")
    assert follow_up.json()["extraction_status"] == "failed"


def test_create_entry_without_photo_is_not_applicable(client):
    response = post_entry(client, entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8)
    assert response.json()["extraction_status"] == "not_applicable"
