"""Image and shape ops: background, rect, poly, ellipse, gradient, arrow, person, image, matrix (runs inside GIMP).

Every op has the signature op_xxx(img, op, job) where `op` is one entry of a template's op list.
"""
import math
import os
import random

import gi
gi.require_version("Gimp", "3.0")
from gi.repository import Gimp

from gimp_helpers import W, H, PX, add_shadow, apply_fade, color, fill_selection, finish_shape, load_layer, new_layer


def op_background(img, op, job):
    x, y, bw, bh = op.get("box", [0, 0, W, H])
    layer = load_layer(img, job["bg"], "Background photo")
    lw, lh = layer.get_width(), layer.get_height()
    s = max(bw / lw, bh / lh)  # scale to cover
    nw, nh = math.ceil(lw * s), math.ceil(lh * s)
    layer.scale(nw, nh, False)
    layer.set_offsets(int(x + (bw - nw) / 2), int(y + (bh - nh) / 2))
    layer.resize_to_image_size()
    if op.get("ellipse"):  # photo inside a circle / ellipse filling `box`
        img.select_ellipse(Gimp.ChannelOps.REPLACE, x, y, bw, bh)
        Gimp.Selection.invert(img)
        layer.edit_clear()
        Gimp.Selection.none(img)
    elif [x, y, bw, bh] != [0, 0, W, H]:
        if op.get("round"):  # rounded panel
            img.select_round_rectangle(Gimp.ChannelOps.REPLACE, x, y, bw, bh, op["round"], op["round"])
        else:
            img.select_rectangle(Gimp.ChannelOps.REPLACE, x, y, bw, bh)
        Gimp.Selection.invert(img)
        layer.edit_clear()
        Gimp.Selection.none(img)
    if op.get("desaturate"):
        layer.desaturate(Gimp.DesaturateMode.LUMINANCE)
    if op.get("fade"):
        apply_fade(layer, op["fade"])
    if op.get("blur"):
        f = Gimp.DrawableFilter.new(layer, "gegl:gaussian-blur", "Blur")
        cfg = f.get_config()
        cfg.set_property("std-dev-x", float(op["blur"]))
        cfg.set_property("std-dev-y", float(op["blur"]))
        cfg.set_property("abyss-policy", "clamp")
        f.update()
        layer.append_filter(f)
    if op.get("darken"):
        dark = new_layer(img, "Darken", opacity=op["darken"] * 100)
        img.select_rectangle(Gimp.ChannelOps.REPLACE, x, y, bw, bh)
        fill_selection(img, dark, "#000000")


def op_rect(img, op, job):
    layer = new_layer(img, op.get("name", "Rectangle"), op.get("opacity", 100), mode=op.get("mode", "normal"))
    img.select_rectangle(Gimp.ChannelOps.REPLACE, *op["box"])
    fill_selection(img, layer, op["color"])
    finish_shape(img, layer, op)


def op_poly(img, op, job):
    """Filled polygon; with `color2` it fades left to right from `color` to `color2`."""
    layer = new_layer(img, op.get("name", "Shape"), op.get("opacity", 100))

    def select():
        img.select_polygon(Gimp.ChannelOps.REPLACE, [float(v) for v in op["points"]])
        if op.get("round"):  # shrink + grow = rounded corners
            Gimp.Selection.shrink(img, op["round"])
            Gimp.Selection.grow(img, op["round"])

    select()
    if op.get("color2"):  # exact color -> color2 across the shape's width
        xs = op["points"][0::2]
        Gimp.context_set_foreground(color(op["color"]))
        Gimp.context_set_background(color(op["color2"]))
        Gimp.context_set_gradient_fg_bg_rgb()
        layer.edit_gradient_fill(Gimp.GradientType.LINEAR, 0, False, 1, 0, True, min(xs), 0, max(xs), 0)
        Gimp.Selection.none(img)
    else:
        fill_selection(img, layer, op["color"])
    finish_shape(img, layer, op)


def op_ellipse(img, op, job):
    x, y, w, h = op["box"]
    layer = new_layer(img, op.get("name", "Circle"), op.get("opacity", 100))
    img.select_ellipse(Gimp.ChannelOps.REPLACE, x, y, w, h)
    if op.get("ring"):
        r = op["ring"]
        img.select_ellipse(Gimp.ChannelOps.SUBTRACT, x + r, y + r, w - 2 * r, h - 2 * r)
    fill_selection(img, layer, op["color"])
    finish_shape(img, layer, op)


