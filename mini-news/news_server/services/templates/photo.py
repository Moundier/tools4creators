"""Foto + título: the photo fills the top, fading into the background; kicker tab and plate over its edge."""
from .base import MARGIN, frame, photo, plate, subhead, tab

NAME, CATEGORY, NEEDS = "Foto + título", "Foto", ("photo",)


def ops(d, c):
    ph_h = c.y0 + int(c.ch * 0.62)
    before = photo(c, d, [0, 0, c.W, ph_h], fade_to=ph_h - int(ph_h * 0.36)) + [
        {"op": "gradient", "name": "Top shade", "color": c.c["background"][-1], "start": [0, 0], "end": [0, c.y0]}]
    py, ph = ph_h - int(c.ch * 0.15), int(c.ch * 0.31)
    t, _ = tab(c, MARGIN, py - 82, d.get("kicker") or "NOTÍCIA", c.c["accent"], 40, 76)
    body = [*t, *plate(c, [30, py, c.W - 60, ph], d["headline"], 84),
            *subhead(c, d.get("subhead"), py + ph + 30, c.y1 - (py + ph + 30), size=38, lines=2)]
    return frame(c, d, body, before=before)
