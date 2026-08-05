import logging
import time
from contextlib import asynccontextmanager

from dotenv import load_dotenv

# Must run before any other backend module is imported - database.py,
# photos.py, and logging_config.py all read env vars into module-level
# constants at import time, so .env has to be loaded into the process
# first. Docker doesn't need this (docker-compose injects env vars
# directly), but this is a harmless no-op when there's no .env file to find.
load_dotenv()

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import crud, database
from .logging_config import setup_logging
from .routers import bean_profiles, entries, insights, photos

logger = logging.getLogger(__name__)

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

# A request slower than this gets a warning in the log - an objective signal
# for "this felt slow" during 1.0.1's real-world use test, since that's
# otherwise just a subjective impression that's easy to forget to write down.
SLOW_REQUEST_SECONDS = 3.0


def resolve_spa_path(full_path: str, base: Path) -> Optional[Path]:
    # full_path comes straight from the URL, so a request like
    # "../../etc/passwd" must never be allowed to resolve outside `base` -
    # resolve() collapses any ".." segments first, and is_relative_to()
    # then confirms the result didn't escape the intended folder. Returns
    # None for "doesn't exist" and "tried to escape" alike, since the
    # caller treats both the same way (fall back to index.html).
    if not full_path:
        return None
    candidate = (base / full_path).resolve()
    if not candidate.is_relative_to(base.resolve()):
        return None
    return candidate if candidate.is_file() else None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configured here rather than at import time so tests can redirect
    # LOG_PATH per-run (see conftest.py) - module-level code only executes
    # once for the whole test session, which would be too early for that.
    setup_logging()
    database.init_db()
    conn = database.get_connection()
    try:
        # Logged so a container restart's before/after counts can be
        # compared straight from the log file (1.0.2's "confirm nothing
        # was lost" check) instead of clicking through the app to verify.
        logger.info("Startup complete. Current counts: %s", crud.get_counts(conn))
    finally:
        conn.close()
    yield


app = FastAPI(title="Coffee Bean Tracker", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_slow_requests(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    elapsed = time.monotonic() - start
    if elapsed > SLOW_REQUEST_SECONDS:
        logger.warning("Slow request: %s %s took %.1fs", request.method, request.url.path, elapsed)
    return response


@app.exception_handler(Exception)
async def log_unhandled_exception(request: Request, exc: Exception):
    # Anything that reaches here is a genuine bug, not an expected error
    # (HTTPException - 404s, 422s, etc. - has its own handler and never
    # reaches this one) - log the full traceback so it ends up in the
    # exportable log file, and never show the client raw exception detail.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error. Check the server logs."})


# All API routes live under /api - the frontend has its own pages at some
# of these same-looking paths (e.g. its Insights page is also "/insights"),
# so without this prefix the two would collide: since these routers are
# registered first, a browser refresh on the Insights page or on an entry's
# detail page would hit the API route below instead of the SPA catch-all
# further down, and show raw JSON instead of the app.
app.include_router(entries.router, prefix="/api")
app.include_router(bean_profiles.router, prefix="/api")
app.include_router(insights.router, prefix="/api")
app.include_router(photos.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}


# Serves the built React app in Docker (frontend/dist doesn't exist in local
# dev - Vite's own dev server handles that separately). Mounted after the API
# routers above so specific routes still win over this catch-all. The
# catch-all itself is needed for client-side routing (e.g. loading /history
# directly): unrecognized paths fall back to index.html instead of 404ing.
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        candidate = resolve_spa_path(full_path, FRONTEND_DIST)
        if candidate is not None:
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
