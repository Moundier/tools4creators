"""Studio settings and the YouTube connection."""
from fastapi import APIRouter, Body, HTTPException

from ..models import job as jobs
from ..models import settings
from ..services import tasks
from .deps import bad_request

router = APIRouter(prefix="/api")


@router.get("/settings")
def get_settings():
    return settings.load()


@router.put("/settings")
def put_settings(body: dict = Body(...)):
    return bad_request(settings.save, body)


@router.get("/youtube/status")
def youtube_status():
    from ..services.youtube_upload import CLIENT_SECRET, token_file
    return {"client_secret": CLIENT_SECRET.is_file(), "connected": token_file().is_file(),
            "client_secret_path": str(CLIENT_SECRET)}


@router.post("/youtube/connect")
def youtube_connect():
    from ..services.youtube_upload import CLIENT_SECRET
    if not CLIENT_SECRET.is_file():
        raise HTTPException(400, f"save your Google OAuth file as {CLIENT_SECRET} first (see README)")
    return jobs.submit("youtube_connect", None, tasks.youtube_connect, lane="upload")
