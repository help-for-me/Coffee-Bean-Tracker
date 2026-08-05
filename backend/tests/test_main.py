import asyncio
import json
from types import SimpleNamespace

from backend import logging_config
from backend.main import log_slow_requests, log_unhandled_exception, resolve_spa_path


def _make_dist(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>root</html>")
    (dist / "app.js").write_text("console.log(1)")
    return dist


def test_resolve_spa_path_serves_an_existing_file(tmp_path):
    dist = _make_dist(tmp_path)
    assert resolve_spa_path("app.js", dist) == (dist / "app.js").resolve()


def test_resolve_spa_path_missing_file_returns_none(tmp_path):
    dist = _make_dist(tmp_path)
    assert resolve_spa_path("nope.js", dist) is None


def test_resolve_spa_path_empty_returns_none(tmp_path):
    dist = _make_dist(tmp_path)
    assert resolve_spa_path("", dist) is None


def test_resolve_spa_path_blocks_traversal_outside_dist(tmp_path):
    dist = _make_dist(tmp_path)
    secret = tmp_path / "secret.txt"
    secret.write_text("SECRET_CONTENT")
    assert resolve_spa_path("../secret.txt", dist) is None


def test_resolve_spa_path_blocks_encoded_style_traversal(tmp_path):
    # FastAPI's {full_path:path} converter hands us the URL-decoded value,
    # so a request for "/%2e%2e/%2e%2e/etc/passwd" arrives here as the
    # literal string "../../etc/passwd" - same case as the plain '..' test,
    # covered explicitly since this is exactly how the real bug was found.
    dist = _make_dist(tmp_path)
    assert resolve_spa_path("../../../../etc/passwd", dist) is None


# --- logging: crashes and slow requests must reach the exportable file ---


def _fake_request(method="GET", path="/broken"):
    return SimpleNamespace(method=method, url=SimpleNamespace(path=path))


def test_log_unhandled_exception_logs_full_traceback(client):
    # `client` already ran setup_logging() with LOG_PATH pointed at tmp_path.
    # logger.exception() reads the *currently handled* exception (like
    # FastAPI itself invokes this handler from within its own except block),
    # so the call has to happen inside a real except block too, not just be
    # handed an exception object - otherwise there's no traceback to log.
    try:
        raise RuntimeError("boom")
    except RuntimeError as exc:
        response = asyncio.run(log_unhandled_exception(_fake_request(path="/broken"), exc))

    assert response.status_code == 500
    log_contents = logging_config.LOG_PATH.read_text()
    assert "Unhandled error on GET /broken" in log_contents
    assert "RuntimeError" in log_contents
    assert "boom" in log_contents


def test_log_unhandled_exception_does_not_leak_exception_text_to_client(client):
    try:
        raise RuntimeError("a sensitive internal detail")
    except RuntimeError as exc:
        response = asyncio.run(log_unhandled_exception(_fake_request(), exc))

    body = json.loads(response.body)
    assert "a sensitive internal detail" not in body["detail"]


def test_log_slow_requests_warns_past_threshold(client, monkeypatch):
    monkeypatch.setattr("backend.main.SLOW_REQUEST_SECONDS", 0)  # anything "takes too long"

    async def call_next(_request):
        return SimpleNamespace(status_code=200)

    asyncio.run(log_slow_requests(_fake_request(path="/slow"), call_next))

    assert "Slow request: GET /slow" in logging_config.LOG_PATH.read_text()


def test_log_slow_requests_silent_when_fast(client):
    async def call_next(_request):
        return SimpleNamespace(status_code=200)

    asyncio.run(log_slow_requests(_fake_request(path="/fast"), call_next))

    assert "Slow request" not in logging_config.LOG_PATH.read_text()


def test_startup_logs_current_counts(client):
    # The client fixture's TestClient(app) context manager already
    # triggered the startup lifespan once, against a fresh (empty) DB.
    log_contents = logging_config.LOG_PATH.read_text()
    assert "Startup complete." in log_contents
    assert "'entries': 0" in log_contents
