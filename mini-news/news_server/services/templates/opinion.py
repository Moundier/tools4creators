"""Opinião: "MINHA OPINIÃO" tab, your take in big type, your channel as signature, the news it's about."""
from .base import MARGIN, frame, shape, tab, text

NAME, CATEGORY, NEEDS = "Opinião", "Voz", ("take",)


def ops(d, c):
    t, _ = tab(c, MARGIN, c.y0, "MINHA OPINIÃO", c.c["accent"], 40, 76)
    ty, th = c.y0 + 120, int(c.ch * 0.52)
    sy = ty + th + 20
    body = [*t, shape([MARGIN, ty, 10, th], c.c["accent"], name="Bar"),
            text(c, d["take"], [MARGIN + 40, ty, c.W - 2 * MARGIN - 40, th], 80, 30, role="body", lines=9,
                 name="Opinion", element="quote", spacing=0.02),
            text(c, f"— {c.texts.get('channel', '')}", [MARGIN + 40, sy, c.W - 2 * MARGIN - 40, 56], 40, 18, lines=1,
                 color=c.c["number"], name="Signature", element="label"),
            shape([MARGIN, sy + 90, c.W - 2 * MARGIN, 2], c.c["plate"][:1], name="Rule"),
            text(c, "SOBRE: " + d["headline"], [MARGIN, sy + 110, c.W - 2 * MARGIN, c.y1 - (sy + 110)], 32, 16,
                 role="body", lines=3, valign="top", color=c.c["muted"], name="About", element="subhead")]
    return frame(c, d, body)
