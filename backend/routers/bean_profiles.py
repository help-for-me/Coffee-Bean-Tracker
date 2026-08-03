from fastapi import APIRouter

from .. import crud, database
from ..models import BeanProfileOut

router = APIRouter(prefix="/bean-profiles", tags=["bean-profiles"])


@router.get("/autocomplete", response_model=list[BeanProfileOut])
def autocomplete(q: str, limit: int = 10):
    if not q.strip():
        return []
    conn = database.get_connection()
    try:
        return crud.search_bean_profiles(conn, q, limit)
    finally:
        conn.close()
