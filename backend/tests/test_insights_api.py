import json


def post_entry(client, **fields):
    return client.post("/entries", data={"data": json.dumps(fields)})


def test_insights_endpoint_empty_database(client):
    response = client.get("/insights")
    assert response.status_code == 200
    body = response.json()
    assert body["monthly_trend"] == []
    assert body["by_process"] == {"all_time": [], "recent": []}
    assert body["most_repurchased"] == {"all_time": [], "recent": []}
    assert body["recent_window"] == {"applicable": False, "cutoff_date": None}


def test_insights_endpoint_reflects_real_entries(client):
    post_entry(
        client,
        entry_type="bag",
        roaster="Stumptown",
        bean_name="Hair Bender",
        score=8,
        process="Washed",
        origin_country="Colombia",
        printed_tasting_notes="Chocolate, Caramel",
    )
    response = client.get("/insights")
    assert response.status_code == 200
    body = response.json()
    assert body["by_process"]["all_time"] == [{"process": "Washed", "avg_score": 8, "count": 1}]
    assert body["by_origin_country"]["all_time"] == [{"origin_country": "Colombia", "avg_score": 8, "count": 1}]
    assert {n["note"] for n in body["by_tasting_note"]["all_time"]} == {"Chocolate", "Caramel"}
    assert len(body["monthly_trend"]) == 1
    assert body["monthly_trend"][0]["count"] == 1
