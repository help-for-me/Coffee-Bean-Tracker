def test_create_entry_endpoint(client):
    response = client.post(
        "/entries",
        json={
            "entry_type": "bag",
            "roaster": "Stumptown",
            "bean_name": "Hair Bender",
            "score": 8.5,
            "narrative_notes": "Chocolatey, bright finish",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["bean_profile"]["roaster"] == "Stumptown"
    assert len(body["ratings"]) == 1
    assert body["ratings"][0]["score"] == 8.5


def test_create_entry_rejects_out_of_range_score(client):
    response = client.post(
        "/entries",
        json={"entry_type": "bag", "roaster": "X", "bean_name": "Y", "score": 15},
    )
    assert response.status_code == 422


def test_autocomplete_returns_prefix_matches(client):
    client.post(
        "/entries",
        json={"entry_type": "bag", "roaster": "Stumptown", "bean_name": "Hair Bender", "score": 8},
    )
    response = client.get("/bean-profiles/autocomplete", params={"q": "Stump"})
    assert response.status_code == 200
    assert response.json()[0]["roaster"] == "Stumptown"


def test_autocomplete_empty_query_returns_empty_list(client):
    response = client.get("/bean-profiles/autocomplete", params={"q": ""})
    assert response.status_code == 200
    assert response.json() == []
