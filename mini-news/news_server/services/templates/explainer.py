"""Entenda: "ENTENDA" tab, the headline on the plate, each point on its own plate with a check mark."""
from .base import MARGIN, frame, plate, shape, tab, text

NAME, CATEGORY, NEEDS = "Entenda", "Dados", ("points",)


def ops(d, c):
    t, _ = tab(c, MARGIN, c.y0, "ENTENDA", c.c["breaking"], 44, 80)
    py, ph = c.y0 + 95, int(c.ch * 0.25)
    body = [*t, *plate(c, [30, py, c.W - 60, ph], d["headline"], 70)]
    pts = d["points"][:4]
    top = py + ph + 40
    row = (c.y1 - top) // len(pts)
    for i, p in enumerate(pts):
        y, h = top + i * row, row - 22
        sq = min(h - 30, 70)
        body += [shape([MARGIN - 30, y, c.W - 2 * MARGIN + 60, h], c.c["bar"], name=f"Point {i + 1} box"),
                 shape([MARGIN - 6, y + (h - sq) // 2, sq, sq], c.c["accent"], round=12, name=f"Point {i + 1} check box"),
                 text(c, "✓", [MARGIN - 6, y + (h - sq) // 2, sq, sq], 46, 16, lines=1, align="center",
                      name=f"Point {i + 1} check", element="tab"),
                 text(c, p, [MARGIN + sq + 20, y + 12, c.W - 2 * MARGIN - sq - 40, h - 24], 40, 20, role="body",
                      lines=3, name=f"Point {i + 1}", element="subhead", spacing=0.02)]
    return frame(c, d, body)
