from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import BASE_DIR, settings
from .database import Base, engine
from .routers import admin, public
from .seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if settings.auto_seed:
        try:
            seed()
        except Exception as exc:  # noqa: BLE001
            print(f"Popolamento automatico non riuscito: {exc}")
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

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
