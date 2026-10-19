"""The channel's library, reused across projects: photos of you with their background already removed
(work/channels/<id>/library/photos/<photo id>/photo.<ext> + cutout.png) and custom thumbnail colors
("thumb_colors" in channel.json, most recent first)."""
import hashlib
import re
import shutil

from . import channel

MAX_COLORS = 12


def photos_dir():
    return channel.work_dir() / "library" / "photos"


def photo_id(path):
    """Same picture -> same id, so saving it twice keeps one copy."""
    return hashlib.sha1(path.read_bytes()).hexdigest()[:12]


def photo_dir(pid):
    if not re.fullmatch(r"[0-9a-f]{12}", pid or ""):
        raise KeyError(pid)
    d = photos_dir() / pid
    if not (d / "cutout.png").is_file():
        raise KeyError(pid)
    return d


def original(d):
    return next((f for f in d.glob("photo.*")), None)


def photos():
    """Saved photos, newest first."""
    d = photos_dir()
    found = [p for p in d.glob("*/cutout.png")] if d.is_dir() else []
    return [{"id": f.parent.name, "photo": original(f.parent).name if original(f.parent) else None}
            for f in sorted(found, key=lambda f: f.stat().st_mtime, reverse=True)]


def save_photo(photo, cutout):
    """Keep a photo and its cutout for later projects; returns its id."""
    pid = photo_id(photo)
    d = photos_dir() / pid
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy(photo, d / ("photo" + photo.suffix.lower()))
    shutil.copy(cutout, d / "cutout.png")
    return pid


def delete_photo(pid):
    shutil.rmtree(photo_dir(pid))


def colors():
    return channel.get().get("thumb_colors", [])


def remember_color(color):
    """Put a custom color first in the saved list (no duplicates, the oldest ones drop off)."""
    color = channel.check_color(color)
    data = channel.get()
    data["thumb_colors"] = ([color] + [c for c in data.get("thumb_colors", []) if c != color])[:MAX_COLORS]
    channel.save(data)
    return data["thumb_colors"]


def forget_color(color):
    data = channel.get()
    data["thumb_colors"] = [c for c in data.get("thumb_colors", []) if c != color.lower()]
    channel.save(data)
    return data["thumb_colors"]
