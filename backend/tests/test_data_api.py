import json


def post_entry(client, **fields):
    return client.post("/api/entries", data={"data": json.dumps(fields)})


def test_export_endpoint_returns_json_with_data(client):
    post_entry(client, entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8)
    response = client.get("/api/data/export")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "attachment" in response.headers["content-disposition"]
    body = response.json()
    assert body["format_version"] == 1
    assert body["bean_profiles"][0]["roaster"] == "Stumptown"


def test_import_endpoint_requires_confirm(client):
    response = client.post("/api/data/import", json={"confirm": False, "data": {"format_version": 1}})
    assert response.status_code == 400


def test_import_endpoint_rejects_invalid_data(client):
    response = client.post(
        "/api/data/import",
        json={"confirm": True, "data": {"format_version": 1, "bean_profiles": [{"evil": "x"}]}},
    )
    assert response.status_code == 422


def test_import_endpoint_round_trip_via_export(client):
    post_entry(client, entry_type="bag", roaster="Monogram", bean_name="Mango", score=9)
    exported = client.get("/api/data/export").json()

    response = client.post("/api/data/import", json={"confirm": True, "data": exported})
    assert response.status_code == 200
    assert response.json() == {"entries": 1, "ratings": 1, "photos": 0}

    entries = client.get("/api/entries").json()
    assert len(entries) == 1
    assert entries[0]["roaster"] == "Monogram"


def test_import_endpoint_replaces_rather_than_merges(client):
    post_entry(client, entry_type="bag", roaster="Old Roaster", bean_name="Old Bean", score=5)
    payload = {
        "format_version": 1,
        "bean_profiles": [{"id": 1, "roaster": "New Roaster", "bean_name": "New Bean", "is_provisional": 0}],
        "entries": [{
            "id": 1, "bean_profile_id": 1, "entry_type": "bag", "extraction_status": "not_applicable",
            "extraction_source": "manual", "currency": "CAD", "co_ferment_status": "unknown",
        }],
        "ratings": [{"id": 1, "entry_id": 1, "score": 7}],
    }

    client.post("/api/data/import", json={"confirm": True, "data": payload})

    entries = client.get("/api/entries").json()
    assert len(entries) == 1
    assert entries[0]["roaster"] == "New Roaster"
