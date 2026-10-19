"""Recordings in the OBS folder and the per-recording project state (work/channels/<channel>/<id>/project.json)."""
import json
import re
import subprocess
import threading
import time
from pathlib import Path

from . import channel, settings

STILL_WRITING = 15  # seconds since last change: OBS is probably still recording
_lock = threading.Lock()
_probe_cache = {}


def project_id(path):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", Path(path).stem).strip("_") or "video"


def project_dir(pid):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", pid):
        raise KeyError(pid)
    return channel.work_dir() / pid


def duration(path):
    """Seconds (ffprobe), cached by path + mtime + size."""
    st = Path(path).stat()
    key = (str(path), st.st_mtime, st.st_size)
    if key not in _probe_cache:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                              str(path)], capture_output=True, text=True).stdout.strip()
        try:
            _probe_cache[key] = float(out)
        except ValueError:
            _probe_cache[key] = None
    return _probe_cache[key]


def watch_folder():
    return Path(settings.load_shared()["watch_folder"]).expanduser()


def recording_path(name):
    """A file directly inside the watch folder (no path tricks)."""
    folder = watch_folder()
    path = (folder / name).resolve()
    if path.parent != folder.resolve() or not path.is_file() or path.suffix.lower() not in settings.VIDEO_EXTS:
        raise KeyError(name)
    return path


def scan_recordings():
    folder = watch_folder()
    if not folder.is_dir():
        return []
    out, now = [], time.time()
    me = channel.get()["id"]
    others = [c for c in channel.all_channels() if c["id"] != me]
    for f in sorted(folder.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not f.is_file() or f.suffix.lower() not in settings.VIDEO_EXTS:
            continue
        st = f.stat()
        pid = project_id(f)
        project = load(pid)
        if now - st.st_mtime < STILL_WRITING:
            status = "recording"
        elif project:
            status = project["status"]
        else:
            status = "new"
        elsewhere = [c["name"] for c in others if (channel.channel_dir(c["id"]) / pid / "project.json").is_file()]
        out.append({"name": f.name, "project": pid, "status": status, "size": st.st_size, "mtime": st.st_mtime,
                    "elsewhere": elsewhere,
                    "duration": None if status == "recording" else duration(f)})
    return out


def new_project(path):
    path = Path(path)
    return {
        "id": project_id(path), "file": str(path), "name": path.name, "created": time.time(), "status": "new",
        "duration": duration(path),
        "subtitles": {"enabled": False, "model": settings.load()["whisper_model"], "done": False},
        "shorts": [],
        "cutout": {"done": False},
        "thumbnail": {"title": "", "subtitle": "", "color": None, "rendered": [], "template": None, "news": []},
        "publish": {"title": "", "description": "", "tags": settings.load()["tags"],
                    "privacy": settings.load()["privacy"], "schedule": None, "playlist": "",
                    "include_subtitles": True, "result": None},
    }


def load(pid):
    return load_from(project_dir(pid))  # KeyError for a bad id, NoChannel without a channel


def load_from(d):
    f = Path(d) / "project.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else None


def save(project):
    with _lock:
        d = project_dir(project["id"])
        d.mkdir(parents=True, exist_ok=True)
        tmp = d / "project.json.tmp"
        tmp.write_text(json.dumps(project, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(d / "project.json")
    return project


def update(pid, fn):
    """Load, change with fn(project), save. Safe to call from job threads."""
    with _lock:
        project = load(pid)
        fn(project)
    return save(project)


def open_project(name):
    path = recording_path(name)
    return load(project_id(path)) or save(new_project(path))
