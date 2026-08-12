def test_get_settings_returns_env_defaults_when_unset(client):
    response = client.get("/api/settings")
    assert response.status_code == 200
    body = response.json()
    assert body["recent_window_months"] == 4
    assert body["recent_window_count"] == 10
    assert body["extraction_custom_instructions"] == ""
    assert body["narrative_custom_instructions"] == ""


def test_get_settings_reflects_env_var_override(client, monkeypatch):
    monkeypatch.setenv("RECENT_WINDOW_MONTHS", "6")
    response = client.get("/api/settings")
    assert response.json()["recent_window_months"] == 6


def test_put_settings_persists_and_overrides_env_var(client, monkeypatch):
    monkeypatch.setenv("RECENT_WINDOW_MONTHS", "6")
    response = client.put("/api/settings", json={"recent_window_months": 2})
    assert response.status_code == 200
    assert response.json()["recent_window_months"] == 2

    # Persisted, not just echoed back - a fresh GET still sees it.
    assert client.get("/api/settings").json()["recent_window_months"] == 2


def test_put_settings_only_updates_provided_fields(client):
    client.put("/api/settings", json={"recent_window_months": 2})
    response = client.put("/api/settings", json={"recent_window_count": 20})
    body = response.json()
    assert body["recent_window_count"] == 20
    assert body["recent_window_months"] == 2  # untouched by the second call


def test_put_settings_stores_custom_instructions(client):
    response = client.put(
        "/api/settings",
        json={
            "extraction_custom_instructions": "Always exclude bilingual packaging text.",
            "narrative_custom_instructions": "Keep it to one sentence.",
        },
    )
    body = response.json()
    assert body["extraction_custom_instructions"] == "Always exclude bilingual packaging text."
    assert body["narrative_custom_instructions"] == "Keep it to one sentence."


def test_put_settings_rejects_non_positive_window(client):
    response = client.put("/api/settings", json={"recent_window_months": 0})
    assert response.status_code == 422


def test_put_settings_rejects_overlong_instructions(client):
    response = client.put("/api/settings", json={"extraction_custom_instructions": "x" * 2001})
    assert response.status_code == 422
