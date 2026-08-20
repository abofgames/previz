from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env before anything reads os.environ-driven config (the client factory).
load_dotenv()

# uvicorn configures only its own loggers, so without this the app's own INFO
# lines — which model ran, which fallback was taken, why a card failed — never
# reach the console.
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(levelname)s %(name)s: %(message)s",
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import routes, ws
from .project import PROJECTS_ROOT

app = FastAPI(title="previz")

# Only needed when the UI is served from a different origin (the Vite dev
# server). In a deployed container the frontend is served from this app, so
# same-origin applies and this is inert.
_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router, prefix="/api")
app.include_router(ws.router)

PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/projects", StaticFiles(directory=PROJECTS_ROOT), name="projects")

# Serve the built frontend when it exists, so the whole app is one service and
# one URL. Absent in local dev, where Vite serves the UI instead.
_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(_DIST / "index.html")
