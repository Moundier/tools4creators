"""Text ops: auto-fitting text boxes and stacked title ribbons (runs inside GIMP)."""
import html
import itertools
import math

import gi
gi.require_version("Gimp", "3.0")
from gi.repository import Gimp

from gimp_helpers import PX, W, add_shadow, color, fill_selection, new_layer


def split_lines(words, n):
    """Split words into n lines with the most balanced character counts.

    With 3 lines the middle one should be the longest (XBOX / TERA GRANDES / MUDANCAS, SHREK 5 / PRIMEIRO / TRAILER):
    a short hook on top, the long part in the middle. Splits shaped like that win; the rest is only a fallback.
    """
    if n == 1:
        return [" ".join(words)]
    best, best_score = None, None
    for cuts in itertools.combinations(range(1, len(words)), n - 1):
        bounds = (0,) + cuts + (len(words),)
        lines = [" ".join(words[a:b]) for a, b in zip(bounds, bounds[1:])]
        lens = [len(l.replace("*", "")) for l in lines]
        middle_longest = n == 3 and lens[1] >= max(lens)
        # middle line longest first, then the shortest longest line, then the most even
        score = (n == 3 and not middle_longest, max(lens), -min(lens))
        if best_score is None or score < best_score:
            best, best_score = lines, score
    return best


def to_markup(lines, base_hex, accent_hex):
    """'*word*' -> accent colored span. Asterisks may span several words."""
    out, in_accent = [], False
    for line in lines:
        parts = line.split("*")
        segs = []
        for i, part in enumerate(parts):
            if i > 0:
                in_accent = not in_accent
            if part:
                c = accent_hex if in_accent else base_hex
                segs.append('<span foreground="%s">%s</span>' % (c, html.escape(part)))
        out.append("".join(segs))
    return "\n".join(out)


def op_text(img, op, job):
    text = op["text"].strip()
    if not text:
        return
    if op.get("upper", True):
        text = text.upper()
    accent = op.get("accent")
    if accent and "*" not in text and op.get("auto_accent") == "last" and " " in text:
        head, last = text.rsplit(" ", 1)
        text = "%s *%s*" % (head, last)
    if not accent:
        text = text.replace("*", "")
    parts = None
    if op.get("parts"):  # "1996|VERY RARE|ENGLISH SUBTITLES" -> colored segments on one line
        parts = [p.strip() for p in text.split("|") if p.strip()]
        text = "  |  ".join(parts)

    forced = None
    if not parts and "/" in text:  # "ONIMUSHA E / O MEU GOTY" -> fixed line breaks
        forced = [l.strip() for l in text.split("/") if l.strip()]
        text = " ".join(forced)

    bx, by, bw, bh = op["box"]
    font = Gimp.Font.get_by_name(op["font"]) or Gimp.Font.get_by_name("Sans-serif Bold")
    words = [text] if parts else text.split()
    outline = op.get("outline", 0)
    ls_factor = op.get("line_spacing", -0.3)

    layer = Gimp.TextLayer.new(img, "x", font, 10, PX)
    img.insert_layer(layer, None, 0)
    layer.set_name("Text: " + text.replace("*", "")[:40])
    layer.set_color(color(op.get("color", "#FFFFFF")))
    if op.get("letter_spacing"):
        layer.set_letter_spacing(float(op["letter_spacing"]))
    layer.set_justification({"left": Gimp.TextJustification.LEFT, "center": Gimp.TextJustification.CENTER,
                             "right": Gimp.TextJustification.RIGHT}[op.get("justify", op.get("align", "left"))])
    if outline:
        layer.set_outline(Gimp.TextOutline.STROKE_FILL)
        layer.set_outline_direction(Gimp.TextOutlineDirection.OUTER)
        layer.set_outline_width(float(outline), PX)
        layer.set_outline_color(color(op.get("outline_color", "#000000")))
        layer.set_outline_join_style(Gimp.JoinStyle.ROUND)

    def measure(lines, size):
        layer.set_font_size(size, PX)
        layer.set_line_spacing(size * ls_factor)
        layer.set_text("\n".join(lines).replace("*", ""))
        return layer.get_width() + 2 * outline, layer.get_height() + 2 * outline

    # pick the line count + font size that gives the biggest text inside the box
    best = None
    min_size, max_size = op.get("min_size", 24), op.get("max_size", 120)
    options = [forced] if forced else [split_lines(words, n)
                                        for n in range(1, min(op.get("max_lines", 3), len(words)) + 1)]
    for lines in options:
        lo, hi, fit = min_size, max_size, None
        while lo <= hi:
            mid = (lo + hi) // 2
            w, h = measure(lines, mid)
            if w <= bw and h <= bh:
                fit, lo = mid, mid + 1
            else:
                hi = mid - 1
        if fit and (best is None or fit > best[0] * 1.08):  # prefer fewer lines unless clearly bigger
            best = (fit, lines)
    if best is None:
        best = (min_size, options[-1])

    size, lines = best
    if op.get("manual_breaks") and not forced and not parts:  # no '/': one line, at the size the auto
        lines = [" ".join(words)]                             # split would get (may overflow the box)
    measure(lines, size)
    if accent:
        layer.set_markup(to_markup(lines, op.get("color", "#FFFFFF"), accent))
    if parts:
        cols, sep = op["parts"], '<span foreground="%s">  |  </span>' % op.get("color", "#FFFFFF")
        layer.set_markup(sep.join('<span foreground="%s">%s</span>' % (cols[i % len(cols)], html.escape(p))
                                  for i, p in enumerate(parts)))
    lw, lh = layer.get_width(), layer.get_height()
    align, valign = op.get("align", "left"), op.get("valign", "middle")
    x = {"left": bx + outline, "center": bx + (bw - lw) / 2, "right": bx + bw - lw - outline}[align]
    y = {"top": by + outline, "middle": by + (bh - lh) / 2, "bottom": by + bh - lh - outline}[valign]
    layer.set_offsets(int(x), int(y))
    if op.get("backdrop"):
        draw_backdrop(img, layer, op["backdrop"])
    if op.get("shadow"):
        add_shadow(layer, 5, 7, 10, 0.75)


