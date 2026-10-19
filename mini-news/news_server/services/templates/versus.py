"""Comparação: the headline on the plate, then the first two figures side by side with a VS badge."""
from .base import MARGIN, frame, plate, shape, tab, text

NAME, CATEGORY, NEEDS = "Comparação", "Dados", ("numbers2",)


def ops(d, c):
    a, b = d["numbers"][:2]
    t, _ = tab(c, MARGIN, c.y0, d.get("kicker") or "COMPARAÇÃO", c.c["accent"], 40, 76)
    py, ph = c.y0 + 90, int(c.ch * 0.26)
    by = py + ph + 60
    bh = c.y1 - by - 20
    gap = 130   # room for the VS badge, so it never covers a label
    bw = (c.W - 2 * MARGIN + 40 - gap) // 2
    body = [*t, *plate(c, [30, py, c.W - 60, ph], d["headline"], 70)]
    for i, (n, x) in enumerate(((a, MARGIN - 20), (b, MARGIN - 20 + bw + gap))):
        body += [shape([x, by, bw, bh], c.c["bar"], round=24, name=f"Side {i + 1}"),
                 shape([x, by, bw, 12], c.c["accent"] if i == 0 else c.c["breaking"], name=f"Side {i + 1} top"),
                 text(c, n["value"], [x + 24, by + 50, bw - 48, int(bh * 0.4)], 150, 40, lines=1, align="center",
                      color=c.c["number"], name=f"Number {i + 1}", element="number"),
                 text(c, n["label"], [x + 24, by + 60 + int(bh * 0.4), bw - 48, int(bh * 0.45)], 44, 20, role="body",
                      lines=4, align="center", valign="top", name=f"Label {i + 1}", element="label")]
    vs = 110
    body += [{"op": "ellipse", "name": "VS circle", "box": [(c.W - vs) // 2, by + bh // 2 - vs // 2, vs, vs],
              "stops": c.c["breaking"], "shadow": True},
             text(c, "VS", [(c.W - vs) // 2, by + bh // 2 - vs // 2, vs, vs], 52, 20, lines=1, align="center",
                  name="VS", element="tab")]
    return frame(c, d, body)
