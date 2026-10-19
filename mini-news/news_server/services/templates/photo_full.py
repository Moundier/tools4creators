"""Foto inteira: the photo fills everything; a dark gradient from the bottom; white headline on the photo."""
from .base import MARGIN, frame, photo, subhead, tab, text

NAME, CATEGORY, NEEDS = "Foto inteira", "Foto", ("photo",)


def ops(d, c):
    dark = c.c["background"][-1]
    before = photo(c, d, [0, 0, c.W, c.H]) + [
        {"op": "gradient", "name": "Bottom shade", "color": dark, "start": [0, c.H], "end": [0, int(c.H * 0.4)]},
        {"op": "gradient", "name": "Top shade", "color": dark, "start": [0, 0], "end": [0, c.y0]}]
    ty = c.y1 - int(c.ch * 0.5)
    t, _ = tab(c, MARGIN, ty, d.get("kicker") or "NOTÍCIA", c.c["breaking"], 40, 76)
    hh = int(c.ch * 0.32)
    body = [*t, text(c, d["headline"], [MARGIN, ty + 100, c.W - 2 * MARGIN, hh], 100, 32, lines=5, upper=True,
                     valign="top", name="Headline", shadow=True),
            *subhead(c, d.get("subhead"), ty + 120 + hh, c.y1 - (ty + 120 + hh), size=38, lines=2)]
    return frame(c, d, body, before=before)
