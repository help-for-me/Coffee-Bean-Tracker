from contextlib import asynccontextmanager

from dotenv import load_dotenv

# Must run before any other backend module is imported - database.py,
# photos.py, and logging_config.py all read env vars into module-level
# constants at import time, so .env has to be loaded into the process
# first. Docker doesn't need this (docker-compose injects env vars
# directly), but this is a harmless no-op when there's no .env file to find.
load_dotenv()

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import database
from .logging_config import setup_logging
from .routers import bean_profiles, entries, insights

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configured here rather than at import time so tests can redirect
    # LOG_PATH per-run (see conftest.py) - module-level code only executes
    # once for the whole test session, which would be too early for that.
    setup_logging()
    database.init_db()
    yield


app = FastAPI(title="Coffee Bean Tracker", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(entries.router)
app.include_router(bean_profiles.router)
app.include_router(insights.router)


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
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