def op_gradient(img, op, job):
    layer = new_layer(img, op.get("name", "Gradient"), op.get("opacity", 100), mode=op.get("mode", "normal"))
    Gimp.context_set_foreground(color(op["color"]))
    Gimp.context_set_gradient_fg_transparent()
    (x1, y1), (x2, y2) = op["start"], op["end"]
    layer.edit_gradient_fill(Gimp.GradientType.LINEAR, 0, False, 1, 0, True, x1, y1, x2, y2)


def op_arrow(img, op, job):
    """Straight arrow from `start` to `end`; with `via` the shaft bends (quadratic curve through `via`)."""
    (x0, y0), (x1, y1) = op["start"], op["end"]
    cx, cy = op.get("via", [(x0 + x1) / 2, (y0 + y1) / 2])
    w = op.get("width", 36)
    head_len, head_w = w * 2.0, w * 2.4
    length = math.hypot(x1 - cx, y1 - cy)
    ux, uy = (x1 - cx) / length, (y1 - cy) / length  # direction at the tip
    bx, by = x1 - ux * head_len, y1 - uy * head_len   # base of the head
    # shaft: sample the curve start -> head base, offset both sides by half the width
    left, right = [], []
    n = 24 if "via" in op else 1
    for i in range(n + 1):
        t = i / n
        px = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * bx
        py = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * by
        dx = 2 * (1 - t) * (cx - x0) + 2 * t * (bx - cx)
        dy = 2 * (1 - t) * (cy - y0) + 2 * t * (by - cy)
        d = math.hypot(dx, dy) or 1
        nx, ny = -dy / d, dx / d
        left.append((px + nx * w / 2, py + ny * w / 2))
        right.append((px - nx * w / 2, py - ny * w / 2))
    nx, ny = -uy, ux
    head = [(bx + nx * head_w / 2, by + ny * head_w / 2), (x1, y1), (bx - nx * head_w / 2, by - ny * head_w / 2)]
    pts = left + head + right[::-1]
    layer = new_layer(img, op.get("name", "Arrow"), op.get("opacity", 100))
    img.select_polygon(Gimp.ChannelOps.REPLACE, [float(c) for p in pts for c in p])
    fill_selection(img, layer, op["color"])
    finish_shape(img, layer, op)


def op_frame(img, op, job):
    """Border around the whole canvas, `width` px, inner corners rounded by `round`; a diagonal
    gradient from `color` (top-left) to `color2` (bottom-right) when `color2` is given."""
    wd, r = op.get("width", 20), op.get("round", 0)
    layer = new_layer(img, op.get("name", "Frame"), op.get("opacity", 100))
    Gimp.Selection.all(img)
    fill_selection(img, layer, op["color"])
    if op.get("color2"):
        Gimp.context_set_foreground(color(op["color2"]))
        Gimp.context_set_gradient_fg_transparent()
        layer.edit_gradient_fill(Gimp.GradientType.LINEAR, 0, False, 1, 0, True, W, H, 0, 0)
    img.select_round_rectangle(Gimp.ChannelOps.REPLACE, wd, wd, W - 2 * wd, H - 2 * wd, r, r)
    layer.edit_clear()
    Gimp.Selection.none(img)
    finish_shape(img, layer, op)


def op_person(img, op, job):
    """Your cutout. With a detected face (job["person_face"]) it is framed by the face: face height and
    face top are the same in every photo, whatever its size or crop. Without one, `height` is the
    visible person's height."""
    layer = load_layer(img, job["person"], "Person")
    # fit inside the canvas first: selections are clipped to the canvas
    lw0, lh0 = layer.get_width(), layer.get_height()
    s = min(W / lw0, H / lh0, 1.0)
    layer.scale(max(1, int(lw0 * s)), max(1, int(lh0 * s)), False)
    sx = layer.get_width() / lw0
    layer.set_offsets(0, 0)
    # crop away transparent margins so `height` means the visible person
    img.select_item(Gimp.ChannelOps.REPLACE, layer)
    _, nonempty, x1, y1, x2, y2 = Gimp.Selection.bounds(img)
    Gimp.Selection.none(img)
    if nonempty:
        ox, oy = layer.get_offsets()[1:]
        layer.resize(x2 - x1, y2 - y1, ox - x1, oy - y1)
    else:
        x1 = y1 = 0
    lw, lh = layer.get_width(), layer.get_height()
    top0 = op["top"] if "top" in op else op["bottom"] - op["height"]
    face = job.get("person_face")
    if face:
        fs = sx * lw0 / face["size"][0]  # face box -> cropped layer pixels
        fx, fy, fw, fh = face["box"]
        fx, fy, fw, fh = fx * fs - x1, fy * fs - y1, fw * fs, fh * fs
        k = op.get("face_height", 0.32 * op["height"]) / fh
        w, h = max(1, round(lw * k)), max(1, round(lh * k))
        cx = (fx + fw / 2) * k
        if op.get("flip"):
            cx = w - cx
        x = op["x"] - cx
        top = op.get("face_top", top0 + 0.13 * op["height"]) - fy * k
        if top + h < H:  # tight selfie: the photo ends above the canvas bottom, so slide it down
            top = H - h
    else:
        h = op["height"]
        w = round(lw * h / lh)
        x, top = op["x"] - w / 2, top0
    layer.scale(w, h, False)
    if op.get("flip"):
        layer.transform_flip_simple(Gimp.OrientationType.HORIZONTAL, True, 0)
    layer.set_offsets(int(x), int(top))
    if op.get("fade"):
        apply_fade(layer, op["fade"])
    if op.get("desaturate"):  # black and white
        layer.desaturate(Gimp.DesaturateMode.LUMINANCE)
    finish_shape(img, layer, {"outline": op.get("outline"), "outline_color": op.get("outline_color", "#FFFFFF"),
                              "shadow": op.get("shadow")})


