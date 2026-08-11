from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from .. import crud, database
from ..enrichment import run_enrichment_confirm, run_enrichment_lookup
from ..models import BeanProfileOut, EnrichmentConfirm, EnrichmentOut, EnrichmentReprocess
from ..rate_limit import enforce_cooldown

router = APIRouter(prefix="/bean-profiles", tags=["bean-profiles"])

# Both endpoints below spend the Anthropic API key's quota (a web search and
# possibly a fetch+extract call), so they're cooled down the same way
# entries.py's re-extract endpoint is.
ENRICHMENT_COOLDOWN_SECONDS = 30


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
