import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Relative to the working directory, same convention as DB_PATH/PHOTOS_PATH -
# resolves under the already-mounted data/ volume in Docker, so log files
# survive restarts and are reachable from Unraid's file browser without
# going through the Docker UI's Logs panel.
LOG_PATH = Path(os.environ.get("LOG_PATH", "data/logs/app.log"))

# Caps a single run's log growth on a host that's expected to stay up
# indefinitely - old data rotates out rather than filling the disk.
MAX_BYTES = 5_000_000
BACKUP_COUNT = 3


def setup_logging() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # Idempotent - safe to call more than once (e.g. once per test, via the
    # app's lifespan) without piling up duplicate handlers and duplicate
    # log lines.
    root.handlers.clear()

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    file_handler = RotatingFileHandler(LOG_PATH, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
