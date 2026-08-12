import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from .. import crud, database
from ..insights.narrative import generate_narrative
from ..insights.stats import get_insights
from ..models import BrewStyle, InsightNarrativeOut, InsightsOut, WindowType
from ..rate_limit import enforce_cooldown

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insights", tags=["insights"])

# Generation spends the Anthropic API key's quota, so it's cooled down per
# time window rather than left free to hammer.
NARRATIVE_COOLDOWN_SECONDS = 30


@router.get("", response_model=InsightsOut)
def read_insights(brew_style: Optional[BrewStyle] = None):
    conn = database.get_connection()
    try:
        return get_insights(conn, brew_style=brew_style)
    finally:
        conn.close()


@router.get("/narrative", response_model=Optional[InsightNarrativeOut])
def read_narrative(window: WindowType = "all_time"):
    conn = database.get_connection()
    try:
        return crud.get_latest_narrative(conn, window)
    finally:
        conn.close()


@router.post("/narrative", response_model=InsightNarrativeOut)
def create_narrative(request: Request, window: WindowType = "all_time"):
    enforce_cooldown(request, f"narrative:{window}", NARRATIVE_COOLDOWN_SECONDS)
    conn = database.get_connection()
    try:
        return generate_narrative(conn, window)
    except Exception as exc:
        # The real reason (e.g. a missing API key, or whatever an SDK
        # dependency put in its exception text) is logged for whoever runs
        # the server to see - it's never safe to hand raw exception text
        # back to the client, since there's no way to know in advance what
        # a given failure might contain.
        logger.exception("Insight generation failed")
        raise HTTPException(status_code=502, detail="Insight generation failed. Check the server logs.") from exc
    finally:
        conn.close()
