"""Drafts on disk: work/drafts/<id>.json. Status: draft -> approved -> published (or failed, to retry).

Nothing is ever published unless its status is "approved": you read and approve every post.
`step` remembers where the wizard was (1 source, 2 template, 3 style, 4 text, 5 preview, 6 publish)."""
import json
import re
import shutil
import time
import uuid
from io import BytesIO

from ..paths import CARDS, DRAFTS, PHOTOS
from . import source, styles, templates, writer
from .gimp import runner

EDITABLE = ("headline", "x_text", "facebook_text", "take", "source_name", "source_url", "hashtags", "kicker",
            "subhead", "quote", "numbers", "points", "question", "template", "step", "style")
IMAGE_FIELDS = ("headline", "source_name", "kicker", "subhead", "quote", "numbers", "points", "question", "take",
                "style")   # changing these redraws the image (template changes reuse the preview when it's current)
PHOTO_WARNING = "a foto veio da matéria e tem direitos autorais: prefira enviar uma foto sua ou de banco gratuito"
GIMP_EDITED = "GIMP_EDITED"   # error prefix: the page asks before redrawing over your GIMP edits
DEFAULTS = writer.Draft.model_construct().model_dump()   # fields older drafts may not have yet


def _path(draft_id):
    p = DRAFTS / f"{draft_id}.json"
    if not p.is_file():
        raise KeyError(f"no draft {draft_id!r}")
    return p


def load(draft_id):
    d = {"step": 2, "style": "default", "rev": 0, "previews_rev": -1, "gimp_edited": False, **DEFAULTS,
         **json.loads(_path(draft_id).read_text(encoding="utf-8"))}
    if "style_data" not in d:   # drafts from before each draft had its own copy of the style
        d["style_data"] = styles.load(d["style"])
    return d


def save(d):
    DRAFTS.mkdir(parents=True, exist_ok=True)
    d["updated"] = time.time()
    (DRAFTS / f"{d['id']}.json").write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    return d


def all_drafts():
    if not DRAFTS.is_dir():
        return []
    return sorted((load(p.stem) for p in DRAFTS.glob("*.json")), key=lambda d: d["created"], reverse=True)


def create(text, take="", template=None, report=print, style="default"):
    """A link or a topic -> a new draft (status "draft") with the article photo (if any) and its image."""
    text = text.strip()
    draft_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    photo = ""
    if source.is_url(text):
        report(f"reading {text}")
        art = source.fetch(text)
        src = f"Veículo: {art['site']}\nLink: {art['url']}\nTítulo: {art['title']}\nData: {art['date']}\n\n{art['text']}"
        if source.download_image(art["image"], PHOTOS / f"{draft_id}.jpg"):
            photo = "article"
        report("Claude Code is writing the post")
        draft = writer.write(src, take).model_dump()
    else:
        report(f"Claude Code is searching the web and writing: {text}")
        draft = writer.write_topic(text, take).model_dump()
    d = {"id": draft_id, "input": text, "status": "draft", "step": 2, "style": style, "rev": 0, "previews_rev": -1,
         "gimp_edited": False, "created": time.time(), **draft, "photo": photo, "published": {},
         "style_data": styles.load(style)}   # its own copy: customizing this draft changes nothing else
    if template:
        d["template"] = template
    if d["template"] not in templates.available(d):
        d["template"] = "breaking"
    report("GIMP is drawing the image")
    templates.render(d)
    return save(d)


def _guard_gimp(d, force):
    """Redrawing replaces the .xcf you edited in GIMP: refuse unless forced, and keep a backup."""
    if not d.get("gimp_edited"):
        return
    if not force:
        raise ValueError(f"{GIMP_EDITED}: this image was edited in GIMP; redrawing it replaces those edits")
    xcf = templates.card_path(d, "xcf")
    if xcf.is_file():
        shutil.copy(xcf, xcf.with_suffix(".xcf.bak"))
    d["gimp_edited"] = False


