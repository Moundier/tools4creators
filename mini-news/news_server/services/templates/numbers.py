"""Números: the headline on the plate, then 1-3 big figures, each with its label."""
from .base import MARGIN, frame, plate, shape, tab, text

NAME, CATEGORY, NEEDS = "Números", "Dados", ("numbers",)


def ops(d, c):
    t, _ = tab(c, MARGIN, c.y0, d.get("kicker") or "EM NÚMEROS", c.c["accent"], 40, 76)
    py, ph = c.y0 + 90, int(c.ch * 0.26)
    body = [*t, *plate(c, [30, py, c.W - 60, ph], d["headline"], 72)]
    nums = d["numbers"][:3]
    top = py + ph + 44
    row = (c.y1 - top) // len(nums)
    for i, n in enumerate(nums):
        y, h = top + i * row, min(row - 30, 240)
        body += [shape([MARGIN - 30, y, c.W - 2 * MARGIN + 60, h], c.c["bar"], name=f"Number {i + 1} box"),
                 shape([MARGIN - 30, y, 14, h], c.c["accent"], name=f"Number {i + 1} edge"),
                 text(c, n["value"], [MARGIN + 20, y + 10, c.W - 2 * MARGIN - 40, int(h * 0.58)], 120, 36, lines=1,
                      color=c.c["number"], name=f"Number {i + 1}", element="number"),
                 text(c, n["label"], [MARGIN + 22, y + int(h * 0.62), c.W - 2 * MARGIN - 40, int(h * 0.32)], 40, 20,
                      role="body", lines=2, name=f"Number {i + 1} label", element="label")]
    return frame(c, d, body)
