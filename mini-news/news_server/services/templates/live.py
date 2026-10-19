"""Ao vivo: red "AO VIVO" pill with a dot, camera viewfinder corners, the headline in the middle."""
from .base import MARGIN, frame, shape, subhead, text

NAME, CATEGORY, NEEDS = "Ao vivo", "Título", ()


def corners(c, x0, y0, x1, y1, arm=90, w=8):
    ops = []
    for cx, cy, dx, dy in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        hx = cx if dx > 0 else cx - arm
        vy = cy if dy > 0 else cy - arm
        ops.append(shape([hx, cy if dy > 0 else cy - w, arm, w], color="#FFFFFF", opacity=80, name="Viewfinder"))
        ops.append(shape([cx if dx > 0 else cx - w, vy, w, arm], color="#FFFFFF", opacity=80, name="Viewfinder"))
    return ops


def ops(d, c):
    red = c.c["breaking"][0]
    py = c.y0 + 20
    hy, hh = c.y0 + 150, int(c.ch * 0.5)
    body = [*corners(c, 30, c.y0 - 10, c.W - 30, c.y1),
            shape([MARGIN + 10, py, 300, 76], color=red, round=38, name="Live pill", shadow=True),
            {"op": "ellipse", "name": "Live dot", "box": [MARGIN + 38, py + 24, 28, 28], "color": "#FFFFFF"},
            text(c, "AO VIVO", [MARGIN + 80, py, 210, 76], 40, 18, lines=1, name="Live text", element="tab"),
            text(c, (d.get("kicker") or "").upper(), [MARGIN + 340, py, c.W - MARGIN - 400, 76], 34, 16, lines=1,
                 color=c.c["muted"], name="Kicker", element="tab"),
            text(c, d["headline"], [MARGIN + 10, hy, c.W - 2 * MARGIN - 20, hh], 112, 36, lines=6, upper=True,
                 name="Headline", shadow=True),
            *subhead(c, d.get("subhead"), hy + hh + 40, c.y1 - 40 - (hy + hh + 40))]
    return frame(c, d, body)
