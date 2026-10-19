"""The work behind each wizard step. Every function runs as a background job: fn(report, pid, ...)."""
import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

from ..models import project as projects
from ..models.project import project_dir

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def video_of(pid):
    return Path(projects.load(pid)["file"])


def image_slot(pid, slot):
    """Path of an uploaded image (person / bg / art / art2), whatever its extension."""
    for f in project_dir(pid).glob(slot + ".*"):
        if f.suffix.lower() in IMAGE_EXTS:
            return f
    return None


def grab_frame(video, t, out=None, width=None):
    """One video frame at t seconds as JPEG: bytes, or written to `out`."""
    cmd = ["ffmpeg", "-v", "error", "-ss", str(max(0.0, t)), "-i", str(video), "-frames:v", "1"]
    if width:
        cmd += ["-vf", f"scale={width}:-2"]
    cmd += ["-q:v", "3", "-f", "image2", "-c:v", "mjpeg", str(out) if out else "pipe:1"]
    if out:
        cmd.insert(1, "-y")
    data = subprocess.run(cmd, capture_output=True, check=True).stdout
    return None if out else data


# ---------------------------------------------------------------- subtitles

def subtitles(report, pid, model):
    from .subtitles import cues_from_words, cues_to_srt, transcribe

    d = project_dir(pid)
    report(0, f"transcribing with whisper {model}")
    words = transcribe(video_of(pid), model=model, report=report)
    (d / "video.words.json").write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
    cues = cues_from_words(words)
    (d / "video.srt").write_text(cues_to_srt(cues), encoding="utf-8")
    projects.update(pid, lambda p: p["subtitles"].update(done=True, model=model))
    return {"cues": len(cues), "words": len(words)}


# ---------------------------------------------------------------- cutout

def cutout(report, pid):
    from .cutout import MODEL, remove_background

    src = image_slot(pid, "person")
    if not src:
        raise ValueError("upload a photo of you first")
    report(None, f"removing the background with AI ({MODEL}, ~15 s)")
    remove_background(src, project_dir(pid) / "cutout.png")
    projects.update(pid, lambda p: p["cutout"].update(done=True))
    return {"file": "cutout.png"}


# ---------------------------------------------------------------- thumbnails

def thumbnails(report, pid, title, color, templates, subtitle=""):
    from .thumbnails.gimp_runner import run_jobs
    from .thumbnails.make_thumb import DEFAULT_BG, DEFAULT_LOGO
    from .thumbnails.templates import TEMPLATES
    from .thumbnails.thumb_job import build_job

    d = project_dir(pid)
    if not (d / "cutout.png").is_file():
        raise ValueError("do the background removal step first")
    names = [t for t in (templates or TEMPLATES) if t in TEMPLATES]
    art, art2, bg = image_slot(pid, "art"), image_slot(pid, "art2"), image_slot(pid, "bg")
    news = projects.load(pid)["thumbnail"].get("news", [])
    args = SimpleNamespace(title=title, subtitle=subtitle.strip() or None, color=color or None, bg=str(bg or DEFAULT_BG),
                           person=str(d / "cutout.png"), art=str(art) if art else None,
                           art2=str(art2) if art2 else None, logo=str(DEFAULT_LOGO), no_logo=False,
                           magazines=[{"title": n.get("title") or n["text"], "path": str(d / "news" / n["file"])}
                                      for n in news if n.get("file")])
    (d / "thumbs").mkdir(exist_ok=True)
    report(None, f"rendering {len(names)} thumbnails in GIMP")
    run_jobs([build_job(n, args, d / "thumbs" / n) for n in names])

    def save(p):
        t = p["thumbnail"]
        rendered = set(names)
        if (t["title"], t["color"], t.get("subtitle", "")) == (title, color, subtitle):  # same text: keep the other tabs' renders
            rendered |= set(t["rendered"])
        t.update(title=title, color=color, subtitle=subtitle, rendered=[n for n in TEMPLATES if n in rendered])
        if p["thumbnail"]["template"] in names:  # re-copy the chosen one so it matches the new render
            shutil.copy(d / "thumbs" / (p["thumbnail"]["template"] + ".png"), d / "thumb.png")
    projects.update(pid, save)
    return {"rendered": names}


