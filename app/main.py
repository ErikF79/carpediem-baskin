from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from .config import BASE_DIR, settings
from .database import Base, engine
from .routers import admin, public
from .seed import seed


def _ensure_schema() -> None:
    """Aggiunge colonne mancanti alle tabelle gia esistenti (mini-migrazione)."""
    insp = inspect(engine)
    if "players" not in insp.get_table_names():
        return
    columns = {c["name"] for c in insp.get_columns("players")}
    if "shot_distance_cm" not in columns:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE players ADD COLUMN shot_distance_cm INTEGER")
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _ensure_schema()
    if settings.auto_seed:
        try:
            seed()
        except Exception as exc:  # noqa: BLE001
            print(f"Popolamento automatico non riuscito: {exc}")
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(public.router)
app.include_router(admin.auth_router)
app.include_router(admin.router)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(
        TEMPLATES_DIR / "index.html", headers={"Cache-Control": "no-cache"}
    )


@app.get("/sw.js", include_in_schema=False)
def service_worker() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "sw.js",
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/manifest.webmanifest", include_in_schema=False)
def manifest() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "manifest.webmanifest", media_type="application/manifest+json"
    )

import shutil
import os

@app.get("/api/force-reset", include_in_schema=False)
def force_reset():
    Base.metadata.drop_all(bind=engine)
    seed()
    return {"status": "ok", "message": "DB resettato con nuovi dati"}

@app.get("/api/backup", include_in_schema=False)
def backup():
    db_path = "carpediem.db"
    backup_path = "carpediem-backup.db"
    if os.path.exists(db_path):
        shutil.copyfile(db_path, backup_path)
        return {"status": "ok", "message": f"Backup creato: {backup_path}"}
    return {"status": "error", "message": "DB non trovato"}

@app.get("/api/restore", include_in_schema=False)
def restore():
    backup_path = "carpediem-backup.db"
    db_path = "carpediem.db"
    if os.path.exists(backup_path):
        shutil.copyfile(backup_path, db_path)
        return {"status": "ok", "message": "DB ripristinato dal backup"}
    return {"status": "error", "message": "Backup non trovato"}
