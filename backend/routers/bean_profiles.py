from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Request, UploadFile

from .. import crud, database
from ..enrichment import run_enrichment_confirm, run_enrichment_lookup, run_enrichment_upload
from ..image_utils import sniff_image_type
from ..models import BeanProfileOut, EnrichmentConfirm, EnrichmentManualUrl, EnrichmentOut, EnrichmentReprocess
from ..rate_limit import enforce_cooldown

router = APIRouter(prefix="/bean-profiles", tags=["bean-profiles"])

# All enrichment endpoints below spend the Anthropic API key's quota (a web
# search and/or a fetch/extract call), so they're cooled down the same way
# entries.py's re-extract endpoint is.
ENRICHMENT_COOLDOWN_SECONDS = 30

# Matches entries.py's per-photo limit - an uploaded screenshot or PDF spec
# sheet is the same order of size as a bag photo.
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
_PDF_MAGIC = b"%PDF-"


@router.get("/autocomplete", response_model=list[BeanProfileOut])
def autocomplete(q: str, limit: int = 10):
    if not q.strip():
        return []
    conn = database.get_connection()
    try:
        return crud.search_bean_profiles(conn, q, limit)
    finally:
        conn.close()


@router.post("/{bean_profile_id}/enrichment/reprocess", response_model=EnrichmentOut)
def reprocess_enrichment(
    bean_profile_id: int, data: EnrichmentReprocess, background_tasks: BackgroundTasks, request: Request
):
    # Covers both a plain manual reprocess (no context) and a "none of
    # these" rejection that supplies a hint for the next search - either
    # way, this resets the row to 'pending' and re-runs the lookup.
    enforce_cooldown(request, f"enrichment-reprocess:{bean_profile_id}", ENRICHMENT_COOLDOWN_SECONDS)
    conn = database.get_connection()
    try:
        profile = crud.get_bean_profile(conn, bean_profile_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Bean profile not found")
        crud.mark_enrichment_pending(conn, bean_profile_id, extra_context=data.context)
        background_tasks.add_task(run_enrichment_lookup, bean_profile_id, data.context)
        return crud.get_enrichment(conn, bean_profile_id)
    finally:
        conn.close()


@router.post("/{bean_profile_id}/enrichment/confirm", response_model=EnrichmentOut)
def confirm_enrichment_candidate(
    bean_profile_id: int, data: EnrichmentConfirm, background_tasks: BackgroundTasks, request: Request
):
    enforce_cooldown(request, f"enrichment-confirm:{bean_profile_id}", ENRICHMENT_COOLDOWN_SECONDS)
    conn = database.get_connection()
    try:
        enrichment = crud.get_enrichment(conn, bean_profile_id)
        if enrichment is None:
            raise HTTPException(status_code=404, detail="No enrichment lookup found for this bean profile")
        if not any(candidate["url"] == data.url for candidate in enrichment["candidates"]):
            raise HTTPException(status_code=422, detail="That URL wasn't one of the offered candidates")
        crud.mark_enrichment_pending(conn, bean_profile_id)
        background_tasks.add_task(run_enrichment_confirm, bean_profile_id, data.url, data.title)
        return crud.get_enrichment(conn, bean_profile_id)
    finally:
        conn.close()


@router.post("/{bean_profile_id}/enrichment/manual-url", response_model=EnrichmentOut)
def submit_manual_enrichment_url(
    bean_profile_id: int, data: EnrichmentManualUrl, background_tasks: BackgroundTasks, request: Request
):
    # For when the automated search can't find the right page but the user,
    # searching by hand, can - skips straight to fetch+extract against a
    # URL the user supplies themselves, unlike /confirm above which only
    # accepts a URL Claude itself offered as a candidate.
    enforce_cooldown(request, f"enrichment-confirm:{bean_profile_id}", ENRICHMENT_COOLDOWN_SECONDS)
    url = data.url.strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="That doesn't look like a valid URL.")
    conn = database.get_connection()
    try:
        profile = crud.get_bean_profile(conn, bean_profile_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Bean profile not found")
        crud.mark_enrichment_pending(conn, bean_profile_id)
        background_tasks.add_task(run_enrichment_confirm, bean_profile_id, url, url)
        return crud.get_enrichment(conn, bean_profile_id)
    finally:
        conn.close()


@router.post("/{bean_profile_id}/enrichment/upload", response_model=EnrichmentOut)
async def upload_enrichment_source(
    bean_profile_id: int, background_tasks: BackgroundTasks, request: Request, file: UploadFile = File(...)
):
    # For when the user has a screenshot or PDF (a product page, a spec
    # sheet) with the roaster's own info on it - treated as the
    # authoritative source (status goes straight to 'confirmed'), with a
    # background web search afterward only ever filling whatever it didn't
    # cover (see run_enrichment_upload).
    enforce_cooldown(request, f"enrichment-confirm:{bean_profile_id}", ENRICHMENT_COOLDOWN_SECONDS)
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=422, detail=f"File must be under {MAX_UPLOAD_BYTES // (1024 * 1024)}MB.")
    media_type = sniff_image_type(contents)
    if media_type is None and contents[: len(_PDF_MAGIC)] == _PDF_MAGIC:
        media_type = "application/pdf"
    if media_type is None:
        raise HTTPException(status_code=422, detail="That file isn't a recognized image or PDF.")
    conn = database.get_connection()
    try:
        profile = crud.get_bean_profile(conn, bean_profile_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Bean profile not found")
        crud.mark_enrichment_pending(conn, bean_profile_id)
        background_tasks.add_task(run_enrichment_upload, bean_profile_id, contents, media_type)
        return crud.get_enrichment(conn, bean_profile_id)
    finally:
        conn.close()