def update(draft_id, fields, force=False):
    """Edit the draft. An edited approved post goes back to "draft", to be approved again.
    force=True: redraw even over edits made in GIMP (the old .xcf is kept as <id>.xcf.bak)."""
    d = load(draft_id)
    if d["status"] == "published":
        raise ValueError("already published: create a new draft instead")
    if fields.get("style"):
        styles.raw(fields["style"])   # KeyError (-> 404) for a style that doesn't exist
    if fields.get("template") and fields["template"] not in templates.available({**d, **fields}):
        raise ValueError(f"template {fields['template']!r} needs data this draft doesn't have")
    changed = [k for k in EDITABLE if k in fields and fields[k] != d.get(k)]
    redraw = set(changed) & set(IMAGE_FIELDS)
    if redraw or "template" in changed:
        _guard_gimp(d, force)
    for k in changed:
        d[k] = fields[k]
    if "style" in changed:   # picking a saved style copies it into this draft (replacing its customizations)
        d["style_data"] = styles.load(d["style"])
    if d["status"] == "approved" and set(changed) - {"step"}:
        d["status"] = "draft"
    if redraw:
        d["rev"] += 1
        templates.render(d)
    elif "template" in changed:   # a fresh preview of that template is the same image: no new GIMP run
        if d["previews_rev"] != d["rev"] or not templates.use_preview(d, d["template"]):
            templates.render(d)
    return save(d)


def set_photo(draft_id, data, force=False):
    """Your own photo (bytes of a JPEG / PNG / WebP) for the photo templates."""
    from PIL import Image

    d = load(draft_id)
    if d["status"] == "published":
        raise ValueError("already published: create a new draft instead")
    try:
        img = Image.open(BytesIO(data)).convert("RGB")
    except OSError:
        raise ValueError("that file isn't an image")
    _guard_gimp(d, force)
    PHOTOS.mkdir(parents=True, exist_ok=True)
    img.save(PHOTOS / f"{d['id']}.jpg", quality=92)
    d["photo"] = "upload"
    d["rev"] += 1
    if d["status"] == "approved":
        d["status"] = "draft"
    templates.render(d)
    return save(d)


def previews(job, draft_id):
    """(Background job) every template this draft has the data for, in one GIMP session.
    job["items"][template] = "ok" / "failed" as each one is done."""
    d = load(draft_id)
    which = templates.available(d)
    job["total"], rev = len(which), d["rev"]
    if d["previews_rev"] == rev and all(templates.preview_path(d, t).is_file() for t in which):
        job["items"] = {t: "ok" for t in which}   # nothing changed since the last previews: reuse them
        job["done"] = len(which)
        return {"draft": draft_id, "reused": True}

    def done(t, ok):
        job["items"][t] = "ok" if ok else "failed"
        job["done"] += 1

    templates.render_many(d, which, on_done=done)
    d = load(draft_id)
    if d["rev"] == rev:   # still current: choosing a template can reuse these images
        d["previews_rev"] = rev
        save(d)
    return {"draft": draft_id}


def set_style(draft_id, data, force=False):
    """Customize this draft's own style (nothing else changes) and draw its image again."""
    d = load(draft_id)
    if d["status"] == "published":
        raise ValueError("already published: create a new draft instead")
    data = styles.validate(data)
    _guard_gimp(d, force)
    d["style_data"] = data
    d["rev"] += 1
    if d["status"] == "approved":
        d["status"] = "draft"
    templates.render(d)
    return save(d)


def style_asset(draft_id, kind, filename, data):
    """Upload a background / logo / font for this draft's style only (drawn on the next render)."""
    d = load(draft_id)
    if d["status"] == "published":
        raise ValueError("already published: create a new draft instead")
    d["style_data"] = styles.add_asset(styles.validate(d["style_data"]), f"draft-{d['id']}", kind, filename, data)
    return save(d)


def style_reset(draft_id, force=False):
    """Back to the default style: throws away this draft's customizations and draws it again."""
    d = load(draft_id)
    d["style"] = "default"
    return set_style(draft_id, styles.load("default"), force) if d["status"] != "published" else d


def style_save_default(draft_id, data=None):
    """Make this draft's style (or `data`, the one on screen) the default: every NEW draft starts with it.
    Existing drafts keep theirs; nothing is redrawn."""
    d = load(draft_id)
    data = styles.validate(data or d["style_data"])
    data["name"] = styles.load("default")["name"]
    styles.save("default", data)
    return d


