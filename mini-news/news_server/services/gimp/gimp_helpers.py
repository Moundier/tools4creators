"""Low-level GIMP helpers shared by all ops (runs inside GIMP). Adapted from mini-studio's thumbnails:
the canvas size comes from each image (9:16 or 4:5), not a fixed 1280x720."""
import traceback

import gi
gi.require_version("Gimp", "3.0")
gi.require_version("Gegl", "0.4")
from gi.repository import Gegl, Gimp, Gio

PX = Gimp.Unit.pixel()

# blend modes usable as "mode" in rect / gradient ops
MODES = {"normal": Gimp.LayerMode.NORMAL, "multiply": Gimp.LayerMode.MULTIPLY, "screen": Gimp.LayerMode.SCREEN,
         "overlay": Gimp.LayerMode.OVERLAY, "soft_light": Gimp.LayerMode.SOFTLIGHT}


def color(hex_):
    return Gegl.Color.new(hex_)


def new_layer(img, name, opacity=100, position=0, parent=None, mode="normal"):
    layer = Gimp.Layer.new(img, name, img.get_width(), img.get_height(), Gimp.ImageType.RGBA_IMAGE, opacity,
                           MODES[mode])
    img.insert_layer(layer, parent, position)
    layer.set_opacity(float(opacity))
    perceptual(layer)
    return layer


def perceptual(layer):
    """Blend like browsers / PIL do. GIMP 3 blends in linear light by default, which makes a 4% white
    layer look like ~20% on a dark background."""
    try:
        layer.set_composite_space(Gimp.LayerColorSpace.RGB_PERCEPTUAL)
        layer.set_blend_space(Gimp.LayerColorSpace.RGB_PERCEPTUAL)
    except Exception:
        traceback.print_exc()


def fill_selection(img, layer, hex_):
    Gimp.context_set_foreground(color(hex_))
    layer.edit_fill(Gimp.FillType.FOREGROUND)
    Gimp.Selection.none(img)


def gradient_fill(img, layer, stops, y0, y1):
    """Fill the current selection with a vertical gradient through 2 or 3 colors (top -> bottom)."""
    stops = list(stops) * 2 if len(stops) == 1 else list(stops)
    sel = img.get_selection().save(img)              # keep the shape: each band intersects it
    n = len(stops) - 1
    for i in range(n):
        a, b = y0 + (y1 - y0) * i / n, y0 + (y1 - y0) * (i + 1) / n
        top = -10000 if i == 0 else int(a)                # the first / last band reach past the shape's edges
        bottom = 10000 if i == n - 1 else int(b) + 1
        img.select_item(Gimp.ChannelOps.REPLACE, sel)
        img.select_rectangle(Gimp.ChannelOps.INTERSECT, 0, top, img.get_width(), bottom - top)
        Gimp.context_set_foreground(color(stops[i]))
        Gimp.context_set_background(color(stops[i + 1]))
        Gimp.context_set_gradient_fg_bg_rgb()
        layer.edit_gradient_fill(Gimp.GradientType.LINEAR, 0, False, 1, 0, True, 0, a, 0, b)
    img.remove_channel(sel)
    Gimp.Selection.none(img)


def add_shadow(layer, x=6, y=8, radius=14, opacity=0.8):
    """Non-destructive drop shadow (stays editable in the .xcf)."""
    try:
        f = Gimp.DrawableFilter.new(layer, "gegl:dropshadow", "Drop Shadow")
        cfg = f.get_config()
        cfg.set_property("x", float(x))
        cfg.set_property("y", float(y))
        cfg.set_property("radius", float(radius))
        cfg.set_property("opacity", float(opacity))
        cfg.set_property("color", color("black"))
        f.update()
        layer.append_filter(f)
    except Exception:
        traceback.print_exc()


def apply_fade(layer, fade):
    """Layer mask with a linear gradient: transparent at fade['from'], opaque at fade['to'] (canvas coords)."""
    mask = layer.create_mask(Gimp.AddMaskType.WHITE)
    layer.add_mask(mask)
    Gimp.context_set_foreground(color("black"))
    Gimp.context_set_background(color("white"))
    Gimp.context_set_gradient_fg_bg_rgb()
    ox, oy = layer.get_offsets()[1:]
    (x1, y1), (x2, y2) = fade["from"], fade["to"]
    mask.edit_gradient_fill(Gimp.GradientType.LINEAR, 0, False, 1, 0, True, x1 - ox, y1 - oy, x2 - ox, y2 - oy)


def load_layer(img, path, name):
    layer = Gimp.file_load_layer(Gimp.RunMode.NONINTERACTIVE, img, Gio.File.new_for_path(path))
    layer.set_name(name)
    img.insert_layer(layer, None, 0)
    if not layer.has_alpha():
        layer.add_alpha()
    perceptual(layer)
    return layer
