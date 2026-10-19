"""Wizard steps that run as background jobs: subtitles, cutout, thumbnails, Shorts, upload."""
import re
import shutil
from pathlib import Path

from fastapi import APIRouter, Body, HTTPException

from ..models import job as jobs
from ..models import project as projects
from ..models.project import project_dir
from ..services import tasks
from .deps import project_or_404, bad_request, require_youtube

router = APIRouter(prefix="/api")


@router.post("/projects/{pid}/subtitles")
def make_subtitles(pid: str, body: dict = Body(default={})):
    p = project_or_404(pid)
    return jobs.submit("subtitles", pid, tasks.subtitles, pid, body.get("model") or p["subtitles"]["model"])


@router.get("/projects/{pid}/subtitles")
def get_subtitles(pid: str):
    from ..services.subtitles import parse_srt
    project_or_404(pid)
    f = project_dir(pid) / "video.srt"
    return {"cues": parse_srt(f.read_text(encoding="utf-8")) if f.is_file() else []}


@router.put("/projects/{pid}/subtitles")
def save_subtitles(pid: str, body: dict = Body(...)):
    from ..services.subtitles import cues_to_srt
    project_or_404(pid)
    cues = sorted((c for c in body.get("cues", []) if c.get("text", "").strip()), key=lambda c: c["start"])
    for c in cues:
        if not 0 <= float(c["start"]) < float(c["end"]):
            raise HTTPException(400, f"bad cue times: {c}")
    (project_dir(pid) / "video.srt").write_text(cues_to_srt(cues), encoding="utf-8")
    projects.update(pid, lambda p: p["subtitles"].update(done=True))
    return {"cues": len(cues)}


@router.post("/projects/{pid}/cutout")
def make_cutout(pid: str):
    project_or_404(pid)
    if not tasks.image_slot(pid, "person"):
        raise HTTPException(400, "upload a photo of you first")
    return jobs.submit("cutout", pid, tasks.cutout, pid)


@router.get("/templates")
def templates():
    from ..services.thumbnails.templates import FAMILIES, FAMILY_OF, TEMPLATES, THEMES
    return {"templates": [{"name": n, "description": t["description"], "color": t["defaults"].get("color"),
                           "max_chars": t.get("max_chars"), "family": FAMILY_OF[n],
                           "needs": t.get("needs", [])} for n, t in TEMPLATES.items()],
            "families": [{"id": fid, "label": f["label"]} for fid, f in FAMILIES.items()],
            "colors": {n: t["color"] for n, t in THEMES.items()}}


@router.post("/projects/{pid}/thumbnails")
def make_thumbnails(pid: str, body: dict = Body(...)):
    project_or_404(pid)
    title = (body.get("title") or "").strip()
    if not title:
        raise HTTPException(400, "type a title for the thumbnail")
    if not (project_dir(pid) / "cutout.png").is_file():
        raise HTTPException(400, "do the background removal step first")
    from ..services.thumbnails.templates import THEMES
    color = body.get("color") or None
    if color and color not in THEMES and not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
        raise HTTPException(400, f"bad color: {color}")
    if color and color.startswith("#"):  # a custom color: keep it in the channel's saved colors
        from ..models import library
        library.remember_color(color)
    return jobs.submit("thumbnails", pid, tasks.thumbnails, pid, title, color, body.get("templates"),
                       body.get("subtitle") or "")


@router.post("/projects/{pid}/news-images")
def find_news_images(pid: str, body: dict = Body(...)):
    project_or_404(pid)
    news = [n.strip() for n in body.get("news") or [] if n and n.strip()]
    if not news:
        raise HTTPException(400, "add at least one news item")
    titles = body.get("titles") or {}  # cover texts you typed: they win over the ones Claude writes

    def save(p):  # keep the list even if the search fails
        old = {o["text"]: o for o in p["thumbnail"].get("news", [])}
        p["thumbnail"]["news"] = [{**old.get(n, {"text": n, "file": None}),
                                   **({"title": titles[n]} if titles.get(n) else {})} for n in news]
    projects.update(pid, save)
    return jobs.submit("news", pid, tasks.news_images, pid, news, lane="upload")  # network, not CPU


