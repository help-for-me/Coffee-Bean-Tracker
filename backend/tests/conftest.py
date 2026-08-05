import pytest
from fastapi.testclient import TestClient

from backend import database, logging_config, photos, rate_limit
from backend.main import app


@pytest.fixture(autouse=True)
def _no_real_api_key(monkeypatch):
    # Guarantees the test suite never makes a real network call to Anthropic,
    # regardless of what's set in the environment it happens to run in.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    # The cooldown tracker is a module-level dict so it survives across
    # requests within a real run (that's the point) - but that also means
    # it survives across tests in the same pytest process. Every test gets
    # a fresh database via tmp_path, so entry IDs restart from 1 each time;
    # without this, an early test's cooldown on "entry 1" would wrongly
    # block a later, unrelated test's request to its own "entry 1".
    rate_limit._last_call.clear()


@pytest.fixture()
def conn(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init_db()
    connection = database.get_connection()
    yield connection
    connection.close()


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(photos, "PHOTOS_PATH", tmp_path / "photos")
    monkeypatch.setattr(logging_config, "LOG_PATH", tmp_path / "logs" / "app.log")
    with TestClient(app) as test_client:
        yield test_client
