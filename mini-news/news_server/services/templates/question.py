"""Pergunta: "E VOCÊ?" tab, the question to readers huge, a "comment" call, the news as context."""
from .base import MARGIN, frame, shape, tab, text

NAME, CATEGORY, NEEDS = "Pergunta", "Voz", ("question",)


def ops(d, c):
    t, _ = tab(c, 0, c.y0, "E VOCÊ?", c.c["breaking"], 48, 88, center=True)
    qy, qh = c.y0 + 130, int(c.ch * 0.5)
    cy = qy + qh + 40
    body = [*t, text(c, d["question"], [MARGIN, qy, c.W - 2 * MARGIN, qh], 110, 36, lines=7, align="center",
                     name="Question", shadow=True),
            shape([(c.W - 560) // 2, cy, 560, 84], c.c["accent"], round=42, name="Comment pill", shine=True),
            text(c, "COMENTE AQUI EMBAIXO", [(c.W - 500) // 2, cy, 500, 84], 36, 16, lines=1, align="center",
                 name="Comment call", element="tab"),
            text(c, d["headline"], [MARGIN, cy + 120, c.W - 2 * MARGIN, c.y1 - (cy + 120)], 32, 16, role="body",
                 lines=2, align="center", valign="top", color=c.c["muted"], name="Context", element="subhead")]
    return frame(c, d, body)
