from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from pydantic import ValidationError

from .. import crud, database
from ..extraction import run_extraction
from ..models import EntryCreate, EntryOut, EntrySummary, RatingCreate
from ..photos import save_photo

router = APIRouter(prefix="/entries", tags=["entries"])


@router.post("", response_model=EntryOut, status_code=201)
async def create_entry(
    background_tasks: BackgroundTasks,
    data: str = Form(...),
    photos: list[UploadFile] = File(default=[]),
):
    try:
        entry_data = EntryCreate.model_validate_json(data)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    conn = database.get_connection()
    try:
        entry_id = crud.create_entry(conn, entry_data, has_photos=bool(photos))
        photo_paths = []
        for i, photo in enumerate(photos):
            contents = await photo.read()
            photo_paths.append(save_photo(entry_id, i, contents))
            crud.add_entry_photo(conn, entry_id, photo_paths[-1], i)
        if photo_paths:
            background_tasks.add_task(run_extraction, entry_id, photo_paths)
        return crud.get_entry(conn, entry_id)
    finally:
        conn.close()


@router.get("", response_model=list[EntrySummary])
def list_entries(q: Optional[str] = None, limit: Optional[int] = None):
    conn = database.get_connection()
    try:
        return crud.list_entries(conn, query=q, limit=limit)
    finally:
        conn.close()


@router.get("/{entry_id}", response_model=EntryOut)
def read_entry(entry_id: int):
    conn = database.get_connection()
    try:
        entry = crud.get_entry(conn, entry_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="Entry not found")
        return entry
    finally:
        conn.close()


@router.post("/{entry_id}/ratings", response_model=EntryOut, status_code=201)
def create_rating(entry_id: int, data: RatingCreate):
    conn = database.get_connection()
    try:
        if crud.get_entry(conn, entry_id) is None:
            raise HTTPException(status_code=404, detail="Entry not found")
        crud.add_rating(conn, entry_id, data)
        return crud.get_entry(conn, entry_id)
    finally:
        conn.close()
