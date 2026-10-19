"""Foto dividida: photo on the top half of the content, a hard edge, the headline on a solid accent block."""
from .base import MARGIN, frame, photo, shape, tab, text

NAME, CATEGORY, NEEDS = "Foto dividida", "Foto", ("photo",)


def ops(d, c):
    split = c.y0 + int(c.ch * 0.48)
    body = [*photo(c, d, [0, c.y0 - 40, c.W, split - c.y0 + 40]),
            shape([0, split, c.W, c.y1 - split], c.c["accent"], name="Headline block")]
    t, _ = tab(c, MARGIN, split - 44, d.get("kicker") or "NOTÍCIA", c.c["breaking"], 40, 80)
    hh = int((c.y1 - split) * 0.68)
    body += [*t, text(c, d["headline"], [MARGIN, split + 70, c.W - 2 * MARGIN, hh], 96, 30, lines=5, upper=True,
                      name="Headline"),
             text(c, d.get("subhead") or "", [MARGIN, split + 80 + hh, c.W - 2 * MARGIN, c.y1 - (split + 100 + hh)],
                  36, 20, role="body", lines=2, valign="top", name="Subhead", element="subhead", spacing=0.05)]
    return frame(c, d, body)
