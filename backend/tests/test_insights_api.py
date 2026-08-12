import json


def post_entry(client, **fields):
    return client.post("/api/entries", data={"data": json.dumps(fields)})


def test_insights_endpoint_empty_database(client):
    response = client.get("/api/insights")
    assert response.status_code == 200
    body = response.json()
    assert body["monthly_trend"] == []
    assert body["by_process"]["all_time"]["items"] == []
    assert body["by_process"]["all_time"]["significance"]["comparable"] is False
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
    response = client.get("/api/insights")
    assert response.status_code == 200
    body = response.json()
    process_items = body["by_process"]["all_time"]["items"]
    assert len(process_items) == 1
    assert process_items[0]["process"] == "Washed"
    assert process_items[0]["avg_score"] == 8
    origin_items = body["by_origin_country"]["all_time"]["items"]
    assert origin_items[0]["origin_country"] == "Colombia"
    note_names = {n["note"] for n in body["by_tasting_note"]["all_time"]["items"]}
    assert note_names == {"Chocolate", "Caramel"}
    assert len(body["monthly_trend"]) == 1
    assert body["monthly_trend"][0]["count"] == 1


# --- 1.2.0: brew-method-sliced insights ---


def test_insights_endpoint_includes_brew_style_breakdown(client):
    post_entry(client, entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8, brew_style="Espresso")
    response = client.get("/api/insights")
    items = response.json()["by_brew_style"]["all_time"]["items"]
    assert len(items) == 1
    assert items[0]["brew_style"] == "Espresso"
    assert items[0]["avg_score"] == 8


def test_insights_endpoint_brew_style_filter_slices_breakdowns(client):
    post_entry(client, entry_type="bag", roaster="A", bean_name="A", score=8, process="Washed", brew_style="Espresso")
    post_entry(client, entry_type="bag", roaster="B", bean_name="B", score=4, process="Washed", brew_style="Pour Over")

    response = client.get("/api/insights", params={"brew_style": "Espresso"})
    assert response.status_code == 200
    items = response.json()["by_process"]["all_time"]["items"]
    assert len(items) == 1
    assert items[0]["process"] == "Washed"
    assert items[0]["avg_score"] == 8


def test_insights_endpoint_rejects_unknown_brew_style(client):
    response = client.get("/api/insights", params={"brew_style": "not-a-real-style"})
    assert response.status_code == 422


# --- 1.2.0 (extended): statistically rigorous rankings ---


def test_insights_endpoint_includes_adjusted_score_and_significance(client):
    post_entry(client, entry_type="bag", roaster="A", bean_name="A", score=8, process="Washed")
    response = client.get("/api/insights")
    items = response.json()["by_process"]["all_time"]["items"]
    assert "adjusted_score" in items[0]
    significance = response.json()["by_process"]["all_time"]["significance"]
    assert significance["comparable"] is False  # only one process logged so far
    assert significance["message"]


def test_insights_endpoint_reports_significant_difference_between_top_two(client):
    for _ in range(5):
        post_entry(client, entry_type="bag", roaster="A", bean_name="A", score=9, process="Washed")
    for _ in range(5):
        post_entry(client, entry_type="bag", roaster="B", bean_name="B", score=4, process="Honey")
    response = client.get("/api/insights")
    significance = response.json()["by_process"]["all_time"]["significance"]
    assert significance["comparable"] is True
    assert significance["significant"] is True
    assert significance["p_value"] < 0.05


# --- AI narrative insights (0.9.0) ---


def test_get_narrative_returns_null_when_none_generated(client):
    response = client.get("/api/insights/narrative")
    assert response.status_code == 200
    assert response.json() is None


def test_post_narrative_without_api_key_returns_502(client):
    # No ANTHROPIC_API_KEY (guaranteed by the autouse fixture) - the real
    # ClaudeInsightGenerator fails to construct, and that must surface as
    # a clean error response, not a crash.
    post_entry(client, entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8)
    response = client.post("/api/insights/narrative")
    assert response.status_code == 502
    assert client.get("/api/insights/narrative").json() is None


def test_post_narrative_error_does_not_leak_exception_text(client):
    # Security hardening: the response must never echo back raw exception
    # text (which could reveal internal details) - just a generic message.
    response = client.post("/api/insights/narrative")
    assert "ANTHROPIC_API_KEY" not in response.text
    assert response.json()["detail"] == "Insight generation failed. Check the server logs."


def test_post_narrative_second_immediate_call_is_cooled_down(client):
    first = client.post("/api/insights/narrative")
    assert first.status_code == 502  # no API key, but the attempt still counts

    second = client.post("/api/insights/narrative")
    assert second.status_code == 429
