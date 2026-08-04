from typing import Optional

from fastapi import APIRouter, HTTPException

from .. import crud, database
from ..insights.narrative import generate_narrative
from ..insights.stats import get_insights
from ..models import InsightNarrativeOut, InsightsOut, WindowType

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("", response_model=InsightsOut)
def read_insights():
    conn = database.get_connection()
    try:
        return get_insights(conn)
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
def create_narrative(window: WindowType = "all_time"):
    conn = database.get_connection()
    try:
        return generate_narrative(conn, window)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Insight generation failed: {exc}") from exc
    finally:
        conn.close()