def news_images(report, pid, news):
    """Claude Code finds a picture per news headline (for the collage magazines)."""
    from .news_images import find_images

    found = find_images(news, project_dir(pid) / "news", report)

    def save(p):
        mine = {n["text"]: n.get("title") for n in p["thumbnail"].get("news", [])}
        for n in found:  # a cover text you already have (maybe edited) wins over Claude's
            n["title"] = mine.get(n["text"]) or n["title"]
        p["thumbnail"]["news"] = found
    projects.update(pid, save)
    missing = [n["text"] for n in found if not n["file"]]
    return {"found": len(found) - len(missing), "missing": missing}


# ---------------------------------------------------------------- shorts

def short(report, pid, n):
    from .shorts import make_short

    d = project_dir(pid)
    clip = next(c for c in projects.load(pid)["shorts"] if c["n"] == n)
    start, end = clip["start"], clip["end"]
    words = []
    if clip.get("captions", True):
        wf = d / "video.words.json"
        if wf.is_file():
            words = json.loads(wf.read_text(encoding="utf-8"))
        else:
            from .subtitles import transcribe
            report(0, "transcribing the clip for captions")
            words = transcribe(video_of(pid), model=projects.load(pid)["subtitles"]["model"], start=start, end=end)
        words = [w for w in words if w["start"] >= start - 0.05 and w["end"] <= end + 0.3]
    (d / "shorts").mkdir(exist_ok=True)
    out = d / "shorts" / f"short_{n}.mp4"
    report(0, "rendering the Short")
    make_short(video_of(pid), start, end, out, face=clip.get("face"), game=clip.get("game"),
               title=clip.get("title") or None, words=words, report=report)

    def save(p):
        for c in p["shorts"]:
            if c["n"] == n:
                c.update(file=f"shorts/short_{n}.mp4", rendered=True)
    projects.update(pid, save)
    return {"file": f"shorts/short_{n}.mp4"}


# ---------------------------------------------------------------- upload

def upload_opts(pid, fields, video, thumb=None, srt=None, shorts=False):
    from .youtube_upload import build_opts

    opts = build_opts(video, sidecar=False, shorts=shorts, thumb=str(thumb) if thumb else None,
                      **{k: fields.get(k) or None for k in ("title", "description", "tags", "schedule",
                                                            "privacy", "playlist")})
    opts.pop("srt", None)  # never pick up a stray .srt next to the recording
    if srt:
        opts["srt"] = str(srt)
    return opts


def publish(report, pid, dry_run=False):
    from .youtube_upload import upload, video_body

    p, d = projects.load(pid), project_dir(pid)
    pub = p["publish"]
    if not (d / "thumb.png").is_file():
        raise ValueError("choose a thumbnail first")
    srt = d / "video.srt" if pub.get("include_subtitles") and (d / "video.srt").is_file() else None
    opts = upload_opts(pid, pub, video_of(pid), d / "thumb.png", srt)
    if dry_run:
        return {"dry_run": True, "body": video_body(opts), "thumbnail": opts.get("thumb"), "subtitles": opts.get("srt")}
    result = upload(str(video_of(pid)), opts, report)
    projects.update(pid, lambda p: (p["publish"].update(result=result), p.update(status="uploaded")))
    return result


def publish_short(report, pid, n, fields, dry_run=False):
    from .youtube_upload import upload, video_body

    d = project_dir(pid)
    clip = next(c for c in projects.load(pid)["shorts"] if c["n"] == n)
    if not clip.get("rendered"):
        raise ValueError("render this Short first")
    opts = upload_opts(pid, fields, d / clip["file"], shorts=True)
    if dry_run:
        return {"dry_run": True, "body": video_body(opts)}
    result = upload(str(d / clip["file"]), opts, report)

    def save(p):
        for c in p["shorts"]:
            if c["n"] == n:
                c["upload"] = {**fields, "result": result}
    projects.update(pid, save)
    return result


def youtube_connect(report):
    from .youtube_upload import youtube_client

    report(None, "waiting for the Google login in your browser")
    youtube_client()
    return {"connected": True}
