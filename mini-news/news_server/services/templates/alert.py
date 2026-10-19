"""Alerta: yellow/black warning stripe bands, a yellow tab, the headline on a dark plate."""
from .base import MARGIN, frame, shape, subhead, tab, text

NAME, CATEGORY, NEEDS = "Alerta", "Título", ()
YELLOW = ["#ffd54f", "#ffb300"]


def band(c, y, h=70):
    return [shape([0, y, c.W, h], color="#111111", name="Warning band"),
            {"op": "stripes", "name": "Warning stripes", "box": [0, y, c.W, h], "color": YELLOW[1], "opacity": 100,
             "step": 70, "width": 35}]


def ops(d, c):
    t, _ = tab(c, MARGIN, c.y0 + 110, d.get("kicker") or "ALERTA", YELLOW, 46, 86, color="#111111")
    py, ph = c.y0 + 210, int(c.ch * 0.46)
    body = [*band(c, c.y0), *t,
            shape([30, py, c.W - 60, ph], c.c["bar"], slant=40, left_slant=40, name="Headline plate"),
            shape([30, py, 14, ph], YELLOW, name="Plate edge"),
            text(c, d["headline"], [100, py + 30, c.W - 220, ph - 60], 104, 32, lines=5, upper=True, name="Headline"),
            *subhead(c, d.get("subhead"), py + ph + 40, c.y1 - 110 - (py + ph + 40)),
            *band(c, c.y1 - 70)]
    return frame(c, d, body)