def draw_backdrop(img, layer, bd):
    """Rounded box hugging the visible letters of a text layer, drawn right below it.
    bd: color, pad [x, y], round, bleed_right (box runs off the right edge: square corners there),
    underline {color, height, gap} (a line under the last line, inside the box), shadow."""
    img.select_item(Gimp.ChannelOps.REPLACE, layer)
    _, _, x1, y1, x2, y2 = Gimp.Selection.bounds(img)
    padx, pady = bd.get("pad", [20, 12])
    r = bd.get("round", 0)
    ul = bd.get("underline")
    left, top = x1 - padx, y1 - pady
    right = W + r if bd.get("bleed_right") else x2 + padx  # corners past the canvas edge are cut off
    bottom = y2 + (ul["gap"] + ul["height"] if ul else 0) + pady
    pos = img.get_item_position(layer) + 1
    box = new_layer(img, "Text box", bd.get("opacity", 100), position=pos)
    img.select_round_rectangle(Gimp.ChannelOps.REPLACE, left, top, right - left, bottom - top, r, r)
    fill_selection(img, box, bd["color"])
    if ul:
        line = new_layer(img, "Underline", position=pos)  # above the box, below the text
        img.select_rectangle(Gimp.ChannelOps.REPLACE, x1, y2 + ul["gap"], x2 - x1, ul["height"])
        fill_selection(img, line, ul["color"])
    Gimp.Selection.none(img)
    if bd.get("shadow"):
        add_shadow(box, 4, 6, 10, 0.5)


def ribbon_markup(line, ink, small_words, highlight=None, in_hl=False):
    """One ribbon's text. With `highlight`, '*words*' get that color (in_hl: a '*' span opened on an earlier line)."""
    out = []
    for word in line.split(" "):
        if word.upper().replace("*", "") in small_words:
            out.append('<span size="62%%">%s</span>' % html.escape(word.lower().replace("*", "")))
            continue
        segs = []
        for i, part in enumerate(word.split("*")):
            if i > 0:
                in_hl = not in_hl
            if part:
                segs.append('<span foreground="%s">%s</span>' % (highlight, html.escape(part)) if in_hl
                            else html.escape(part))
        out.append("".join(segs))
    return '<span foreground="%s">%s</span>' % (ink, " ".join(out))


