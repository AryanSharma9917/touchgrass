"""FastAPI application and static frontend routes."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.models import Mission, MissionRequest
from app.services.mission_generator import (
    MissionGenerationError,
    generate_mission,
)

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title=get_settings().app_name)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/missions", response_model=Mission)
async def create_mission(request: MissionRequest) -> Mission:
    try:
        return await generate_mission(request)
    except MissionGenerationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
