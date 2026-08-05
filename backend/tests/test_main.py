from backend.main import resolve_spa_path


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
