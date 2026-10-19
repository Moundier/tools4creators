"""The channel's library: saved photos + cutouts to reuse in other projects, and saved thumbnail colors."""
import shutil

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse

from ..models import library
from ..models import project as projects
from ..models.project import project_dir
from ..services import tasks
from .deps import bad_request, project_or_404

router = APIRouter(prefix="/api")


def _photo_dir(photo):
    try:
        return library.photo_dir(photo)
    except KeyError:
        raise HTTPException(404, "saved photo not found")


@router.get("/library")
def get_library(pid: str | None = None):
    """Saved photos and colors; with ?pid, also which saved photo that project's photo is (None if not saved)."""
    current = None
    if pid:
        project_or_404(pid)
        person = tasks.image_slot(pid, "person")
        if person:
            current = library.photo_id(person)
    ids = {p["id"] for p in library.photos()}
    return {"photos": library.photos(), "colors": library.colors(), "current": current if current in ids else None}


@router.get("/library/photos/{photo}/{kind}")
def photo_file(photo: str, kind: str):
    d = _photo_dir(photo)
    f = d / "cutout.png" if kind == "cutout" else library.original(d) if kind == "photo" else None
    if not f or not f.is_file():
        raise HTTPException(404, "file not found")
    return FileResponse(f)


@router.delete("/library/photos/{photo}")
def delete_photo(photo: str):
    _photo_dir(photo)
    library.delete_photo(photo)
    return {"deleted": photo}


@router.post("/projects/{pid}/library/save")
def save_photo(pid: str):
    """Keep this project's photo and its cutout in the library."""
    project_or_404(pid)
    person, cutout = tasks.image_slot(pid, "person"), project_dir(pid) / "cutout.png"
    if not person or not cutout.is_file():
        raise HTTPException(400, "remove the background first")
    return {"id": library.save_photo(person, cutout)}


@router.post("/projects/{pid}/library/use/{photo}")
def use_photo(pid: str, photo: str):
    """Put a saved photo and its cutout in this project: no background removal needed."""
    project_or_404(pid)
    d, dest = _photo_dir(photo), project_dir(pid)
    old = tasks.image_slot(pid, "person")
    if old:
        old.unlink()
    src = library.original(d)
    if src:
        shutil.copy(src, dest / ("person" + src.suffix))
    shutil.copy(d / "cutout.png", dest / "cutout.png")
    projects.update(pid, lambda p: p["cutout"].update(done=True))
    return {"used": photo}


@router.post("/library/colors")
def add_color(body: dict = Body(...)):
    return {"colors": bad_request(library.remember_color, body.get("color"))}


@router.delete("/library/colors/{hex_}")
def delete_color(hex_: str):
    return {"colors": library.forget_color("#" + hex_.lstrip("#"))}
