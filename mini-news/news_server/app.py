"""Web app: one page (ui/index.html, a step-by-step wizard) + a small JSON API over the drafts and styles.
Images are drawn by GIMP in background jobs (GET /api/jobs/<id> for progress)."""
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from .paths import CARDS, UI
from .services import drafts, jobs, styles, templates, writer

app = FastAPI(title="mini-news")


def _run(fn, *args, **kw):
    try:
        return fn(*args, **kw)
    except KeyError as e:
        raise HTTPException(404, str(e.args[0]))
    except ValueError as e:
        raise HTTPException(409 if str(e).startswith(drafts.GIMP_EDITED) else 400, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e))


def _url(path, stamp=None):
    return f"/cards/{path.name}?v={int((stamp or time.time()) * 1000)}"


def _view(d):
    jpg, xcf = templates.card_path(d), templates.card_path(d, "xcf")
    return {**d, "x_post": writer.x_post_text(d), "x_length": writer.x_length(d), "x_limit": writer.X_LIMIT,
            "facebook_post": writer.facebook_post_text(d),
            "card": _url(jpg, jpg.stat().st_mtime) if jpg.is_file() else None,
            "xcf": xcf.is_file(), "xcf_mtime": xcf.stat().st_mtime if xcf.is_file() else None,
            "available": templates.available(d),
            "missing": {t: templates.missing(d, t) for t in templates.TEMPLATES if t not in templates.available(d)},
            "all_warnings": drafts.warnings(d)}


@app.get("/")
def index():
    return FileResponse(UI / "index.html")


@app.get("/cards/{name}")
def card(name: str):
    path = CARDS / name
    if path.parent != CARDS or not path.is_file():
        raise HTTPException(404, "no image")
    return FileResponse(path, headers={"Cache-Control": "no-store"})


@app.get("/api/templates")
def list_templates():
    return {"templates": templates.listing(), "categories": templates.CATEGORIES}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    """Progress of a GIMP job; items maps each template to the URL of its image once it's drawn."""
    j = _run(jobs.get, job_id)
    items = {t: (_url(j["paths"][t]) if s == "ok" else None) for t, s in j["items"].items()} if j.get("paths") else {}
    return {"status": j["status"], "done": j["done"], "total": j["total"], "error": j["error"], "items": items}


# ---------------------------------------------------------------- styles

@app.get("/api/styles")
def list_styles():
    return {"styles": styles.all_styles(), "formats": list(styles.FORMATS), "themes": styles.THEMES,
            "default": styles.DEFAULT}


@app.get("/style-assets/{name}")
def style_asset_file(name: str):
    """An uploaded background / logo, for the thumbnails in the Estilo step."""
    path = styles.asset(name)
    if not path:
        raise HTTPException(404, "no file")
    return FileResponse(path)


@app.get("/api/styles/{style_id}")
def get_style(style_id: str):
    return {"id": style_id, "style": _run(styles.load, style_id)}


@app.post("/api/styles")
def new_style(body: dict):
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "give the style a name")
    style_id = _run(styles.create, name, body.get("copy_from") or "default")
    return {"id": style_id, "style": styles.load(style_id)}


@app.put("/api/styles/{style_id}")
def edit_style(style_id: str, body: dict):
    _run(styles.raw, style_id)
    return {"id": style_id, "style": _run(styles.save, style_id, body)}


@app.delete("/api/styles/{style_id}")
def delete_style(style_id: str):
    _run(styles.delete, style_id)
    return {"ok": True}


@app.post("/api/styles/{style_id}/asset")
async def style_asset(style_id: str, kind: str, filename: str, request: Request):
    """Upload a background / logo / font (the raw file as the request body)."""
    data = await request.body()
    if not data or len(data) > 20_000_000:
        raise HTTPException(400, "send a file up to 20 MB")
    return {"id": style_id, "style": _run(styles.save_asset, style_id, kind, filename, data)}


@app.post("/api/styles/{style_id}/previews")
def style_previews(style_id: str, body: dict):
    """Start drawing templates with this style (on a draft, or the sample story): 4 of them, or all 20."""
    _run(styles.raw, style_id)
    d = _run(drafts.load, body["draft_id"]) if body.get("draft_id") else templates.sample()
    which = [t for t in (list(templates.TEMPLATES) if body.get("all") else
                         ["breaking", "photo", "quote", "numbers"]) if t in templates.available(d)]
    prefix = f"_style-{style_id}-{d['id']}"

    def work(job):
        job["total"] = len(which)
        job["paths"] = {t: CARDS / f"{prefix}-{t}.jpg" for t in which}

        def done(t, ok):
            job["items"][t] = "ok" if ok else "failed"
            job["done"] += 1
        templates.style_previews(style_id, d, which, done)

    return {"job": jobs.start(work)}


