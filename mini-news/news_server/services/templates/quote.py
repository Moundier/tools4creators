"""Citação: a giant quotation mark, the quote word for word, the author on a tab + role, the headline as context."""
from .base import MARGIN, frame, shape, tab, text

NAME, CATEGORY, NEEDS = "Citação", "Voz", ("quote",)


def quote_body(c, d, color=None):
    q = d["quote"]
    mark = int(c.ch * 0.2)
    qy, qh = c.y0 + int(mark * 0.6), int(c.ch * 0.5)
    ay = qy + qh + 30
    body = [text(c, "“", [MARGIN - 14, c.y0 - int(mark * 0.35), int(mark * 1.4), int(mark * 1.6)], int(mark * 2.2), 60,
                 lines=1, valign="top", color=c.c["quote_mark"], name="Quote mark", element="quote"),
            text(c, q["text"].strip().strip('"“”'), [MARGIN + 10, qy, c.W - 2 * MARGIN - 20, qh], 84, 30,
                 role="body", lines=9, valign="bottom", color=color, name="Quote", element="quote", spacing=0.02,
                 shadow=bool(color))]
    t, _ = tab(c, MARGIN, ay, q.get("author") or "", c.c["accent"], 38, 74, name="Author")
    body += t
    if q.get("role"):
        rw = min(int(c.width(q["role"], c.size("label", 30), "body")) + 120, c.W - MARGIN - 30)
        body += [shape([MARGIN + 30, ay + 80, rw, 56], c.c["plate"], slant=22, left_slant=22, name="Role plate"),
                 text(c, q["role"], [MARGIN + 75, ay + 80, rw - 110, 56], 30, 16, role="body", lines=1,
                      color=c.c["plate_text"], name="Role", element="label")]
    body.append(text(c, d["headline"], [MARGIN, ay + 160, c.W - 2 * MARGIN, c.y1 - (ay + 160)], 34, 18, role="body",
                     lines=2, valign="top", color=c.c["muted"], name="Context", element="subhead", spacing=0.05))
    return body


def ops(d, c):
    return frame(c, d, quote_body(c, d))
