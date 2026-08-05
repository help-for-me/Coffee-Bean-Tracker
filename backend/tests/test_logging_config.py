import logging

from backend import logging_config


def test_setup_logging_creates_log_directory(tmp_path, monkeypatch):
    log_path = tmp_path / "logs" / "app.log"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    logging_config.setup_logging()

    assert log_path.parent.is_dir()


def test_setup_logging_writes_to_file(tmp_path, monkeypatch):
    log_path = tmp_path / "logs" / "app.log"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    logging_config.setup_logging()
    logging.getLogger("backend.test").info("hello from a test")

    assert log_path.exists()
    assert "hello from a test" in log_path.read_text()


def test_setup_logging_is_idempotent(tmp_path, monkeypatch):
    log_path = tmp_path / "logs" / "app.log"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    logging_config.setup_logging()
    logging_config.setup_logging()
    logging.getLogger("backend.test").info("only once")

    # Re-running setup shouldn't pile up duplicate handlers - the message
    # should appear exactly once in the file, not twice.
    contents = log_path.read_text()
    assert contents.count("only once") == 1


def test_setup_logging_uses_rotating_handler(tmp_path, monkeypatch):
    log_path = tmp_path / "logs" / "app.log"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    logging_config.setup_logging()

    root = logging.getLogger()
    file_handlers = [h for h in root.handlers if hasattr(h, "maxBytes")]
    assert len(file_handlers) == 1
    assert file_handlers[0].maxBytes == logging_config.MAX_BYTES
    assert file_handlers[0].backupCount == logging_config.BACKUP_COUNT


def test_setup_logging_routes_uvicorn_access_log_into_the_file(tmp_path, monkeypatch):
    # Uvicorn configures its own handlers with propagate=False by default,
    # so without this, per-request access lines (and the client IP in
    # them) only ever reach stdout, never the exportable file.
    log_path = tmp_path / "logs" / "app.log"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    logging_config.setup_logging()
    logging.getLogger("uvicorn.access").info('127.0.0.1:0 - "GET /health HTTP/1.1" 200 OK')

    assert "GET /health" in log_path.read_text()


def test_setup_logging_uvicorn_loggers_have_no_handlers_of_their_own(tmp_path, monkeypatch):
    # Confirms messages reach the file via propagation to root, not via a
    # second, separately-configured handler that would double-print them.
    log_path = tmp_path / "logs" / "app.log"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    logging_config.setup_logging()

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        assert uvicorn_logger.handlers == []
        assert uvicorn_logger.propagate is True