# ---------------------------------------------------------------- drafts

@app.get("/api/drafts")
def list_drafts():
    return [_view(d) for d in drafts.all_drafts()]


@app.get("/api/drafts/{draft_id}")
def get_draft(draft_id: str):
    return _view(_run(drafts.load, draft_id))


@app.post("/api/drafts")
def new_draft(body: dict):
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "paste a link or write a topic")
    return _view(_run(drafts.create, text, body.get("take") or "", None, lambda msg: None))


@app.put("/api/drafts/{draft_id}")
def edit(draft_id: str, body: dict, force: bool = False):
    """409 when the image was edited in GIMP: send again with ?force=true to redraw anyway."""
    return _view(_run(drafts.update, draft_id, body, force))


@app.post("/api/drafts/{draft_id}/previews")
def previews(draft_id: str):
    """Start drawing every template this draft can use (one GIMP session); poll /api/jobs/<job>."""
    d = _run(drafts.load, draft_id)
    paths = {t: templates.preview_path(d, t) for t in templates.available(d)}

    def work(job):
        job["paths"] = paths
        return drafts.previews(job, draft_id)

    return {"job": jobs.start(work)}


@app.post("/api/drafts/{draft_id}/photo")
async def photo(draft_id: str, request: Request, force: bool = False):
    data = await request.body()   # the raw image file (the page sends it as the request body)
    if not data or len(data) > 20_000_000:
        raise HTTPException(400, "send an image up to 20 MB")
    return _view(_run(drafts.set_photo, draft_id, data, force))


@app.put("/api/drafts/{draft_id}/style")
def draft_style(draft_id: str, body: dict, force: bool = False):
    """Customize THIS draft's own style and draw it again (other drafts and the saved styles don't change)."""
    return _view(_run(drafts.set_style, draft_id, body, force))


@app.post("/api/drafts/{draft_id}/style-asset")
async def draft_style_asset(draft_id: str, kind: str, filename: str, request: Request):
    """Upload a background / logo / font for this draft's style only."""
    data = await request.body()
    if not data or len(data) > 20_000_000:
        raise HTTPException(400, "send a file up to 20 MB")
    return _view(_run(drafts.style_asset, draft_id, kind, filename, data))


@app.post("/api/drafts/{draft_id}/style/reset")
def draft_style_reset(draft_id: str, force: bool = False):
    """Back to the default style (drops this draft's customizations)."""
    return _view(_run(drafts.style_reset, draft_id, force))


@app.post("/api/drafts/{draft_id}/style/save-default")
def draft_style_save_default(draft_id: str, body: dict = None):
    """This draft's style (or body["style"], the one on screen) becomes the default for NEW drafts."""
    return _view(_run(drafts.style_save_default, draft_id, (body or {}).get("style")))


@app.post("/api/drafts/{draft_id}/style/save-as")
def draft_style_save_as(draft_id: str, body: dict):
    """Keep this draft's style as a named saved style, to reuse in other drafts."""
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "give the style a name")
    d = _run(drafts.load, draft_id)
    style_id = _run(styles.create, name)
    _run(styles.save, style_id, {**(body.get("style") or d["style_data"]), "name": name})
    return {"id": style_id}


@app.post("/api/styles/reset-default")
def reset_default_style():
    """The default style back to the original look (blue + silver)."""
    return {"style": styles.reset_default()}


@app.post("/api/drafts/{draft_id}/render")
def redraw(draft_id: str, force: bool = False):
    """Draw the draft's image again with GIMP (after editing its style). 409 over GIMP edits, like PUT."""
    return _view(_run(drafts.redraw, draft_id, force))


@app.post("/api/drafts/{draft_id}/gimp/open")
def gimp_open(draft_id: str):
    return _view(_run(drafts.gimp_open, draft_id))


@app.post("/api/drafts/{draft_id}/gimp/apply")
def gimp_apply(draft_id: str):
    return _view(_run(drafts.gimp_apply, draft_id))


@app.post("/api/drafts/{draft_id}/approve")
def approve(draft_id: str):
    return _view(_run(drafts.approve, draft_id))


@app.post("/api/drafts/{draft_id}/publish")
def publish(draft_id: str, body: dict):
    only = body.get("only") or None
    if only not in (None, "x", "facebook"):
        raise HTTPException(400, "only: x or facebook")
    if body.get("dry_run"):
        return _run(drafts.publish, draft_id, only, True)
    return _view(_run(drafts.publish, draft_id, only))


@app.delete("/api/drafts/{draft_id}")
def delete(draft_id: str):
    _run(drafts.delete, draft_id)
    return {"ok": True}
