import json

from backend.routers import exports as exports_router


def post_entry(client, **fields):
    return client.post("/api/entries", data={"data": json.dumps(fields)})


# --- CSV: always available, no config, nothing logged ---


def test_export_csv_returns_csv_with_data(client):
    post_entry(client, entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8)
    response = client.get("/api/exports/csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "Stumptown" in response.text


def test_export_csv_empty_database_still_returns_header(client):
    response = client.get("/api/exports/csv")
    assert response.status_code == 200
    assert "entry_id" in response.text


# --- XLSX: always downloadable; local save is opt-in via env var ---


def test_export_xlsx_returns_a_file(client):
    post_entry(client, entry_type="bag", roaster="Stumptown", bean_name="Hair Bender", score=8)
    response = client.post("/api/exports/xlsx")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert len(response.content) > 0


def test_export_xlsx_does_not_write_locally_when_disabled(client, tmp_path, monkeypatch):
    xlsx_path = tmp_path / "backup.xlsx"
    monkeypatch.setattr(exports_router, "LOCAL_XLSX_PATH", xlsx_path)
    monkeypatch.delenv("LOCAL_XLSX_ENABLED", raising=False)

    post_entry(client, entry_type="bag", roaster="X", bean_name="Y", score=7)
    client.post("/api/exports/xlsx")

    assert not xlsx_path.exists()


def test_export_xlsx_writes_locally_when_enabled(client, tmp_path, monkeypatch):
    xlsx_path = tmp_path / "backup.xlsx"
    monkeypatch.setattr(exports_router, "LOCAL_XLSX_PATH", xlsx_path)
    monkeypatch.setenv("LOCAL_XLSX_ENABLED", "true")

    post_entry(client, entry_type="bag", roaster="X", bean_name="Y", score=7)
    response = client.post("/api/exports/xlsx")

    assert response.status_code == 200
    assert xlsx_path.exists()
    assert xlsx_path.read_bytes() == response.content


# --- status endpoint ---


def test_export_status_reports_disabled_sinks_by_default(client):
    status = client.get("/api/exports/status").json()
    assert status["local_xlsx"]["enabled"] is False
    assert status["local_xlsx"]["last"] is None
    assert status["github"]["enabled"] is False
    assert status["github"]["last"] is None


def test_export_status_reflects_successful_local_xlsx_backup(client, tmp_path, monkeypatch):
    monkeypatch.setattr(exports_router, "LOCAL_XLSX_PATH", tmp_path / "backup.xlsx")
    monkeypatch.setenv("LOCAL_XLSX_ENABLED", "true")

    client.post("/api/exports/xlsx")
    status = client.get("/api/exports/status").json()

    assert status["local_xlsx"]["enabled"] is True
    assert status["local_xlsx"]["last"]["status"] == "success"


# --- GitHub: gated behind config ---


def test_export_github_rejected_when_not_enabled(client, monkeypatch):
    monkeypatch.delenv("GITHUB_BACKUP_ENABLED", raising=False)
    response = client.post("/api/exports/github")
    assert response.status_code == 400


def test_export_github_rejected_when_enabled_but_not_configured(client, monkeypatch):
    monkeypatch.setenv("GITHUB_BACKUP_ENABLED", "true")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPO", raising=False)
    response = client.post("/api/exports/github")
    assert response.status_code == 400


def test_export_github_logs_failure_when_not_configured(client, conn, monkeypatch):
    monkeypatch.setenv("GITHUB_BACKUP_ENABLED", "true")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    client.post("/api/exports/github")
    row = conn.execute("SELECT status FROM export_log WHERE sink = 'github'").fetchone()
    assert row["status"] == "failed"
