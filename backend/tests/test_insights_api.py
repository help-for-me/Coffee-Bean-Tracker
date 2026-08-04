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


# --- AI narrative insights (0.9.0) ---


def test_get_narrative_returns_null_when_none_generated(client):
    response = client.get("/insights/narrative")
    assert response.status_code == 200
    assert response.json() is None


def test_post_narrative_without_api_key_returns_502(client):
    # No ANTHROPIC_API_KEY (guaranteed by the autouse fixture) - the real
    # ClaudeInsightGenerator fails to construct, and that must surface as
    # a clean error response, not a crash.
    post_entry(client, entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8)
    response = client.post("/insights/narrative")
    assert response.status_code == 502
    assert client.get("/insights/narrative").json() is None