@router.put("/projects/{pid}/news")
def save_news_titles(pid: str, body: dict = Body(...)):
    """Your edits to the magazine cover texts: {"titles": {news text: cover text}}."""
    project_or_404(pid)
    titles = body.get("titles") or {}

    def save(p):
        for n in p["thumbnail"].get("news", []):
            if n["text"] in titles:
                n["title"] = " ".join(str(titles[n["text"]]).split())
    return projects.update(pid, save)["thumbnail"]["news"]


@router.post("/projects/{pid}/thumbnail/choose")
def choose_thumbnail(pid: str, body: dict = Body(...)):
    project_or_404(pid)
    d = project_dir(pid)
    src = d / "thumbs" / f"{body.get('template')}.png"
    if not src.is_file():
        raise HTTPException(400, "render that template first")
    shutil.copy(src, d / "thumb.png")
    return projects.update(pid, lambda p: p["thumbnail"].update(template=body["template"]))


@router.post("/projects/{pid}/shorts")
def add_short(pid: str, body: dict = Body(...)):
    p = project_or_404(pid)
    start, end = float(body.get("start", -1)), float(body.get("end", -1))
    if not 0 <= start < end:
        raise HTTPException(400, "mark a start and an end (end after start)")
    for key in ("face", "game"):
        box = body.get(key)
        if box is not None and (len(box) != 4 or min(box[2:]) < 16):
            raise HTTPException(400, f"{key} box is too small")
    n = max([c["n"] for c in p["shorts"]], default=0) + 1
    clip = {"n": n, "start": round(start, 2), "end": round(end, 2), "face": body.get("face"),
            "game": body.get("game"), "title": body.get("title", ""), "captions": body.get("captions", True),
            "rendered": False, "file": None, "upload": None}
    projects.update(pid, lambda p: p["shorts"].append(clip))
    return {"short": clip, "job": jobs.submit("short", pid, tasks.short, pid, n)}


@router.post("/projects/{pid}/shorts/{n}/render")
def rerender_short(pid: str, n: int):
    p = project_or_404(pid)
    if not any(c["n"] == n for c in p["shorts"]):
        raise HTTPException(404, "short not found")
    return jobs.submit("short", pid, tasks.short, pid, n)


@router.delete("/projects/{pid}/shorts/{n}")
def delete_short(pid: str, n: int):
    project_or_404(pid)
    (project_dir(pid) / "shorts" / f"short_{n}.mp4").unlink(missing_ok=True)
    return projects.update(pid, lambda p: p.update(shorts=[c for c in p["shorts"] if c["n"] != n]))


@router.post("/projects/{pid}/publish")
def publish(pid: str, body: dict = Body(default={})):
    p = project_or_404(pid)
    d = project_dir(pid)
    if not (d / "cutout.png").is_file() or not (d / "thumb.png").is_file():
        raise HTTPException(400, "background removal and thumbnail are required before uploading")
    srt = d / "video.srt" if p["publish"].get("include_subtitles") and (d / "video.srt").is_file() else None
    bad_request(tasks.upload_opts, pid, p["publish"], Path(p["file"]), d / "thumb.png", srt)  # validate now
    dry = bool(body.get("dry_run"))
    require_youtube(dry)
    return jobs.submit("publish", pid, tasks.publish, pid, dry, lane="work" if dry else "upload")


@router.post("/projects/{pid}/shorts/{n}/publish")
def publish_short(pid: str, n: int, body: dict = Body(...)):
    p = project_or_404(pid)
    clip = next((c for c in p["shorts"] if c["n"] == n), None)
    if not clip or not clip.get("rendered"):
        raise HTTPException(400, "render this Short first")
    fields = {k: body.get(k) for k in ("title", "description", "tags", "schedule", "privacy", "playlist")}
    bad_request(tasks.upload_opts, pid, fields, project_dir(pid) / clip["file"], shorts=True)
    dry = bool(body.get("dry_run"))
    require_youtube(dry)
    return jobs.submit("publish_short", pid, tasks.publish_short, pid, n, fields, dry,
                       lane="work" if dry else "upload")


@router.get("/jobs/{job_id}")
def job(job_id: str):
    j = jobs.get(job_id)
    if not j:
        raise HTTPException(404, "job not found")
    return j
