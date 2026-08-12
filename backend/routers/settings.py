import os

from fastapi import APIRouter

from .. import crud, database
from ..models import SettingsOut, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])

# Each DB-backed setting's env-var name and hardcoded fallback, used until
# the user overrides it here - same defaults get_insights used before this
# milestone, just no longer the only way to change them.
_RECENT_WINDOW_DEFAULTS = {
    "recent_window_months": ("RECENT_WINDOW_MONTHS", 4),
    "recent_window_count": ("RECENT_WINDOW_COUNT", 10),
}


def _int_setting(conn, key: str) -> int:
    stored = crud.get_setting(conn, key)
    if stored is not None:
        return int(stored)
    env_var, default = _RECENT_WINDOW_DEFAULTS[key]
    return int(os.environ.get(env_var, default))


def _read_settings(conn) -> SettingsOut:
    return SettingsOut(
        recent_window_months=_int_setting(conn, "recent_window_months"),
        recent_window_count=_int_setting(conn, "recent_window_count"),
        extraction_custom_instructions=crud.get_setting(conn, "extraction_custom_instructions") or "",
        narrative_custom_instructions=crud.get_setting(conn, "narrative_custom_instructions") or "",
    )


@router.get("", response_model=SettingsOut)
def read_settings():
    conn = database.get_connection()
    try:
        return _read_settings(conn)
    finally:
        conn.close()


@router.put("", response_model=SettingsOut)
def update_settings(data: SettingsUpdate):
    conn = database.get_connection()
    try:
        for key, value in data.model_dump(exclude_unset=True).items():
            crud.set_setting(conn, key, str(value))
        return _read_settings(conn)
    finally:
        conn.close()
