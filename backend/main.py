from __future__ import annotations

from dotenv import load_dotenv

# Load .env before anything reads os.environ-driven config (the client factory).
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api import routes, ws
from .project import PROJECTS_ROOT

app = FastAPI(title="previz")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(routes.router, prefix="/api")
app.include_router(ws.router)

PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/projects", StaticFiles(directory=PROJECTS_ROOT), name="projects")
