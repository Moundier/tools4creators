"""Breaking news: kicker tab (breaking color), huge headline on the silver plate, subhead underneath."""
from .base import MARGIN, frame, plate, shape, subhead, tab

NAME, CATEGORY, NEEDS = "Breaking news", "Título", ()


def ops(d, c):
    t, _ = tab(c, MARGIN, c.y0, d.get("kicker") or "URGENTE", c.c["breaking"], 46, 86)
    py, ph = c.y0 + 100, int(c.ch * 0.5)
    body = [*t, *plate(c, [30, py, c.W - 60, ph], d["headline"], 112, slant=46, lines=5),
            shape([290, py + ph + 8, c.W - 330, 20], c.c["accent"], slant=12, left_slant=12, name="Strip"),
            *subhead(c, d.get("subhead"), py + ph + 60, c.y1 - (py + ph + 60))]
    return frame(c, d, body)
