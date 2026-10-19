"""Citação + foto: the quote over the darkened photo (usually of who said it)."""
from .base import frame, photo
from .quote import quote_body

NAME, CATEGORY, NEEDS = "Citação + foto", "Voz", ("quote", "photo")


def ops(d, c):
    dark = c.c["background"][-1]
    before = photo(c, d, [0, 0, c.W, c.H], darken=0.35) + [
        {"op": "gradient", "name": "Bottom shade", "color": dark, "start": [0, c.H], "end": [0, int(c.H * 0.45)]},
        {"op": "gradient", "name": "Top shade", "color": dark, "start": [0, 0], "end": [0, c.y0]}]
    return frame(c, d, quote_body(c, d, "#FFFFFF"), before=before)
