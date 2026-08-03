import pytest
from fastapi.testclient import TestClient

from backend import database, photos
from backend.main import app


@pytest.fixture(autouse=True)
def _no_real_api_key(monkeypatch):
    # Guarantees the test suite never makes a real network call to Anthropic,
    # regardless of what's set in the environment it happens to run in.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


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
    with TestClient(app) as test_client:
        yield test_client
