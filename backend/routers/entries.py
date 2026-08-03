from typing import Optional

from fastapi import APIRouter, HTTPException

from .. import crud, database
from ..models import EntryCreate, EntryOut, EntrySummary, RatingCreate

router = APIRouter(prefix="/entries", tags=["entries"])


@router.post("", response_model=EntryOut, status_code=201)
def create_entry(data: EntryCreate):
    conn = database.get_connection()
    try:
        entry_id = crud.create_entry(conn, data)
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
