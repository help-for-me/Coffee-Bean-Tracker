import os
from datetime import date
from pathlib import Path

PHOTOS_PATH = Path(os.environ.get("PHOTOS_PATH", "data/photos"))


def save_photo(entry_id: int, upload_order: int, contents: bytes) -> str:
    PHOTOS_PATH.mkdir(parents=True, exist_ok=True)
    filename = f"{entry_id}_{date.today().strftime('%Y%m%d')}_{upload_order}.jpg"
    path = PHOTOS_PATH / filename
    path.write_bytes(contents)
    return str(path)
