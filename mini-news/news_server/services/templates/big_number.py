"""Número gigante: the first figure huge, its label, the headline as context underneath."""
from .base import MARGIN, frame, plate, shape, tab, text

NAME, CATEGORY, NEEDS = "Número gigante", "Dados", ("numbers",)


def ops(d, c):
    n = d["numbers"][0]
    t, _ = tab(c, 0, c.y0, d.get("kicker") or "EM NÚMEROS", c.c["accent"], 38, 70, center=True)
    vy, vh = c.y0 + 100, int(c.ch * 0.34)
    ly = vy + vh + 10
    body = [*t, text(c, n["value"], [MARGIN - 20, vy, c.W - 2 * MARGIN + 40, vh], 330, 60, lines=1, align="center",
                     color=c.c["number"], name="Big number", element="number", shadow=True),
            text(c, n["label"], [MARGIN, ly, c.W - 2 * MARGIN, int(c.ch * 0.12)], 52, 24, role="body", lines=2,
                 align="center", name="Label", element="label"),
            shape([(c.W - 200) // 2, ly + int(c.ch * 0.12) + 24, 200, 10], c.c["accent"], name="Divider"),
            *plate(c, [30, c.y1 - int(c.ch * 0.27), c.W - 60, int(c.ch * 0.27)], d["headline"], 66)]
    return frame(c, d, body)