def op_image(img, op, job):
    """Optional extra image (logo, game art) fitted inside `box`; skipped when not provided."""
    path = job.get("images", {}).get(op["key"])
    if not path or not os.path.isfile(path):
        return
    bx, by, bw, bh = op["box"]
    layer = load_layer(img, path, op.get("name", op["key"].capitalize()))
    lw, lh = layer.get_width(), layer.get_height()
    cover = op.get("ellipse") or op.get("cover")
    s = (max if cover else min)(bw / lw, bh / lh)  # cover a circle / tile, else contain
    w, h = max(1, round(lw * s)), max(1, round(lh * s))
    layer.scale(w, h, False)
    x = {"left": bx, "center": bx + (bw - w) / 2, "right": bx + bw - w}[op.get("align", "center")]
    layer.set_offsets(int(x), int(by + (bh - h) / 2))
    if cover:  # clip to the circle / ellipse, or to the (rounded) tile
        if not layer.has_alpha():
            layer.add_alpha()
        if op.get("ellipse"):
            img.select_ellipse(Gimp.ChannelOps.REPLACE, bx, by, bw, bh)
        else:
            r = op.get("round", 0)
            img.select_round_rectangle(Gimp.ChannelOps.REPLACE, bx, by, bw, bh, r, r)
        Gimp.Selection.invert(img)
        layer.edit_clear()
        Gimp.Selection.none(img)
    if op.get("shadow"):
        add_shadow(layer, 4, 6, 10, 0.7)


def op_matrix(img, op, job):
    """'Matrix' code rain: columns of random glyphs fading from dark to a bright head (seeded, repeatable)."""
    rnd = random.Random(op.get("seed", 7))
    group = Gimp.GroupLayer.new(img, "Matrix rain")
    img.insert_layer(group, None, 0)
    group.set_opacity(op.get("opacity", 100))
    font = next(filter(None, (Gimp.Font.get_by_name(n) for n in
                              ("DejaVu Sans Mono Bold", "Monospace Bold", "Montserrat Black"))))
    dark, bright = op.get("dark", "#0A3A12"), op.get("color", "#3CFF6A")
    mix = lambda t: "#" + "".join("%02X" % round(int(dark[i:i + 2], 16) * (1 - t) + int(bright[i:i + 2], 16) * t)
                                  for i in (1, 3, 5))
    glyphs, size, step = op.get("glyphs", "0123456789ABCDEFXZ<>=+*"), op.get("size", 30), op.get("spacing", 38)
    x0, y0, bw, bh = op.get("box", [0, 0, W, H])
    for c in range(bw // step + 1):
        n = rnd.randint(6, 20)
        spans = ['<span foreground="%s">%s</span>' % (mix((i + 1) / n) if i < n - 1 else "#E8FFE8", rnd.choice(glyphs))
                 for i in range(n)]
        t = Gimp.TextLayer.new(img, "x", font, size * rnd.choice([0.8, 1.0, 1.0, 1.25]), PX)
        img.insert_layer(t, group, 0)
        t.set_name("Matrix column %d" % (c + 1))
        t.set_line_spacing(-size * 0.25)
        t.set_markup("\n".join(spans))
        t.set_offsets(x0 + c * step + rnd.randint(-6, 6), y0 + rnd.randint(-t.get_height() // 2, bh - t.get_height() // 3))
        t.set_opacity(rnd.choice([45, 70, 100]))
