"""Channels: each one has its own projects, YouTube login and upload defaults (work/channels/<id>/channel.json).

The channel a request works on comes from the X-Channel header (set by a middleware in app.py) and lives in a
ContextVar, so background jobs (copied context, see job.py) keep using the channel that started them.
The OBS recording folder is shared by every channel (work/settings.json).
"""
import contextvars
import json
import re
import shutil
import threading
import time
import unicodedata

from ..paths import SECRETS, WORK

CHANNELS = WORK / "channels"
TOKENS = SECRETS / "channels"
COLORS = ["#c00fc9", "#e53935", "#fb8c00", "#f6bf26", "#2ba640", "#039be5", "#3f51b5", "#8e24aa"]
# upload defaults kept per channel (the rest of settings.json is shared)
DEFAULTS = {
    "privacy": "private",
    "publish_time": "18:00",
    "description_template": "{title}\n\n🔔 Se inscreva no canal e ative o sininho!\n\n#games",
    "tags": "games, gameplay",
    "whisper_model": "small",
}

current = contextvars.ContextVar("channel", default=None)
_lock = threading.RLock()


class NoChannel(LookupError):
    """No channel chosen (missing X-Channel), or it doesn't exist."""


def slug(name):
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "channel"


def channel_dir(cid):
    if not re.fullmatch(r"[a-z0-9_]+", cid or ""):
        raise NoChannel(cid)
    return CHANNELS / cid


def load(cid):
    f = channel_dir(cid) / "channel.json"
    if not f.is_file():
        raise NoChannel(cid)
    return {**DEFAULTS, **json.loads(f.read_text(encoding="utf-8"))}


def save(data):
    d = channel_dir(data["id"])
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "channel.json.tmp"
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(d / "channel.json")
    return data


def all_channels():
    migrate()
    out = []
    for f in sorted(CHANNELS.glob("*/channel.json")):
        out.append(load(f.parent.name))
    return sorted(out, key=lambda c: c.get("created", 0))


def summary(c):
    projects = sum(1 for p in channel_dir(c["id"]).glob("*/project.json"))
    return {"id": c["id"], "name": c["name"], "color": c["color"], "connected": token_path(c["id"]).is_file(),
            "projects": projects}


def create(name, color=None):
    name = " ".join(str(name or "").split())
    if not name or len(name) > 40:
        raise ValueError("channel name: 1-40 characters")
    with _lock:
        base = cid = slug(name)
        n = 2
        while (CHANNELS / cid).exists():
            cid, n = f"{base}_{n}", n + 1
        used = {c["color"] for c in all_channels()}
        color = color or next((c for c in COLORS if c not in used), COLORS[0])
        return save({"id": cid, "name": name, "color": check_color(color), "created": time.time(), **DEFAULTS})


def update(cid, changes):
    data = load(cid)
    if "name" in changes:
        name = " ".join(str(changes["name"] or "").split())
        if not name or len(name) > 40:
            raise ValueError("channel name: 1-40 characters")
        data["name"] = name
    if "color" in changes:
        data["color"] = check_color(changes["color"])
    data.update({k: v for k, v in changes.items() if k in DEFAULTS})
    return save(data)


def delete(cid):
    """Delete the channel's projects and YouTube login. The recordings themselves are never touched."""
    load(cid)
    if len(all_channels()) <= 1:
        raise ValueError("can't delete the last channel")
    d = channel_dir(cid).resolve()
    if d.parent != CHANNELS.resolve():  # safety: only ever delete inside work/channels/
        raise ValueError("refusing to delete outside the channels folder")
    shutil.rmtree(d)
    t = TOKENS / cid
    if t.is_dir() and t.resolve().parent == TOKENS.resolve():
        shutil.rmtree(t)


def check_color(color):
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(color or "")):
        raise ValueError("color must look like #c00fc9")
    return color.lower()


# ---------------------------------------------------------------- the channel of this request / job

def get():
    """The current channel's data; NoChannel when none was chosen."""
    cid = current.get()
    if not cid:
        raise NoChannel(None)
    return load(cid)


def work_dir():
    """Where the current channel's projects live."""
    return channel_dir(get()["id"])


def token_path(cid=None):
    return TOKENS / (cid or get()["id"]) / "token.json"


# ---------------------------------------------------------------- one-time move from the single-channel layout

def migrate():
    """First run with channels: move work/<project>/, secrets/token.json and the upload defaults
    into a "CASA NOVA" channel."""
    if CHANNELS.is_dir():
        return
    with _lock:
        if CHANNELS.is_dir():
            return
        WORK.mkdir(parents=True, exist_ok=True)
        old = {}
        settings_file = WORK / "settings.json"
        if settings_file.is_file():
            old = json.loads(settings_file.read_text(encoding="utf-8"))
        CHANNELS.mkdir()
        c = save({"id": "casa_nova", "name": "CASA NOVA", "color": COLORS[0], "created": time.time(),
                  **{k: old.get(k, v) for k, v in DEFAULTS.items()}})
        moved = []
        for d in WORK.iterdir():
            if d.is_dir() and d != CHANNELS and (d / "project.json").is_file():
                d.rename(channel_dir(c["id"]) / d.name)
                moved.append(d.name)
        token = SECRETS / "token.json"
        if token.is_file():
            token_path(c["id"]).parent.mkdir(parents=True, exist_ok=True)
            token.rename(token_path(c["id"]))
            moved.append("secrets/token.json")
        if old:  # the shared file keeps only the shared settings
            settings_file.write_text(json.dumps({k: v for k, v in old.items() if k not in DEFAULTS},
                                                indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"channels: created \"{c['name']}\" and moved into it: {', '.join(moved) or 'nothing'}")
