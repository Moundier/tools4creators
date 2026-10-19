"""'Magazines' op: fake magazine covers from the news images (photo, masthead, two-line headline), warped
in fake perspective and scattered over the canvas (runs inside GIMP).

Headline: a small line on top (t1) and a big line under it (t2) stretched to t1's width, e.g.
"DISCO POLEMICO DE / GTA VI". Fonts, colors and the spot (top / middle) vary per cover: a controlled
random (shuffled lists, so neighbors differ). Each render gives a new wall; the same seed gives the same one."""
import math
import random

import gi
gi.require_version("Gimp", "3.0")
from gi.repository import Gimp, Gio

from gimp_helpers import PX, W, H, add_shadow, color, fill_selection, new_layer
from gimp_text import op_text

PAGE_W, PAGE_H = 360, 480
MASTHEADS = ["GAMER", "PLAY", "PIXEL", "NERD", "LEVEL", "JOGO", "ARCADE", "BOSS"]
MASTHEAD_COLORS = ["#FFFFFF", "#FFD400", "#FF2E2E", "#FFFFFF", "#33E1FF"]
# (small line font, big line font)
FONT_PAIRS = [("Oswald Bold", "Anton Regular"), ("Barlow Condensed Bold", "Bebas Neue Regular"),
              ("Montserrat ExtraBold", "Archivo Black Regular"), ("Oswald Bold", "Playfair Display Black"),
              ("Barlow Condensed Bold", "Montserrat Black"), ("Montserrat ExtraBold", "Bebas Neue Regular")]
# (small line color, big line color)
COLOR_PAIRS = [("#FFFFFF", "#FFD400"), ("#FFD400", "#FFFFFF"), ("#FFFFFF", "#FF3030"), ("#33E1FF", "#FFFFFF"),
               ("#FFFFFF", "#7CFF4F"), ("#FF5FA8", "#FFFFFF"), ("#FFD400", "#FF3030")]
SPOTS = ["top", "middle"]


def split_headline(text):
    """'DISCO POLEMICO DE / GTA VI' -> ('DISCO POLEMICO DE', 'GTA VI'). Without '/': the last word is the big
    line (the last two when it is tiny, like 'VI')."""
    text = " ".join(text.upper().split())
    if "/" in text:
        head, tail = text.split("/", 1)
        return head.strip(), tail.replace("/", " ").strip()
    words = text.split()
    if len(words) < 2:
        return "", text
    n = 2 if len(words[-1]) <= 2 and len(words) > 2 else 1
    return " ".join(words[:-n]), " ".join(words[-n:])


def text_layer(page, text, font, size, ink):
    t = Gimp.TextLayer.new(page, text, Gimp.Font.get_by_name(font) or Gimp.Font.get_by_name("Sans-serif Bold"),
                           size, PX)
    page.insert_layer(t, None, 0)
    t.set_color(color(ink))
    return t


def ink(page, t):
    """(x, y, h) of the visible glyphs, relative to the text layer."""
    t.set_offsets(0, 0)
    page.select_item(Gimp.ChannelOps.REPLACE, t)
    _, _, x1, y1, x2, y2 = Gimp.Selection.bounds(page)
    Gimp.Selection.none(page)
    return x1, y1, y2 - y1


def headline(page, text, style):
    """Small t1 over big t2, t2 sized so both lines are equally wide; at the top or in the middle."""
    t1_text, t2_text = split_headline(text)
    if not t2_text:
        return
    (f1, f2), (c1, c2), spot = style["fonts"], style["colors"], style["spot"]
    maxw = PAGE_W - 44
    t1 = None
    if t1_text:
        t1 = text_layer(page, t1_text, f1, style["size"], c1)
        if t1.get_width() > maxw:  # long small line: shrink it to the page
            t1.set_font_size(style["size"] * maxw / t1.get_width(), PX)
    width = t1.get_width() if t1 else maxw * 0.8
    t2 = text_layer(page, t2_text, f2, 100, c2)
    size = 100.0
    for _ in range(3):  # text width is ~linear in the size: converge on t1's width
        size *= width / max(1, t2.get_width())
        size = min(size, PAGE_H * 0.3)  # a one-word line can't get taller than this
        t2.set_font_size(size, PX)
    # stack by the visible letters (not the text boxes, which carry the font's line spacing): small gap
    _, y1, h1 = ink(page, t1) if t1 else (0, 0, 0)
    _, y2, h2 = ink(page, t2)
    gap = max(4, round(h2 * 0.08)) if t1 else 0
    block = h1 + gap + h2
    top = 30 if spot == "top" else (PAGE_H - block) / 2
    if t1:
        t1.set_offsets(int((PAGE_W - t1.get_width()) / 2), int(top - y1))
    t2.set_offsets(int((PAGE_W - t2.get_width()) / 2), int(top + h1 + gap - y2))
    for t in filter(None, (t1, t2)):
        add_shadow(t, 2, 3, 6, 0.9)


