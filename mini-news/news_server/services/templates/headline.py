"""Manchete: a big centered headline straight on the background, accent underline, subhead."""
from .base import MARGIN, frame, shape, subhead, tab, text

NAME, CATEGORY, NEEDS = "Manchete", "Título", ()


def ops(d, c):
    t, _ = tab(c, 0, c.y0, d.get("kicker") or "NOTÍCIA", c.c["accent"], 38, 70, center=True)
    hy, hh = c.y0 + 110, int(c.ch * 0.52)
    body = [*t, text(c, d["headline"], [MARGIN, hy, c.W - 2 * MARGIN, hh], 120, 36, lines=6, align="center",
                     upper=True, name="Headline", shadow=True),
            shape([(c.W - 240) // 2, hy + hh + 30, 240, 14], c.c["accent"], name="Underline"),
            *subhead(c, d.get("subhead"), hy + hh + 80, c.y1 - (hy + hh + 80), align="center")]
    return frame(c, d, body)