def draw_warning(img, group, x0, x1, top, height):
    """Yellow warning sign (black rim, "!") filling the gap [x0, x1) left of line 1's ribbon,
    standing on the ribbon's bottom edge (a tall sign sticks out above it)."""
    size = (x1 - x0) * 0.94
    cx, base = (x0 + x1) / 2 - (x1 - x0) * 0.03, top + height
    layer = new_layer(img, "Warning sign", position=0, parent=group)

    def tri(s, b, r):
        img.select_polygon(Gimp.ChannelOps.REPLACE, [cx, b - s * 0.87, cx + s / 2, b, cx - s / 2, b])
        Gimp.Selection.shrink(img, r)
        Gimp.Selection.grow(img, r)

    tri(size, base, max(2, int(size * 0.06)))
    fill_selection(img, layer, "#111111")
    inner = size * 0.74
    tri(inner, base - size * 0.07, max(1, int(size * 0.04)))
    fill_selection(img, layer, "#FFD400")
    bar_w = max(3, size * 0.09)  # the "!": a bar and a dot
    img.select_rectangle(Gimp.ChannelOps.REPLACE, cx - bar_w / 2, base - size * 0.6, bar_w, size * 0.3)
    fill_selection(img, layer, "#111111")
    img.select_ellipse(Gimp.ChannelOps.REPLACE, cx - bar_w * 0.6, base - size * 0.24, bar_w * 1.2, bar_w * 1.2)
    fill_selection(img, layer, "#111111")
    Gimp.Selection.none(img)


