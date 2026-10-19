"""Foto moldura: kicker + headline on top, the photo as a framed rounded card, subhead under it."""
from .base import MARGIN, frame, photo, shape, subhead, tab, text

NAME, CATEGORY, NEEDS = "Foto moldura", "Foto", ("photo",)


def ops(d, c):
    t, _ = tab(c, MARGIN, c.y0, d.get("kicker") or "NOTÍCIA", c.c["accent"], 38, 70)
    hh = int(c.ch * 0.24)
    fy, fh = c.y0 + 100 + hh + 20, int(c.ch * 0.48)
    body = [*t, text(c, d["headline"], [MARGIN, c.y0 + 90, c.W - 2 * MARGIN, hh], 86, 30, lines=4, upper=True,
                     name="Headline"),
            shape([MARGIN - 12, fy - 12, c.W - 2 * MARGIN + 24, fh + 24], c.c["plate"], round=40, name="Photo frame",
                  shadow=True),
            *photo(c, d, [MARGIN, fy, c.W - 2 * MARGIN, fh], round=30),
            *subhead(c, d.get("subhead"), fy + fh + 40, c.y1 - (fy + fh + 40), size=36, lines=2)]
    return frame(c, d, body)
