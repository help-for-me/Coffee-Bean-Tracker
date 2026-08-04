from contextlib import asynccontextmanager

from dotenv import load_dotenv

# Must run before any other backend module is imported - database.py and
# photos.py read env vars into module-level constants at import time, so
# .env has to be loaded into the process first. Docker doesn't need this
# (docker-compose injects env vars directly), but this is a harmless no-op
# when there's no .env file to find.
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import database
from .routers import bean_profiles, entries


@asynccontextmanager
async def lifespan(app: FastAPI):
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


@app.get("/health")
def health():
    return {"status": "ok"}
