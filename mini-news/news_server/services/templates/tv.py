"""TV: the headline as a TV lower third (tab + silver plate + ticker strip), over the photo when there is one."""
from ...paths import PHOTOS
from .base import MARGIN, frame, photo, shape, tab, text

NAME, CATEGORY, NEEDS = "TV", "Título", ()


def ops(d, c):
    before = []
    if (PHOTOS / f"{d['id']}.jpg").is_file():
        before = photo(c, d, [0, 0, c.W, c.y1], darken=0.15) + [
            {"op": "gradient", "name": "Top shade", "color": c.c["background"][-1], "start": [0, 0], "end": [0, c.y0 + 80]}]
    py, ph = c.y1 - int(c.ch * 0.42), int(c.ch * 0.27)
    t, _ = tab(c, 40, py - 70, d.get("kicker") or "AGORA", c.c["accent"], 36, 70)
    sy = py + ph + 12
    body = [*t,
            shape([20, py, c.W - 40, ph], c.c["plate"], slant=30, name="Lower third", shadow=True),
            text(c, d["headline"], [60, py + 22, c.W - 150, ph - 44], 80, 30, lines=3, color=c.c["plate_text"],
                 upper=True, name="Headline"),
            shape([20, sy, c.W - 40, 72], c.c["bar"], name="Ticker"),
            shape([20, sy, 210, 72], c.c["breaking"], slant=20, name="Ticker label"),
            text(c, "ÚLTIMAS", [30, sy, 170, 72], 30, 16, lines=1, align="center", name="Ticker label text",
                 element="tab"),
            text(c, d.get("subhead") or d.get("x_text") or "", [250, sy, c.W - 300, 72], 32, 24, role="body", lines=1,
                 name="Ticker text", element="label")]
    return frame(c, d, body, before=before)
