import json
import logging
from datetime import date

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from .. import crud, database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data", tags=["data"])


class ImportPayload(BaseModel):
    # A separate flag from the export data itself, so a client can't
    # trigger the restore just by POSTing a previously-downloaded export
    # file unmodified - this has to be an explicit, deliberate choice,
    # since it replaces every entry, rating, and photo record in the app.
    confirm: bool
    data: dict


@router.get("/export")
def export_data():
    conn = database.get_connection()
    try:
        payload = crud.get_full_export(conn)
    finally:
        conn.close()
    filename = f"coffee-bean-tracker-backup-{date.today().isoformat()}.json"
    return Response(
        content=json.dumps(payload, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import")
def import_data(payload: ImportPayload):
    if not payload.confirm:
        raise HTTPException(
            status_code=400, detail="Set confirm=true to acknowledge this replaces all existing data."
        )
    conn = database.get_connection()
    try:
        try:
            counts = crud.import_full_export(conn, payload.data)
        except crud.ImportValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        logger.warning("Data import completed - all existing data replaced. New counts: %s", counts)
        return counts
    finally:
        conn.close()
