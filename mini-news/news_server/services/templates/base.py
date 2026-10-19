"""Shared building blocks for the news templates. Templates return GIMP op lists (see gimp/gimp_render.py);
GIMP draws them, fits the text (text layers stay editable) and saves .xcf + .jpg.

Everything that changes the look comes from the style (styles.py): format, colors, background image, logo,
fonts, font sizes and texts. Layout: each format has a content area (y0..y1) where templates place their
headline / quote / numbers...; branding (logo, channel badge, date) sits above it, the source bar and footer
line below. In 9:16, feeds on X and Facebook crop to about 4:5, so the content area is the middle 1080x1350.
"""
import time

from PIL import ImageFont

from ...paths import FONT
from .. import styles

MARGIN = 60
LAYOUTS = {   # format -> branding top, content y0..y1, source bar top, footer line center (None = no footer)
    "9:16": {"brand": 120, "y0": 330, "y1": 1530, "source": 1551, "follow": 1770},
    "4:5": {"brand": 36, "y0": 170, "y1": 1180, "source": 1206, "follow": 1305},
}
SILVER_TEXT = "#0d1a4a"


class Ctx:
    """One render: the style (with this template's overrides), canvas size and layout."""

    def __init__(self, style_id, template, data=None):
        self.s = styles.load(style_id, template, data)   # data: the draft's own copy of the style
        self.W, self.H = styles.FORMATS[self.s["format"]]
        self.L = LAYOUTS[self.s["format"]]
        self.y0, self.y1 = self.L["y0"], self.L["y1"]
        self.c = self.s["colors"]
        self.sizes, self.texts = self.s["sizes"], self.s["texts"]
        self.big = self.s["format"] == "9:16"

    @property
    def ch(self):
        """Content area height."""
        return self.y1 - self.y0

    def font(self, role="heading"):
        """GIMP font name for a role (heading / body): the style's uploaded font, or Montserrat Bold."""
        f = self.s["fonts"]
        return f.get(f"{role}_name") or f.get("heading_name") or "Montserrat Bold"

    def _pil_font(self, role, size):
        path = styles.asset(self.s["fonts"].get(role)) or styles.asset(self.s["fonts"].get("heading")) or FONT
        try:
            return ImageFont.truetype(str(path), int(size))
        except OSError:
            return ImageFont.load_default(int(size))

    def width(self, text, size, role="heading"):
        """Text width in px, to size tabs and badges around a label (GIMP fits the text itself)."""
        return self._pil_font(role, size).getlength(text)

    def size(self, element, base):
        return int(base * float(self.sizes.get(element, 1.0)))


# ---------------------------------------------------------------- op builders

def text(c, value, box, max_size, min_size=22, *, role="heading", color=None, lines=3, align="left",
         valign="middle", upper=False, name=None, element="headline", spacing=-0.12, shadow=False):
    return {"op": "text", "text": value or "", "box": [int(v) for v in box], "font": c.font(role),
            "color": color or c.c["text"], "max_size": c.size(element, max_size),
            "min_size": min(c.size(element, max_size), min_size), "max_lines": lines, "align": align,
            "valign": valign, "upper": upper, "name": name, "line_spacing": spacing, "shadow": shadow}


def shape(box, stops=None, color=None, *, slant=0, left_slant=0, round=0, shine=False, name="Shape",
          opacity=100, shadow=False, points=None):
    op = {"op": "shape", "box": [int(v) for v in box], "name": name, "opacity": opacity, "slant": slant,
          "left_slant": left_slant, "round": round, "shine": shine, "shadow": shadow}
    if stops:
        op["stops"] = list(stops)
    else:
        op["color"] = color
    if points:
        op["points"] = points
    return op


def background(c, with_image=True):
    """Gradient, the style's background image (faded + darkened), stripes."""
    b = c.s["background"]
    ops = [shape([0, 0, c.W, c.H], c.c["background"], name="Background")]
    path = styles.asset(b.get("image")) if with_image else None
    if path:
        ops.append({"op": "image", "name": "Background image", "path": str(path), "box": [0, 0, c.W, c.H],
                    "opacity": 100 * float(b.get("opacity", 0.35))})
        if float(b.get("darken", 0)):
            ops.append(shape([0, 0, c.W, c.H], color=c.c["background"][-1], name="Darken",
                             opacity=100 * float(b["darken"])))
    if b.get("stripes", True):
        ops.append({"op": "stripes", "name": "Stripes", "opacity": 4})
    return ops


def photo(c, d, box, *, fade_to=None, darken=0, round=0, name="Photo"):
    """The draft's photo filling `box` (cover). fade_to: y where it has fully faded into the background."""
    from ...paths import PHOTOS
    op = {"op": "image", "name": name, "path": str(PHOTOS / f"{d['id']}.jpg"), "box": [int(v) for v in box],
          "fit": "cover", "round": round}
    if fade_to:
        bottom = box[1] + box[3]
        op["fade"] = {"from": [0, bottom], "to": [0, fade_to]}
    ops = [op]
    if darken:
        ops.append(shape(box, color="#000000", name="Photo darken", opacity=100 * darken, round=round))
    return ops


