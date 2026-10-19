"""Linha do tempo: the headline, then a vertical line with a dot per point (in order)."""
from .base import MARGIN, frame, shape, tab, text

NAME, CATEGORY, NEEDS = "Linha do tempo", "Dados", ("points",)


def ops(d, c):
    t, _ = tab(c, MARGIN, c.y0, d.get("kicker") or "LINHA DO TEMPO", c.c["accent"], 40, 76)
    hh = int(c.ch * 0.22)
    body = [*t, text(c, d["headline"], [MARGIN, c.y0 + 95, c.W - 2 * MARGIN, hh], 78, 30, lines=4, upper=True,
                     name="Headline")]
    pts = d["points"][:4]
    top = c.y0 + 130 + hh
    row = (c.y1 - top) // len(pts)
    lx, dot = MARGIN + 30, 44
    body.append(shape([lx + dot // 2 - 4, top + dot // 2, 8, row * (len(pts) - 1)], c.c["accent"], name="Line"))
    for i, p in enumerate(pts):
        y = top + i * row
        body += [{"op": "ellipse", "name": f"Stop {i + 1}", "box": [lx, y, dot, dot], "color": c.c["number"],
                  "ring": 0},
                 {"op": "ellipse", "name": f"Stop {i + 1} center", "box": [lx + 12, y + 12, dot - 24, dot - 24],
                  "color": c.c["background"][-1]},
                 text(c, p, [lx + dot + 36, y - 6, c.W - lx - dot - 36 - MARGIN, row - 20], 44, 22, role="body",
                      lines=3, valign="top", name=f"Point {i + 1}", element="subhead", spacing=0.02)]
    return frame(c, d, body)
