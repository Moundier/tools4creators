"""Projects: open/discard, wizard state, the recording's video/frames, uploaded images."""
import shutil
from pathlib import Path

from fastapi import APIRouter, Body, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

from ..models import job as jobs
from ..models import project as projects
from ..models import channel
from ..models.project import project_dir
from ..services import tasks
from .deps import project_or_404

router = APIRouter(prefix="/api")
SLOTS = {"person", "bg", "art", "art2"}
PROJECT_FIELDS = {"subtitles", "shorts", "thumbnail", "publish"}


@router.post("/projects")
def open_project(body: dict = Body(...)):
    try:
        return projects.open_project(body.get("name", ""))
    except KeyError:
        raise HTTPException(404, "recording not found")


@router.get("/projects/{pid}")
def get_project(pid: str):
    p = project_or_404(pid)
    d = project_dir(pid)
    files = {s: (f.name if (f := tasks.image_slot(pid, s)) else None) for s in SLOTS}
    files.update(cutout=(d / "cutout.png").is_file(), thumb=(d / "thumb.png").is_file(),
                 srt=(d / "video.srt").is_file())
    return {**p, "files": files, "jobs": jobs.for_project(pid)}


@router.patch("/projects/{pid}")
def patch_project(pid: str, body: dict = Body(...)):
    project_or_404(pid)

    def apply(p):
        for k, v in body.items():
            if k in PROJECT_FIELDS:
                p[k] = {**p[k], **v} if isinstance(p[k], dict) and isinstance(v, dict) else v
    return projects.update(pid, apply)


@router.delete("/projects/{pid}")
def discard_project(pid: str):
    """Throw away everything this channel made for the recording. The recording itself is never touched."""
    project_or_404(pid)
    if jobs.for_project(pid):
        raise HTTPException(409, "wait for the running job to finish (or stop the server) before discarding")
    d = project_dir(pid).resolve()
    if d.parent != channel.work_dir().resolve():  # safety: only ever delete inside this channel's folder
        raise HTTPException(400, "refusing to delete outside the work folder")
    shutil.rmtree(d)
    return {"discarded": pid}


@router.post("/projects/{pid}/status")
def set_status(pid: str, body: dict = Body(...)):
    project_or_404(pid)
    if body.get("status") not in ("editing", "uploaded"):
        raise HTTPException(400, "status must be editing or uploaded")
    return projects.update(pid, lambda p: p.update(status=body["status"]))


@router.get("/projects/{pid}/video")
def video(pid: str):
    return FileResponse(project_or_404(pid)["file"])


@router.get("/projects/{pid}/frame")
def frame(pid: str, t: float = 0, width: int | None = None):
    data = tasks.grab_frame(project_or_404(pid)["file"], t, width=width)
    return Response(data, media_type="image/jpeg")


@router.get("/projects/{pid}/files/{path:path}")
def project_file(pid: str, path: str):
    project_or_404(pid)
    d = project_dir(pid).resolve()
    f = (d / path).resolve()
    if not f.is_relative_to(d) or not f.is_file() or f.name == "project.json":
        raise HTTPException(404, "file not found")
    return FileResponse(f, headers={"Cache-Control": "no-cache"})


@router.post("/projects/{pid}/upload/{slot}")
def upload_image(pid: str, slot: str, file: UploadFile = File(...)):
    project_or_404(pid)
    ext = Path(file.filename or "").suffix.lower()
    if slot not in SLOTS or ext not in tasks.IMAGE_EXTS:
        raise HTTPException(400, "unsupported slot or image type (png, jpg, webp)")
    d = project_dir(pid)
    old = tasks.image_slot(pid, slot)
    if old:
        old.unlink()
    with open(d / (slot + ext), "wb") as fh:
        shutil.copyfileobj(file.file, fh)
    if slot == "person":  # a new photo invalidates the old cutout
        (d / "cutout.png").unlink(missing_ok=True)
        projects.update(pid, lambda p: p["cutout"].update(done=False))
    return {"file": slot + ext}


@router.delete("/projects/{pid}/upload/{slot}")
def delete_image(pid: str, slot: str):
    project_or_404(pid)
    f = tasks.image_slot(pid, slot) if slot in SLOTS else None
    if f:
        f.unlink()
    return {"deleted": bool(f)}


@router.post("/projects/{pid}/bg-from-frame")
def bg_from_frame(pid: str, body: dict = Body(...)):
    p = project_or_404(pid)
    old = tasks.image_slot(pid, "bg")
    if old:
        old.unlink()
    tasks.grab_frame(p["file"], float(body.get("t", 0)), project_dir(pid) / "bg.jpg")
    return {"file": "bg.jpg"}
