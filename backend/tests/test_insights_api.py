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
        client, entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8, process="Washed"
    )
    response = client.get("/insights")
    assert response.status_code == 200
    body = response.json()
    assert body["by_process"]["all_time"] == [{"process": "Washed", "avg_score": 8, "count": 1}]
    assert len(body["monthly_trend"]) == 1
    assert body["monthly_trend"][0]["count"] == 1
