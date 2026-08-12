import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile
from pydantic import ValidationError

from .. import crud, database
from ..extraction import run_extraction
from ..image_utils import sniff_image_type
from ..models import EntryCreate, EntryOut, EntrySort, EntrySummary, EntryType, EntryUpdate, RatingCreate, RatingUpdate
from ..photos import save_photo
from ..rate_limit import enforce_cooldown

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/entries", tags=["entries"])

# Upload limits - a phone photo is a few MB and nobody photographs a single
# bag from more than a handful of angles, so these are generous for real
# use while still capping how much an unauthenticated request can write to
# disk in one call.
MAX_PHOTOS_PER_ENTRY = 10
MAX_PHOTO_BYTES = 15 * 1024 * 1024

# Re-extraction spends the Anthropic API key's quota, so it's cooled down
# per entry rather than left free to hammer.
REEXTRACT_COOLDOWN_SECONDS = 30


def _bean_label(entry: dict) -> str:
    return f"{entry['bean_profile']['roaster']} — {entry['bean_profile']['bean_name']}"


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

    if len(photos) > MAX_PHOTOS_PER_ENTRY:
        raise HTTPException(status_code=422, detail=f"At most {MAX_PHOTOS_PER_ENTRY} photos per entry.")

    # Read and validate every photo up front, before creating anything in
    # the database - a rejected upload should never leave a half-created
    # entry behind. Checks the file's actual bytes rather than trusting
    # whatever content-type the client claims.
    photo_contents = []
    for photo in photos:
        contents = await photo.read()
        if len(contents) > MAX_PHOTO_BYTES:
            raise HTTPException(
                status_code=422, detail=f"Photos must be under {MAX_PHOTO_BYTES // (1024 * 1024)}MB."
            )
        if sniff_image_type(contents) is None:
            raise HTTPException(status_code=422, detail="One of the uploaded files isn't a recognized image type.")
        photo_contents.append(contents)

    has_identity = bool(entry_data.roaster and entry_data.bean_name)
    # A bag with at least one photo can skip typed identity - extraction
    # resolves it. Cafe cups have nothing printed to photograph for this,
    # so they always need it typed.
    identity_from_photo_allowed = entry_data.entry_type == "bag" and bool(photos)
    if not has_identity and not identity_from_photo_allowed:
        raise HTTPException(
            status_code=422,
            detail="Roaster and bean name are required, unless attaching a photo to a bag entry.",
        )

    conn = database.get_connection()
    try:
        entry_id = crud.create_entry(conn, entry_data, has_photos=bool(photos))
        photo_paths = []
        for i, contents in enumerate(photo_contents):
            photo_paths.append(save_photo(entry_id, i, contents))
            crud.add_entry_photo(conn, entry_id, photo_paths[-1], i)
        if photo_paths:
            background_tasks.add_task(run_extraction, entry_id, photo_paths)
        entry = crud.get_entry(conn, entry_id)
        # Identity source matters for 1.0.1's real-world-use checklist (bag
        # via photo vs. bag typed by hand vs. a cafe cup, which always
        # requires typing) - logged here rather than left to be pieced
        # together from field values later.
        identity_source = "typed" if has_identity else "photo (identity pending extraction)"
        logger.info(
            "Entry created: id=%s type=%s identity=%s bean=%r score=%s has_photos=%s",
            entry_id, entry_data.entry_type, identity_source, _bean_label(entry), entry_data.score, bool(photo_paths),
        )
        return entry
    finally:
        conn.close()


@router.get("", response_model=list[EntrySummary])
def list_entries(
    q: Optional[str] = None,
    limit: Optional[int] = None,
    entry_type: Optional[EntryType] = None,
    sort: EntrySort = "date_desc",
):
    conn = database.get_connection()
    try:
        return crud.list_entries(conn, query=q, limit=limit, entry_type=entry_type, sort=sort)
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
        entry = crud.get_entry(conn, entry_id)
        # This is also how "Rate a Previous Bean" adds a rating - a second
        # log line for the same bean confirms 1.0.1's repeat-rating check
        # without needing to track it by hand.
        logger.info("Rating added: entry_id=%s score=%s bean=%r", entry_id, data.score, _bean_label(entry))
        return entry
    finally:
        conn.close()


@router.patch("/{entry_id}", response_model=EntryOut)
def update_entry(entry_id: int, data: EntryUpdate):
    conn = database.get_connection()
    try:
        updated = crud.update_entry(conn, entry_id, data.model_dump(exclude_unset=True))
        if not updated:
            raise HTTPException(status_code=404, detail="Entry not found")
        return crud.get_entry(conn, entry_id)
    finally:
        conn.close()


@router.delete("/{entry_id}", status_code=204)
def delete_entry(entry_id: int):
    conn = database.get_connection()
    try:
        photo_paths = crud.delete_entry(conn, entry_id)
    finally:
        conn.close()
    if photo_paths is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    for path in photo_paths:
        Path(path).unlink(missing_ok=True)


@router.post("/{entry_id}/reextract", response_model=EntryOut)
def reextract_entry(entry_id: int, background_tasks: BackgroundTasks, request: Request):
    enforce_cooldown(request, f"reextract:{entry_id}", REEXTRACT_COOLDOWN_SECONDS)
    conn = database.get_connection()
    try:
        if crud.get_entry(conn, entry_id) is None:
            raise HTTPException(status_code=404, detail="Entry not found")
        photo_paths = crud.get_entry_photo_paths(conn, entry_id)
        if not photo_paths:
            raise HTTPException(status_code=422, detail="This entry has no photos to re-extract from.")
        crud.mark_extraction_pending(conn, entry_id)
        background_tasks.add_task(run_extraction, entry_id, photo_paths)
        return crud.get_entry(conn, entry_id)
    finally:
        conn.close()


@router.patch("/{entry_id}/ratings/{rating_id}", response_model=EntryOut)
def update_rating(entry_id: int, rating_id: int, data: RatingUpdate):
    conn = database.get_connection()
    try:
        if crud.get_entry(conn, entry_id) is None:
            raise HTTPException(status_code=404, detail="Entry not found")
        updated = crud.update_rating(conn, rating_id, data.model_dump(exclude_unset=True))
        if not updated:
            raise HTTPException(status_code=404, detail="Rating not found")
        return crud.get_entry(conn, entry_id)
    finally:
        conn.close()


@router.delete("/{entry_id}/ratings/{rating_id}", response_model=EntryOut)
def delete_rating(entry_id: int, rating_id: int):
    conn = database.get_connection()
    try:
        if crud.get_entry(conn, entry_id) is None:
            raise HTTPException(status_code=404, detail="Entry not found")
        deleted = crud.delete_rating(conn, rating_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Rating not found")
        return crud.get_entry(conn, entry_id)
    finally:
        conn.close()
