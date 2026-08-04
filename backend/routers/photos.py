from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from .. import database

router = APIRouter(prefix="/photos", tags=["photos"])


@router.get("/{photo_id}")
def get_photo(photo_id: int):
    conn = database.get_connection()
    try:
        row = conn.execute(
            "SELECT photo_path FROM entry_photos WHERE id = ?", (photo_id,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    # photo_path comes from the DB, never from this request, so there's no
    # path-traversal surface here - it's whatever save_photo() wrote.
    path = Path(row["photo_path"])
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Photo file missing on disk")
    return FileResponse(path, media_type="image/jpeg")