def redraw(draft_id, force=False):
    """Draw the draft's image again (after its style changed). Asks first over GIMP edits, like update()."""
    d = load(draft_id)
    if d["status"] == "published":
        raise ValueError("already published: create a new draft instead")
    _guard_gimp(d, force)
    d["rev"] += 1
    if d["status"] == "approved":
        d["status"] = "draft"
    templates.render(d)
    return save(d)


def gimp_open(draft_id):
    """Open the draft's .xcf in the GIMP app to fix it by hand. Then save it (Ctrl+S) and "use the GIMP version"."""
    d = load(draft_id)
    if d["status"] == "published":
        raise ValueError("already published: create a new draft instead")
    xcf = templates.card_path(d, "xcf")
    if not xcf.is_file():
        templates.render(d)
    if not d.get("gimp_edited"):
        shutil.copy(xcf, xcf.with_suffix(".xcf.orig"))   # how it was before your edits
    d["gimp_edited"], d["gimp_opened"] = True, time.time()
    runner.open_in_gimp(xcf)
    return save(d)


def gimp_apply(draft_id):
    """Your saved .xcf -> the image that gets published (<id>.jpg)."""
    d = load(draft_id)
    if d["status"] == "published":
        raise ValueError("already published: create a new draft instead")
    xcf = templates.card_path(d, "xcf")
    if not xcf.is_file():
        raise ValueError("no .xcf for this draft yet")
    templates.export_xcf(d)
    d["gimp_edited"], d["gimp_applied"], d["xcf_saved"] = True, time.time(), xcf.stat().st_mtime
    if d["status"] == "approved":
        d["status"] = "draft"
    return save(d)


def warnings(d):
    w = list(d.get("warnings", []))
    if "photo" in templates.TEMPLATES[d.get("template", "breaking")].NEEDS and d.get("photo") == "article":
        w.append(PHOTO_WARNING)
    return w


def approve(draft_id):
    d = load(draft_id)
    if re.search(r"\[[^\]]+\]", d.get("take", "")):
        raise ValueError("your opinion still has Claude's [suggestion]: rewrite it or clear it")
    if writer.x_length(d) > writer.X_LIMIT:
        raise ValueError(f"the X post is {writer.x_length(d)} characters with the link (max {writer.X_LIMIT})")
    if not templates.card_path(d).is_file():
        templates.render(d)
    xcf = templates.card_path(d, "xcf")
    if d.get("gimp_edited") and xcf.is_file() and xcf.stat().st_mtime > d.get("xcf_saved", 0):
        templates.export_xcf(d)   # you saved in GIMP but didn't click "use the GIMP version": use it now
        d["xcf_saved"] = xcf.stat().st_mtime
    if d["status"] in ("draft", "failed"):
        d["status"] = "approved"
    d["step"] = 6
    return save(d)


def delete(draft_id):
    _path(draft_id).unlink()
    for f in [*CARDS.glob(f"{draft_id}*"), PHOTOS / f"{draft_id}.jpg"]:
        f.unlink(missing_ok=True)


def publish(draft_id, only=None, dry_run=False):
    """Post an approved draft. only: "x" or "facebook". Each platform is posted once, so a retry after
    a failure skips the one that already worked."""
    from . import fb_post, x_post

    d = load(draft_id)
    if d["status"] not in ("approved", "failed"):
        raise ValueError(f"draft is {d['status']!r}: approve it first")
    image = templates.card_path(d)
    targets = {"x": lambda: x_post.post(writer.x_post_text(d), image, dry_run),
               "facebook": lambda: fb_post.post(writer.facebook_post_text(d), image, dry_run)}
    errors = {}
    for name, send in targets.items():
        if (only and name != only) or name in d["published"]:
            continue
        try:
            result = send()
            if not dry_run:
                d["published"][name] = result
        except Exception as e:  # keep going: one platform failing must not block the other
            errors[name] = str(e)
    if dry_run:
        return {"dry_run": True, "image": str(image), "errors": errors}
    d["errors"] = errors
    if all(n in d["published"] for n in targets):
        d["status"] = "published"
    elif errors:
        d["status"] = "failed"   # approve-able again: a retry posts only to the platform that failed
    return save(d)
