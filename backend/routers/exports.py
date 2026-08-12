import logging
import os
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Response

from .. import crud, database
from ..exports.csv_sink import build_csv
from ..exports.github_sink import GithubSinkNotConfigured, push_to_github
from ..exports.xlsx_sink import build_xlsx
from ..insights.stats import get_insights

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/exports", tags=["exports"])

LOCAL_XLSX_PATH = Path(os.environ.get("LOCAL_XLSX_PATH", "exports/coffee-bean-tracker.xlsx"))


def _local_xlsx_enabled() -> bool:
    return os.environ.get("LOCAL_XLSX_ENABLED", "").lower() in ("1", "true", "yes")


def _github_backup_enabled() -> bool:
    return os.environ.get("GITHUB_BACKUP_ENABLED", "").lower() in ("1", "true", "yes")


@router.get("/status")
def export_status():
    conn = database.get_connection()
    try:
        return {
            "local_xlsx": {"enabled": _local_xlsx_enabled(), "last": crud.get_last_export(conn, "local_xlsx")},
            "github": {"enabled": _github_backup_enabled(), "last": crud.get_last_export(conn, "github")},
        }
    finally:
        conn.close()


@router.get("/csv")
def export_csv():
    # A plain on-demand report, not a tracked "sink" - nothing persists on
    # the server and there's no export_log entry, since there's nothing
    # to report the status of for a synchronous download.
    conn = database.get_connection()
    try:
        content = build_csv(crud.get_export_rows(conn))
    finally:
        conn.close()
    filename = f"coffee-bean-tracker-{date.today().isoformat()}.csv"
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/xlsx")
def export_xlsx():
    conn = database.get_connection()
    try:
        rows = crud.get_export_rows(conn)
        insights = get_insights(conn)
        content = build_xlsx(rows, insights)
        if _local_xlsx_enabled():
            try:
                LOCAL_XLSX_PATH.parent.mkdir(parents=True, exist_ok=True)
                LOCAL_XLSX_PATH.write_bytes(content)
                crud.log_export(conn, "local_xlsx", "success")
            except Exception:
                logger.exception("Local XLSX backup failed")
                crud.log_export(conn, "local_xlsx", "failed")
    finally:
        conn.close()
    filename = f"coffee-bean-tracker-{date.today().isoformat()}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/github")
def export_github():
    if not _github_backup_enabled():
        raise HTTPException(status_code=400, detail="GitHub backup isn't enabled - set GITHUB_BACKUP_ENABLED in .env.")
    conn = database.get_connection()
    try:
        rows = crud.get_export_rows(conn)
        insights = get_insights(conn)
        content = build_xlsx(rows, insights)
        path = f"coffee-bean-tracker-{date.today().isoformat()}.xlsx"
        try:
            push_to_github(content, path)
        except GithubSinkNotConfigured as exc:
            crud.log_export(conn, "github", "failed")
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("GitHub backup failed")
            crud.log_export(conn, "github", "failed")
            raise HTTPException(status_code=502, detail="GitHub backup failed. Check the server logs.") from exc
        crud.log_export(conn, "github", "success")
        return crud.get_last_export(conn, "github")
    finally:
        conn.close()
