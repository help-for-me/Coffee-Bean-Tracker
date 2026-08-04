from fastapi import APIRouter

from .. import database
from ..insights.stats import get_insights
from ..models import InsightsOut

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("", response_model=InsightsOut)
def read_insights():
    conn = database.get_connection()
    try:
        return get_insights(conn)
    finally:
        conn.close()
