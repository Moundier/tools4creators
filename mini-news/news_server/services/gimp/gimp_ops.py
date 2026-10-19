"""Image and shape ops for the news templates (runs inside GIMP).

Every op has the signature op_xxx(img, op, job) where `op` is one entry of a template's op list.
Shapes: "box" [x, y, w, h]; optional "slant" / "left_slant" (px the right / left edge leans), "round" (corner
radius), "stops" (1-3 colors, top -> bottom), "shine" (lighter top half), "shadow", "opacity", "name".
"""
import math

import gi
gi.require_version("Gimp", "3.0")
from gi.repository import Gimp

from gimp_helpers import add_shadow, apply_fade, color, fill_selection, gradient_fill, load_layer, new_layer


def _select_shape(img, op):
    x, y, w, h = op["box"]
    if op.get("points"):
        img.select_polygon(Gimp.ChannelOps.REPLACE, [float(v) for v in op["points"]])
    elif op.get("round"):
        r = min(op["round"], w / 2, h / 2)
        img.select_round_rectangle(Gimp.ChannelOps.REPLACE, x, y, w, h, r, r)
    elif op.get("slant") or op.get("left_slant"):
        s, ls = op.get("slant", 0), op.get("left_slant", 0)
        img.select_polygon(Gimp.ChannelOps.REPLACE, [float(v) for v in (x + ls, y, x + w, y, x + w - s, y + h, x, y + h)])
    else:
        img.select_rectangle(Gimp.ChannelOps.REPLACE, x, y, w, h)


def op_shape(img, op, job):
    """A filled shape: solid ("color") or vertical gradient ("stops")."""
    layer = new_layer(img, op.get("name", "Shape"), op.get("opacity", 100), mode=op.get("mode", "normal"))
    _select_shape(img, op)
    if op.get("stops"):
        gradient_fill(img, layer, op["stops"], op["box"][1], op["box"][1] + op["box"][3])
    else:
        fill_selection(img, layer, op["color"])
    if op.get("shine"):   # glossy top half, on its own layer so it can be hidden
        x, y, w, h = op["box"]
        gloss = new_layer(img, op.get("name", "Shape") + " shine", 15)
        _select_shape(img, op)
        img.select_rectangle(Gimp.ChannelOps.INTERSECT, x, y, w, int(h * 0.45))
        fill_selection(img, gloss, "#FFFFFF")
    if op.get("shadow"):
        add_shadow(layer, 4, 8, 16, 0.6)


def op_ellipse(img, op, job):
    x, y, w, h = op["box"]
    layer = new_layer(img, op.get("name", "Circle"), op.get("opacity", 100))
    img.select_ellipse(Gimp.ChannelOps.REPLACE, x, y, w, h)
    if op.get("ring"):
        r = op["ring"]
        img.select_ellipse(Gimp.ChannelOps.SUBTRACT, x + r, y + r, w - 2 * r, h - 2 * r)
    if op.get("stops"):
        gradient_fill(img, layer, op["stops"], y, y + h)
    else:
        fill_selection(img, layer, op["color"])
    if op.get("shadow"):
        add_shadow(layer, 3, 6, 12, 0.6)


def op_gradient(img, op, job):
    """`color` fading to transparent from `start` to `end` (canvas coords), e.g. a dark fade over a photo."""
    layer = new_layer(img, op.get("name", "Gradient"), op.get("opacity", 100), mode=op.get("mode", "normal"))
    if op.get("box"):
        img.select_rectangle(Gimp.ChannelOps.REPLACE, *op["box"])
    Gimp.context_set_foreground(color(op["color"]))
    Gimp.context_set_gradient_fg_transparent()
    (x1, y1), (x2, y2) = op["start"], op["end"]
    layer.edit_gradient_fill(Gimp.GradientType.LINEAR, 0, False, 1, 0, True, x1, y1, x2, y2)
    Gimp.Selection.none(img)


def op_stripes(img, op, job):
    """Faint diagonal stripes over the whole canvas (like a TV studio backdrop), or warning stripes in `box`."""
    x0, y0, bw, bh = op.get("box", [0, 0, img.get_width(), img.get_height()])
    layer = new_layer(img, op.get("name", "Stripes"), op.get("opacity", 4))
    step, width = op.get("step", 52), op.get("width", 16)
    Gimp.Selection.none(img)
    for i in range(-bh, bw + bh, step):
        pts = [x0 + i, y0 + bh, x0 + i + bh, y0, x0 + i + bh + width, y0, x0 + i + width, y0 + bh]
        img.select_polygon(Gimp.ChannelOps.ADD, [float(v) for v in pts])
    img.select_rectangle(Gimp.ChannelOps.INTERSECT, x0, y0, bw, bh)
    fill_selection(img, layer, op.get("color", "#FFFFFF"))


def op_image(img, op, job):
    """A picture file (photo, background, logo) in `box`: fit "cover" (fill + crop) or "contain"."""
    path = op.get("path")
    if not path:
        return
    bx, by, bw, bh = op["box"]
    layer = load_layer(img, path, op.get("name", "Image"))
    lw, lh = layer.get_width(), layer.get_height()
    s = (max if op.get("fit", "cover") == "cover" else min)(bw / lw, bh / lh)
    w, h = max(1, math.ceil(lw * s)), max(1, math.ceil(lh * s))
    layer.scale(w, h, False)
    align = op.get("align", "center")
    x = {"left": bx, "center": bx + (bw - w) / 2, "right": bx + bw - w}[align]
    y = by + (bh - h) / (3 if op.get("fit", "cover") == "cover" else 2)   # cover: a bit above center (faces)
    layer.set_offsets(int(x), int(y))
    if op.get("fit", "cover") == "cover":    # clip to the box
        layer.resize_to_image_size()
        if op.get("round"):
            r = min(op["round"], bw / 2, bh / 2)
            img.select_round_rectangle(Gimp.ChannelOps.REPLACE, bx, by, bw, bh, r, r)
        else:
            img.select_rectangle(Gimp.ChannelOps.REPLACE, bx, by, bw, bh)
        Gimp.Selection.invert(img)
        if not Gimp.Selection.is_empty(img):   # empty selection = edit_clear would wipe the whole layer
            layer.edit_clear()
        Gimp.Selection.none(img)
    if op.get("opacity") is not None:
        layer.set_opacity(float(op["opacity"]))
    if op.get("desaturate"):
        layer.desaturate(Gimp.DesaturateMode.LUMINANCE)
    if op.get("fade"):
        apply_fade(layer, op["fade"])
    if op.get("shadow"):
        add_shadow(layer, 4, 8, 16, 0.6)
