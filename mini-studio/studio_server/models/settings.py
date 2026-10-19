"""Studio settings: the shared ones in work/settings.json (the OBS folder), the upload defaults per channel
(work/channels/<id>/channel.json). load() / save() join and split them, so callers see one dict."""
import json
import os
from pathlib import Path

from ..paths import WORK
from . import channel

SETTINGS_FILE = WORK / "settings.json"
VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".flv", ".webm", ".ts", ".m4v"}

SHARED = {
    "watch_folder": str(Path.home() / "Videos"),   # where OBS saves recordings (all channels)
}
DEFAULTS = {**SHARED, **channel.DEFAULTS}


def load_shared():
    channel.migrate()  # the first run moves the old single-channel settings into a channel
    data = dict(SHARED)
    if SETTINGS_FILE.is_file():
        data.update({k: v for k, v in json.loads(SETTINGS_FILE.read_text(encoding="utf-8")).items() if k in SHARED})
    if os.environ.get("STUDIO_WATCH"):  # override for testing
        data["watch_folder"] = os.environ["STUDIO_WATCH"]
    return data


def load():
    """Shared settings + the current channel's upload defaults (NoChannel if none is chosen)."""
    c = channel.get()
    return {**load_shared(), **{k: c[k] for k in channel.DEFAULTS}}


def save(changes):
    shared = {**load_shared(), **{k: v for k, v in changes.items() if k in SHARED}}
    if not Path(shared["watch_folder"]).expanduser().is_dir():
        raise ValueError(f"folder not found: {shared['watch_folder']}")
    WORK.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(shared, indent=2, ensure_ascii=False), encoding="utf-8")
    channel.update(channel.get()["id"], {k: v for k, v in changes.items() if k in channel.DEFAULTS})
    return load()
