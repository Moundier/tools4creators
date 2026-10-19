"""Text op: an editable GIMP text layer, auto-fitted into a box (runs inside GIMP). From mini-studio's
thumbnails, plus greedy wrapping for long texts (quotes, opinions), where trying every split would be too slow.

op: text, box [x, y, w, h], font, color, max_size, min_size, max_lines, align left/center/right,
valign top/middle/bottom, upper (default False), line_spacing (factor), letter_spacing, shadow, name.
"""
import itertools

import gi
gi.require_version("Gimp", "3.0")
from gi.repository import Gimp

from gimp_helpers import PX, add_shadow, color, perceptual

BALANCED_MAX_WORDS = 9   # up to this many words: try every split for the most even lines (titles)


def split_lines(words, n):
    """Split words into n lines with the most balanced lengths (the longest line as short as possible)."""
    if n == 1:
        return [" ".join(words)]
    best, best_score = None, None
    for cuts in itertools.combinations(range(1, len(words)), n - 1):
        bounds = (0,) + cuts + (len(words),)
        lines = [" ".join(words[a:b]) for a, b in zip(bounds, bounds[1:])]
        lens = [len(l) for l in lines]
        score = (max(lens), -min(lens))
        if best_score is None or score < best_score:
            best, best_score = lines, score
    return best


def greedy_lines(words, font, size, width):
    """Wrap words to `width` px at `size`, measured with Pango (the same layout GIMP draws)."""
    lines, line = [], ""
    for word in words:
        test = f"{line} {word}".strip()
        if not line or Gimp.text_get_extents_font(test, size, font)[1] <= width:
            line = test
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def op_text(img, op, job):
    text = " ".join(str(op.get("text", "")).split())
    if not text:
        return
    if op.get("upper"):
        text = text.upper()
    bx, by, bw, bh = op["box"]
    font = Gimp.Font.get_by_name(op.get("font") or "Montserrat Bold") or Gimp.Font.get_by_name("Sans-serif Bold")
    words = text.split()
    ls_factor = op.get("line_spacing", -0.12)
    max_lines = op.get("max_lines", 3)

    layer = Gimp.TextLayer.new(img, "x", font, 10, PX)
    img.insert_layer(layer, None, 0)
    perceptual(layer)
    layer.set_name(op.get("name") or "Text: " + text[:40])
    layer.set_color(color(op.get("color", "#FFFFFF")))
    if op.get("letter_spacing"):
        layer.set_letter_spacing(float(op["letter_spacing"]))
    layer.set_justification({"left": Gimp.TextJustification.LEFT, "center": Gimp.TextJustification.CENTER,
                             "right": Gimp.TextJustification.RIGHT}[op.get("align", "left")])

    def measure(lines, size):
        layer.set_font_size(size, PX)
        layer.set_line_spacing(size * ls_factor)
        layer.set_text("\n".join(lines))
        return layer.get_width(), layer.get_height()

    def fits(lines, size):
        if len(lines) > max_lines:
            return False
        w, h = measure(lines, size)
        return w <= bw and h <= bh

    min_size, max_size = int(op.get("min_size", 24)), int(op.get("max_size", 120))
    best = None
    if len(words) <= BALANCED_MAX_WORDS:   # titles: most even split per line count, biggest size wins
        for n in range(1, min(max_lines, len(words)) + 1):
            lines = split_lines(words, n)
            lo, hi, fit = min_size, max_size, None
            while lo <= hi:
                mid = (lo + hi) // 2
                if fits(lines, mid):
                    fit, lo = mid, mid + 1
                else:
                    hi = mid - 1
            if fit and (best is None or fit > best[0] * 1.08):  # prefer fewer lines unless clearly bigger
                best = (fit, lines)
    else:                                  # long text: wrap at each size, biggest size that fits
        lo, hi = min_size, max_size
        while lo <= hi:
            mid = (lo + hi) // 2
            lines = greedy_lines(words, font, mid, bw)
            if fits(lines, mid):
                best, lo = (mid, lines), mid + 1
            else:
                hi = mid - 1
    if best is None:   # doesn't fit even at min_size: keep what fits and end with "…"
        lines = greedy_lines(words, font, min_size, bw)[:max_lines]
        lines[-1] = lines[-1].rstrip(".,;:") + "…"
        best = (min_size, lines)

    size, lines = best
    lw, lh = measure(lines, size)
    align, valign = op.get("align", "left"), op.get("valign", "middle")
    x = {"left": bx, "center": bx + (bw - lw) / 2, "right": bx + bw - lw}[align]
    y = {"top": by, "middle": by + (bh - lh) / 2, "bottom": by + bh - lh}[valign]
    layer.set_offsets(int(x), int(y))
    if op.get("shadow"):
        add_shadow(layer, 3, 5, 10, 0.7)
