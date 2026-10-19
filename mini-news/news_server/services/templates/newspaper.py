"""Jornal: a newspaper front page on paper: masthead, double rules with the date, headline, 2-column subhead."""
import time

from .base import MARGIN, frame, shape, text

NAME, CATEGORY, NEEDS = "Jornal", "Título", ()
PAPER = ["#f7f4ec", "#ebe5d6"]


def ops(d, c):
    ink = c.c["plate_text"]
    x0, x1 = MARGIN - 20, c.W - MARGIN + 20
    y = c.y0 - 20
    paper = [shape([x0 - 10, y, x1 - x0 + 20, c.y1 - y + 10], PAPER, name="Paper", shadow=True)]
    channel = c.texts.get("channel") or "Notícias"
    body = [text(c, channel, [x0 + 20, y + 20, x1 - x0 - 40, 120], 110, 40, lines=1, align="center", color=ink,
                 upper=True, name="Masthead"),
            shape([x0 + 20, y + 150, x1 - x0 - 40, 5], color=ink, name="Rule"),
            text(c, f"{time.strftime('%d/%m/%Y')}  ·  EDIÇÃO DIGITAL", [x0 + 20, y + 160, x1 - x0 - 40, 40], 26, 14,
                 role="body", lines=1, align="center", color=ink, name="Edition", element="label"),
            shape([x0 + 20, y + 206, x1 - x0 - 40, 2], color=ink, name="Rule"),
            text(c, (d.get("kicker") or "").upper(), [x0 + 20, y + 230, x1 - x0 - 40, 44], 32, 16, lines=1,
                 color=c.c["breaking"][0], name="Kicker", element="tab"),
            text(c, d["headline"], [x0 + 20, y + 280, x1 - x0 - 40, int(c.ch * 0.42)], 96, 32, lines=5, color=ink,
                 name="Headline", valign="top", spacing=-0.08)]
    sub = (d.get("subhead") or "").split()
    if sub:
        half = (len(sub) + 1) // 2
        cy = y + 300 + int(c.ch * 0.42)
        cw = (x1 - x0 - 40 - 40) // 2
        ch = c.y1 - 30 - cy
        body += [shape([x0 + 20, cy - 16, x1 - x0 - 40, 2], color=ink, name="Rule"),
                 text(c, " ".join(sub[:half]), [x0 + 20, cy, cw, ch], 36, 18, role="body", lines=6, color=ink,
                      valign="top", name="Column 1", element="subhead", spacing=0.05),
                 shape([x0 + 20 + cw + 18, cy, 2, ch], color=ink, name="Column rule"),
                 text(c, " ".join(sub[half:]), [x0 + 60 + cw, cy, cw, ch], 36, 18, role="body", lines=6, color=ink,
                      valign="top", name="Column 2", element="subhead", spacing=0.05)]
    return frame(c, d, body, before=paper)
