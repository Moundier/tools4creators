"""Styles: how the images look (format, colors, background, logo, fonts, font sizes, texts).

Saved styles: one JSON file each in styles/ (next to news.py); "default" is the one every new draft starts from.
Each draft keeps its OWN copy (draft["style_data"]): customizing a draft never changes other drafts or the saved
styles, unless you "save as default". Uploaded files (background, logo, fonts) go to styles/assets/.
A style only needs the keys it changes: everything else comes from DEFAULT. "templates" can override any of them
for one template, e.g. {"templates": {"breaking": {"colors": {"accent": ["#ff0000", "#990000"]}}}}.
"""
import copy
import json
import re
import time

from pathlib import Path

from ..paths import STYLES

FONTS_DIR = Path.home() / ".local/share/fonts/mini-news"

FORMATS = {"9:16": (1080, 1920), "4:5": (1080, 1350)}

DEFAULT = {
    "name": "Padrão",
    "format": "9:16",
    "colors": {
        "accent": ["#3056ff", "#0a1a96"],         # tabs, strips, author tab
        "breaking": ["#eb2834", "#960a16"],       # the Breaking news tab
        "background": ["#162878", "#060c34"],     # top -> bottom
        "plate": ["#fafbfd", "#d6dae2", "#b0b6c2"],   # the headline plate
        "plate_text": "#0d1a4a",
        "bar": ["#101e60", "#050b30"],            # source bar, number boxes
        "text": "#ffffff",
        "muted": "#aab6e1",
        "number": "#7896ff",
        "quote_mark": "#3056ff",
    },
    "background": {"image": "", "opacity": 0.35, "darken": 0.45, "stripes": True},
    "logo": {"image": "", "position": "top", "height": 110},   # top / top-left / top-right / none
    "fonts": {"heading": "", "body": "", "heading_name": "", "body_name": ""},   # files in styles/assets/ + the
                                                   # font names GIMP knows them by ("" = Montserrat Bold)
    "sizes": {"headline": 1.0, "subhead": 1.0, "quote": 1.0, "number": 1.0, "label": 1.0, "tab": 1.0},
    "texts": {"channel": "Newhouse", "badge": "NEWS", "follow": "Siga {channel} para mais notícias",
              "source_prefix": "FONTE:", "show_date": True, "show_badge": True},
    "templates": {},
}
# "Cor" in the Estilo step: one click sets the accent colors (like mini-studio's --color themes)
THEMES = {
    "azul": {"accent": ["#3056ff", "#0a1a96"], "number": "#7896ff", "quote_mark": "#3056ff"},
    "roxo": {"accent": ["#8e24aa", "#4a148c"], "number": "#ce93d8", "quote_mark": "#ab47bc"},
    "verde": {"accent": ["#2e9b45", "#1b5e20"], "number": "#81c784", "quote_mark": "#43a047"},
    "rosa": {"accent": ["#e0177d", "#8c0a4b"], "number": "#f48fb1", "quote_mark": "#ec407a"},
    "vermelho": {"accent": ["#d62630", "#7f0d14"], "number": "#ef9a9a", "quote_mark": "#e53935"},
    "laranja": {"accent": ["#f07800", "#a04f00"], "number": "#ffb74d", "quote_mark": "#fb8c00"},
    "turquesa": {"accent": ["#0f8a8f", "#065a5e"], "number": "#80deea", "quote_mark": "#26a69a"},
    "amarelo": {"accent": ["#ffcc00", "#c79a00"], "number": "#ffe082", "quote_mark": "#ffcc00"},
}

ASSET_KINDS = {"background": (".jpg", ".jpeg", ".png", ".webp"), "logo": (".png", ".webp", ".jpg", ".jpeg"),
               "font_heading": (".ttf", ".otf"), "font_body": (".ttf", ".otf")}


def merge(base, over):
    """Deep merge: dicts are merged key by key, everything else is replaced."""
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else copy.deepcopy(v)
    return out


def _file(style_id):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,40}", style_id or ""):
        raise KeyError(f"no style {style_id!r}")
    return STYLES / f"{style_id}.json"


def ensure_default():
    STYLES.mkdir(parents=True, exist_ok=True)
    f = STYLES / "default.json"
    if not f.is_file():
        f.write_text(json.dumps({"name": DEFAULT["name"]}, ensure_ascii=False, indent=2), encoding="utf-8")


def raw(style_id):
    """What the style file itself says (only the keys it changes)."""
    f = _file(style_id)
    if not f.is_file():
        raise KeyError(f"no style {style_id!r}")
    return json.loads(f.read_text(encoding="utf-8"))