def tab(c, x, y, label, stops=None, size=40, h=76, name="Tab", element="tab", color=None, center=False):
    """A glossy slanted label tab; returns (ops, width). center=True centers it on the canvas (x ignored)."""
    label = (label or "").upper()
    s = c.size(element, size)
    w = int(c.width(label, s)) + 110
    if center:
        x = (c.W - w) // 2
    return [shape([x, y, w, h], stops or c.c["accent"], slant=28, left_slant=28, shine=True, name=name),
            text(c, label, [x + 30, y, w - 60, h], s, 16, align="center", lines=1, name=f"{name} text",
                 element=element, color=color)], w


def plate(c, box, value, max_size, *, slant=40, lines=4, name="Headline", upper=True, pad=80):
    """The silver headline plate with the headline fitted inside."""
    x, y, w, h = box
    return [shape(box, c.c["plate"], slant=slant, left_slant=slant, name=f"{name} plate"),
            text(c, value, [x + pad, y + 28, w - 2 * pad - slant, h - 56], max_size, 30, color=c.c["plate_text"],
                 lines=lines, upper=upper, name=name)]


def subhead(c, value, y, h, size=44, *, align="left", color=None, lines=3):
    if not value:
        return []
    return [text(c, value, [MARGIN, y, c.W - 2 * MARGIN, h], size, 22, role="body", lines=lines, align=align,
                 valign="top", color=color, name="Subhead", element="subhead", spacing=0.05)]


def source_bar(c, name):
    y = c.L["source"]
    prefix = c.texts.get("source_prefix", "FONTE:")
    return [shape([0, y, c.W, 64], c.c["bar"], name="Source bar"),
            shape([0, y, c.W, 3], c.c["plate"][:2], name="Source line"),
            text(c, f"{prefix} {name}".strip(), [MARGIN, y + 8, c.W - 2 * MARGIN, 50], 30, 16, role="body",
                 lines=1, upper=True, name="Source", element="label")]


def branding(c):
    """Above the content: logo (if any) + channel badge (+ date). Below the source bar: the footer line."""
    t, lg = c.texts, c.s["logo"]
    channel = t.get("channel", "")
    y, bh = c.L["brand"], 76 if c.big else 64
    pos = lg.get("position", "top")
    logo = styles.asset(lg.get("image")) if pos != "none" else None
    lh = int(lg.get("height", 110)) * (1 if c.big else 0.75)
    lw = 0
    if logo:
        from PIL import Image
        with Image.open(logo) as im:
            lw = int(im.width * lh / im.height)
    ops = []
    badge_w = nw = rw = 0
    fs = 40 if c.big else 34
    if t.get("show_badge", True) and channel:
        nw = int(c.width(channel.upper(), fs)) + 70
        rw = int(c.width(t.get("badge", ""), fs)) + 70 if t.get("badge") else 0
        badge_w = nw + rw
    gap = 18 if logo and badge_w else 0
    if pos == "top" or not logo:
        x = (c.W - lw - gap - badge_w) // 2
        logo_x, badge_x = x, x + lw + gap
    elif pos == "top-left":
        logo_x, badge_x = MARGIN, c.W - MARGIN - badge_w
    else:
        logo_x, badge_x = c.W - MARGIN - lw, MARGIN
    if logo:
        ly = int(y + bh / 2 - lh / 2) if badge_w else y
        ops.append({"op": "image", "name": "Logo", "path": str(logo), "box": [logo_x, ly, lw, int(lh)],
                    "fit": "contain"})
    if badge_w:
        if rw:
            ops.append(shape([badge_x + nw - 24, y, rw + 24, bh], c.c["plate"], name="Badge right"))
        ops.append(shape([badge_x, y, nw, bh], c.c["accent"], slant=22 if rw else 0, shine=True, name="Badge"))
        ops.append(text(c, channel.upper(), [badge_x + 20, y, nw - 40 - (22 if rw else 0), bh], fs, 14,
                        align="center", lines=1, name="Channel"))
        if rw:
            ops.append(text(c, t["badge"], [badge_x + nw, y, rw - 20, bh], fs, 14, align="center", lines=1,
                            color=c.c["plate_text"], name="Badge text"))
    if t.get("show_date", True):
        below = max(bh, lh if logo else 0) / 2 + bh / 2 + (8 if c.big else 2)
        ops.append(text(c, time.strftime("%d/%m/%Y"), [0, y + below, c.W, 44 if c.big else 36], 30 if c.big else 26,
                        14, role="body", align="center", lines=1, color=c.c["muted"], name="Date", element="label"))
    if t.get("follow") and c.L["follow"]:
        fy = c.L["follow"]
        ops.append(text(c, t["follow"].format(channel=channel), [MARGIN, fy - 30, c.W - 2 * MARGIN, 60],
                        34 if c.big else 28, 14, role="body", align="center", lines=1, color=c.c["muted"],
                        name="Footer", element="label"))
    return ops


def frame(c, d, body, *, with_bg_image=True, before=None):
    """A full template: background (+ ops drawn before branding, e.g. a photo), branding, body, source bar."""
    return [*background(c, with_bg_image), *(before or []), *branding(c), *body, *source_bar(c, d["source_name"])]