def cover(news, i, rnd, style):
    """A flat magazine cover in its own small image; returns that image (caller deletes it)."""
    page = Gimp.Image.new(PAGE_W, PAGE_H, Gimp.ImageBaseType.RGB)
    paper = new_layer(page, "Paper")
    Gimp.Selection.all(page)
    fill_selection(page, paper, "#F4F1EA")
    photo = Gimp.file_load_layer(Gimp.RunMode.NONINTERACTIVE, page, Gio.File.new_for_path(news["path"]))
    page.insert_layer(photo, None, 0)
    lw, lh = photo.get_width(), photo.get_height()
    s = max(PAGE_W / lw, PAGE_H / lh)  # cover the page
    w, h = math.ceil(lw * s), math.ceil(lh * s)
    photo.scale(w, h, False)
    photo.set_offsets((PAGE_W - w) // 2, (PAGE_H - h) // 2)
    if style["spot"] == "middle":  # the masthead only fits when the headline isn't at the top
        op_text(page, {"text": MASTHEADS[i % len(MASTHEADS)], "box": [14, 8, PAGE_W - 28, 92],
                       "font": "Anton Regular", "color": rnd.choice(MASTHEAD_COLORS), "align": "center",
                       "valign": "top", "max_size": 110, "max_lines": 1, "letter_spacing": 2}, None)
    headline(page, news.get("title", ""), style)
    # thin paper edge
    edge = new_layer(page, "Edge")
    Gimp.Selection.all(page)
    page.select_rectangle(Gimp.ChannelOps.SUBTRACT, 5, 5, PAGE_W - 10, PAGE_H - 10)
    fill_selection(page, edge, "#F4F1EA")
    return page


def styles(rnd, n):
    """n cover styles: each list is shuffled and cycled, so consecutive covers never repeat a combination."""
    def cycle(items):
        items = list(items)
        rnd.shuffle(items)
        return [items[i % len(items)] for i in range(n)]
    spots = cycle(SPOTS * 3)
    return [{"fonts": f, "colors": c, "spot": s, "size": rnd.choice([28, 32, 36])}
            for f, c, s in zip(cycle(FONT_PAIRS), cycle(COLOR_PAIRS), spots)]


def quad(cx, cy, scale, rnd):
    """Corners (tl, tr, bl, br) of a page turned and tilted in fake 3D: rotated, with one side shorter
    (keystone) and a little shear, like a magazine lying at an angle."""
    hw, hh = PAGE_W * scale / 2, PAGE_H * scale / 2
    a = math.radians(rnd.uniform(-16, 16))
    k = rnd.uniform(0.66, 0.86)          # the far side is this much shorter
    near_left = rnd.random() < 0.5
    kl, kr = (1.0, k) if near_left else (k, 1.0)
    shear = rnd.uniform(-0.18, 0.18) * hw
    pts = [(-hw + shear, -hh * kl), (hw + shear, -hh * kr), (-hw - shear, hh * kl), (hw - shear, hh * kr)]
    ca, sa = math.cos(a), math.sin(a)
    return [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in pts]


def assign(rnd, cells, n_news):
    """Which news goes in each grid cell: every news about as often as the others, and never the same news
    as the cell to the left or above."""
    pool = []
    while len(pool) < len(cells):
        batch = list(range(n_news))
        rnd.shuffle(batch)
        pool += batch
    got = {}
    for r, c in cells:
        near = {got.get((r, c - 1)), got.get((r - 1, c))}
        k = next((k for k, v in enumerate(pool) if v not in near), 0)
        got[(r, c)] = pool.pop(k)
    return got


def op_magazines(img, op, job):
    """Covers on a jittered grid that covers the canvas, plus a few extra ones on top. A new arrangement on
    every render (job["seed"]): positions, sizes, turns, which news goes where and each cover's style all
    change, within limits that keep the wall full and varied."""
    news = [n for n in job.get("magazines", []) if n.get("path")]
    if not news:
        return
    rnd = random.Random(job.get("seed", 0) * 7919 + op.get("seed", 0))
    cols, rows = op.get("cols", 5), op.get("rows", 2)
    cells = [(r, c) for r in range(rows) for c in range(cols)]
    which = assign(rnd, cells, len(news))
    cw, ch = W / cols, H / rows
    base = op.get("scale", 0.92)
    def jitter(i, n, amount):
        """Random shift near the cell; on the first / last column (or row) only outward, so no corner shows."""
        if i == 0:
            return rnd.uniform(-amount, 0)
        if i == n - 1:
            return rnd.uniform(0, amount)
        return rnd.uniform(-amount, amount)

    def corner(r, c):
        return r in (0, rows - 1) and c in (0, cols - 1)

    slots = [((c + 0.5) * cw + jitter(c, cols, 0.18) * cw,
              (r + 0.5) * ch + (jitter(r, rows, 0.12) if corner(r, c) else rnd.uniform(-0.06, 0.06)) * ch,
              base * rnd.uniform(1.0 if corner(r, c) else 0.82, 1.15),  # corner covers stay big
              which[(r, c)]) for r, c in cells]
    extra = list(range(len(news)))
    rnd.shuffle(extra)
    slots += [(rnd.uniform(0.1, 0.9) * W, rnd.uniform(0.15, 0.85) * H, base * rnd.uniform(0.75, 0.95),
               extra[k % len(extra)]) for k in range(op.get("extra", 3))]
    rnd.shuffle(slots)  # drawing order = which cover lies on top

    group = Gimp.GroupLayer.new(img, "Magazines")
    img.insert_layer(group, None, 0)
    for i, ((cx, cy, scale, n), style) in enumerate(zip(slots, styles(rnd, len(slots)))):
        page = cover(news[n], i, rnd, style)  # one cover per slot: a repeated news gets a new look
        page.flatten()
        layer = Gimp.Layer.new_from_drawable(page.get_layers()[0], img)
        page.delete()
        layer.set_name("Magazine %d: %s" % (i + 1, news[n].get("title", "")[:30]))
        img.insert_layer(layer, group, 0)
        layer.set_offsets(0, 0)
        (x0, y0), (x1, y1), (x2, y2), (x3, y3) = quad(cx, cy, scale, rnd)
        layer = layer.transform_perspective(x0, y0, x1, y1, x2, y2, x3, y3)
        add_shadow(layer, 6, 10, 18, 0.7)
