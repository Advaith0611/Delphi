import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.services.project_builder import PUBLISHED_ROOT

app = FastAPI(title="Pythios Spatial AI API", version="0.1.0")
DEPLOYMENTS_DIR = PUBLISHED_ROOT

default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "https://pythios.xyz",
    "https://www.pythios.xyz",
    "https://app.pythios.xyz",
    "https://delphi.pythios.xyz",
]

extra_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

# Keep the normal production domains working if the frontend is served from a
# subdomain, while still requiring HTTPS and the project's own domain.
origin_regex = os.getenv(
    "ALLOWED_ORIGIN_REGEX",
    r"https://([a-z0-9-]+\.)*pythios\.xyz",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[*default_origins, *extra_origins],
    allow_origin_regex=origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

DEPLOYMENTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/apps", StaticFiles(directory=DEPLOYMENTS_DIR, html=True), name="pythios-apps")
app.mount("/app", StaticFiles(directory=DEPLOYMENTS_DIR, html=True), name="pythios-apps-path")


@app.get("/")
async def root():
    return {"name": "Pythios Spatial AI API", "status": "ok"}


app.mount("/", StaticFiles(directory=DEPLOYMENTS_DIR, html=True), name="pythios-root-apps")