def load(style_id, template=None, data=None):
    """The full style: DEFAULT + the saved style file (or `data`, a draft's own copy), with that template's
    overrides applied when given."""
    if data is not None:
        s = merge(DEFAULT, data)
    else:
        try:
            s = merge(DEFAULT, raw(style_id or "default"))
        except KeyError:
            ensure_default()
            s = merge(DEFAULT, raw("default"))
    if template:
        s = merge(s, s.get("templates", {}).get(template))
    if s["format"] not in FORMATS:
        s["format"] = "9:16"
    return s


def all_styles():
    ensure_default()
    out = []
    for f in sorted(STYLES.glob("*.json")):
        s = merge(DEFAULT, json.loads(f.read_text(encoding="utf-8")))
        out.append({"id": f.stem, "name": s["name"], "format": s["format"], "accent": s["colors"]["accent"][0]})
    return sorted(out, key=lambda s: (s["id"] != "default", s["name"].lower()))


def validate(data):
    """The full style (DEFAULT + data), or ValueError for a bad format / size / color."""
    data = merge(DEFAULT, data)
    if data["format"] not in FORMATS:
        raise ValueError(f"format must be one of {', '.join(FORMATS)}")
    for k, v in data["sizes"].items():
        if not isinstance(v, (int, float)) or not 0.5 <= v <= 2:
            raise ValueError(f"size {k} must be between 0.5 and 2")
    for k, v in data["colors"].items():
        for c in v if isinstance(v, list) else [v]:
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(c)):
                raise ValueError(f"color {k}: {c!r} isn't #rrggbb")
    return data


def save(style_id, data):
    """Store the full style as given (after validating it)."""
    data = validate(data)
    STYLES.mkdir(parents=True, exist_ok=True)
    _file(style_id).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return load(style_id)


def reset_default():
    """The default style back to the original look (blue + silver)."""
    STYLES.mkdir(parents=True, exist_ok=True)
    (STYLES / "default.json").write_text(json.dumps({"name": DEFAULT["name"]}, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
    return load("default")


def create(name, copy_from="default"):
    base = raw(copy_from) if _file(copy_from).is_file() else {}
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:30] or "estilo"
    style_id, n = slug, 2
    while _file(style_id).is_file():
        style_id, n = f"{slug}-{n}", n + 1
    save(style_id, {**base, "name": name.strip() or slug})
    return style_id


def delete(style_id):
    if style_id == "default":
        raise ValueError("the default style can't be deleted")
    f = _file(style_id)
    if not f.is_file():
        raise KeyError(f"no style {style_id!r}")
    f.unlink()   # its uploaded files stay: drafts may still use them in their own copy of the style


def add_asset(style, prefix, kind, filename, data):
    """Store an uploaded background / logo / font in styles/assets/ and set it on `style` (a full style dict,
    changed in place and returned)."""
    if kind not in ASSET_KINDS:
        raise ValueError(f"kind must be one of {', '.join(ASSET_KINDS)}")
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ASSET_KINDS[kind]:
        raise ValueError(f"{kind}: use a {' / '.join(ASSET_KINDS[kind])} file")
    name = f"{prefix}-{kind}-{int(time.time())}{ext}"
    (STYLES / "assets").mkdir(parents=True, exist_ok=True)
    (STYLES / "assets" / name).write_bytes(data)
    if kind == "background":
        style["background"]["image"] = name
    elif kind == "logo":
        style["logo"]["image"] = name
    else:
        role = kind.removeprefix("font_")
        style["fonts"][role], style["fonts"][f"{role}_name"] = name, install_font(STYLES / "assets" / name)
    return style


def save_asset(style_id, kind, filename, data):
    """An uploaded file set on a saved style."""
    return save(style_id, add_asset(merge(DEFAULT, raw(style_id)), style_id, kind, filename, data))


def install_font(path):
    """Copy a font where GIMP finds it (~/.local/share/fonts/mini-news/) and return its name ("Family Style")."""
    import subprocess

    from PIL import ImageFont

    family, style = ImageFont.truetype(str(path), 20).getname()
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    (FONTS_DIR / path.name).write_bytes(path.read_bytes())
    subprocess.run(["fc-cache", "-f", str(FONTS_DIR)], capture_output=True)
    return f"{family} {style}".strip()


def asset(name):
    """Path of an uploaded file, or None."""
    p = STYLES / "assets" / name if name else None
    return p if p and p.parent == STYLES / "assets" and p.is_file() else None
