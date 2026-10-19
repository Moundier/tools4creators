"""Pontos-chave: the headline, then the key points as a numbered list (numbers in accent circles)."""
from .base import MARGIN, frame, tab, text

NAME, CATEGORY, NEEDS = "Pontos-chave", "Dados", ("points",)


def ops(d, c):
    t, _ = tab(c, MARGIN, c.y0, d.get("kicker") or "PONTOS-CHAVE", c.c["accent"], 40, 76)
    hh = int(c.ch * 0.24)
    body = [*t, text(c, d["headline"], [MARGIN, c.y0 + 95, c.W - 2 * MARGIN, hh], 80, 30, lines=4, upper=True,
                     name="Headline")]
    pts = d["points"][:4]
    top = c.y0 + 120 + hh
    row = (c.y1 - top) // len(pts)
    r = 84
    for i, p in enumerate(pts):
        y = top + i * row
        body += [{"op": "ellipse", "name": f"Point {i + 1} circle", "box": [MARGIN, y + 6, r, r], "stops": c.c["accent"]},
                 text(c, str(i + 1), [MARGIN, y + 6, r, r], 50, 20, lines=1, align="center", name=f"Point {i + 1} n",
                      element="tab"),
                 text(c, p, [MARGIN + r + 30, y, c.W - 2 * MARGIN - r - 30, row - 24], 46, 22, role="body", lines=3,
                      valign="top", name=f"Point {i + 1}", element="subhead", spacing=0.02)]
    return frame(c, d, body)