def op_ribbons(img, op, job):
    """Stacked title ribbons: each line is a text layer on a box sized to the text.

    `/` in the text separates ribbons; otherwise the words are split into balanced lines.
    The stack is anchored at the bottom-left of `box` (`align: "center"` centers each line), then tilted
    as one layer group. `highlight` colors '*words*'; a style with `"box": None` draws text only.
    """
    text = op["text"].strip()
    if not text:
        return
    highlight = op.get("highlight")
    text = text.upper() if highlight else text.upper().replace("*", "")
    styles = op["styles"]
    style = lambda i: styles[min(i, len(styles) - 1)]
    small_words = [w.upper() for w in op.get("small_words", [])]
    bx, by, bw, bh = op["box"]
    padx, pady = op.get("pad", [24, 14])
    offsets = op.get("x_offsets", [0])
    accent = op.get("accent")  # {"color": ..., "width": px}: vertical bar left of the whole stack
    aw = accent["width"] if accent else 0
    font = Gimp.Font.get_by_name(op.get("font", "Montserrat Black"))

    group = Gimp.GroupLayer.new(img, "Title ribbons")
    img.insert_layer(group, None, 0)

    def ink_box(t):
        """Visible glyph bounds (x, y, w, h) relative to the text layer."""
        t.set_offsets(0, 0)
        img.select_item(Gimp.ChannelOps.REPLACE, t)
        _, _, x1, y1, x2, y2 = Gimp.Selection.bounds(img)
        Gimp.Selection.none(img)
        return x1, y1, x2 - x1, y2 - y1

    def fit(lines):
        """Text layers for `lines`, sized as big as the box allows. Returns (texts, sizes, boxes)."""
        texts = []
        # is a '*' highlight span still open at the start of each line?
        opens = [sum(l.count("*") for l in lines[:i]) % 2 == 1 for i in range(len(lines))]
        for i, line in enumerate(lines):
            t = Gimp.TextLayer.new(img, line.replace("*", ""), font, 10, PX)
            img.insert_layer(t, group, 0)
            t.set_name("Ribbon text: " + line.replace("*", "")[:40])
            st = style(i)
            if st.get("outline"):
                t.set_outline(Gimp.TextOutline.STROKE_FILL)
                t.set_outline_direction(Gimp.TextOutlineDirection.OUTER)
                t.set_outline_width(float(st["outline"]), PX)
                t.set_outline_color(color(st.get("outline_color", "#000000")))
                t.set_outline_join_style(Gimp.JoinStyle.ROUND)
            texts.append(t)

        def set_size(i, size):
            texts[i].set_font_size(size, PX)
            texts[i].set_markup(ribbon_markup(lines[i], style(i)["text"], small_words, highlight, opens[i]))

        # biggest size per line that fits the width;
        # shrink everything until the stack fits the height
        max_size = op.get("max_size", 120)
        for _ in range(12):
            sizes, boxes = [], []
            for i in range(len(lines)):
                avail = bw - aw - offsets[min(i, len(offsets) - 1)] - 2 * padx
                lo, hi, best = op.get("min_size", 24), int(max_size * style(i).get("scale", 1.0)), None
                while lo <= hi:
                    mid = (lo + hi) // 2
                    set_size(i, mid)
                    if texts[i].get_width() <= avail:
                        best, lo = mid, mid + 1
                    else:
                        hi = mid - 1
                sizes.append(best or op.get("min_size", 24))
            if op.get("same_size"):  # every line at the size of the longest one
                sizes = [min(sizes)] * len(lines)
            for i in range(len(lines)):
                set_size(i, sizes[i])
                boxes.append(ink_box(texts[i]))
            total = sum(b[3] + 2 * pady for b in boxes) + op.get("gap", 0) * (len(lines) - 1)
            if total <= bh:
                break
            max_size *= max(0.6, bh / total * 0.98)
        return texts, sizes, boxes

    if "/" in text:
        lines = [l.strip() for l in text.split("/") if l.strip()][:op.get("max_lines", 3)]
        texts, sizes, boxes = fit(lines)
    else:  # try 1..auto_lines lines, keep the one with the biggest text (fewer lines unless clearly bigger)
        words, best = text.split(), None
        for n in range(1, min(op.get("auto_lines", 3), op.get("max_lines", 3), len(words)) + 1):
            cand = split_lines(words, n)
            texts, sizes, boxes = fit(cand)
            if best is None or min(sizes) > min(best[2]) * 1.12:
                if best:
                    for t in best[1]:
                        img.remove_layer(t)
                best = (cand, texts, sizes, boxes)
            else:
                for t in texts:
                    img.remove_layer(t)
        lines, texts, sizes, boxes = best

    # lay out bottom-up
    cur = by + bh
    for i in reversed(range(len(lines))):
        ix, iy, iw, ih = boxes[i]
        st = style(i)
        bh_i = ih + 2 * pady
        top = cur - bh_i
        left = bx + aw + offsets[min(i, len(offsets) - 1)]
        if op.get("align") == "center":
            left = bx + aw + (bw - aw - iw - 2 * padx) / 2
        lead = i == 0 and op.get("lead_icon")  # icon before line 1's text (sizes and breaks untouched)
        if lead:
            gap = op.get("lead_gap", 150)
            draw_warning(img, group, left, left + gap, top, bh_i)
            left += gap
        if op.get("bleed_left"):  # box runs off the left edge of the canvas (behind the lead icon too)
            box_x, box_w = -20, left + iw + 2 * padx + 20
        else:
            box_x, box_w = left, iw + 2 * padx
        if st["box"]:
            rect = new_layer(img, "Ribbon box %d" % (i + 1), st.get("opacity", 100),
                             position=len(group.get_children()), parent=group)
            img.select_rectangle(Gimp.ChannelOps.REPLACE, box_x, top, box_w, bh_i)
            fill_selection(img, rect, st["box"])
        texts[i].set_offsets(int(left + padx - ix), int(top + pady - iy))
        cur = top - op.get("gap", 0)
    if accent:
        stack_top = cur + op.get("gap", 0)
        bar = new_layer(img, "Ribbon accent", position=len(group.get_children()), parent=group)
        img.select_rectangle(Gimp.ChannelOps.REPLACE, bx, stack_top, aw, by + bh - stack_top)
        fill_selection(img, bar, accent["color"])

    if op.get("tilt"):
        group.transform_rotate(math.radians(op["tilt"]), True, 0, 0)
    if op.get("shadow"):
        add_shadow(group, 6, 8, 12, 0.6)
