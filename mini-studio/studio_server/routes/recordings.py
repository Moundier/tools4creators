"""Recordings OBS saved in the watch folder."""
import shutil
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..models import channel
from ..models import job as jobs
from ..models import project as projects
from ..models import settings
from ..services import tasks

router = APIRouter(prefix="/api")


@router.get("/recordings")
def recordings():
    return {"folder": str(projects.watch_folder()), "recordings": projects.scan_recordings()}


@router.get("/recordings/{name}/poster")
def poster(name: str):
    try:
        path = projects.recording_path(name)
    except KeyError:
        raise HTTPException(404, "recording not found")
    cache = settings.WORK / ".posters" / (projects.project_id(path) + ".jpg")
    if not cache.is_file() or cache.stat().st_mtime < path.stat().st_mtime:
        cache.parent.mkdir(parents=True, exist_ok=True)
        dur = projects.duration(path) or 0
        tasks.grab_frame(path, dur * 0.1, cache, width=480)
    return FileResponse(cache)


def _projects_of(path):
    """(channel, project folder) of every channel that has a project for this recording file."""
    pid, out = projects.project_id(path), []
    for c in channel.all_channels():
        d = channel.channel_dir(c["id"]) / pid
        p = projects.load_from(d)
        if p and p.get("file") == str(path):
            out.append((c, d))
    return out


@router.get("/recordings/{name}/usage")
def usage(name: str):
    """What deleting this recording would also delete (shown in the confirmation)."""
    try:
        path = projects.recording_path(name)
    except KeyError:
        raise HTTPException(404, "recording not found")
    return {"channels": [c["name"] for c, _ in _projects_of(path)]}


@router.delete("/recordings/{name}")
def delete_recording(name: str):
    """Delete the video file from the computer (no trash, can't be undone), plus its projects in every channel."""
    try:
        path = projects.recording_path(name)
    except KeyError:
        raise HTTPException(404, "recording not found")
    if time.time() - path.stat().st_mtime < projects.STILL_WRITING:
        raise HTTPException(409, "OBS is still writing this recording")
    pid = projects.project_id(path)
    if jobs.running_for(pid):
        raise HTTPException(409, "wait for the running job on this video to finish first")
    removed = []
    for c, d in _projects_of(path):
        if d.resolve().parent != channel.channel_dir(c["id"]).resolve():  # safety: only inside that channel
            raise HTTPException(400, "refusing to delete outside the channel folder")
        shutil.rmtree(d)
        removed.append(c["name"])
    (settings.WORK / ".posters" / (pid + ".jpg")).unlink(missing_ok=True)
    path.unlink()
    return {"deleted": name, "projects": removed}
