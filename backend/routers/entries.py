from fastapi import APIRouter, HTTPException

from .. import crud, database
from ..models import EntryCreate, EntryOut

router = APIRouter(prefix="/entries", tags=["entries"])


@router.post("", response_model=EntryOut, status_code=201)
def create_entry(data: EntryCreate):
    conn = database.get_connection()
    try:
        entry_id = crud.create_entry(conn, data)
        return crud.get_entry(conn, entry_id)
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
