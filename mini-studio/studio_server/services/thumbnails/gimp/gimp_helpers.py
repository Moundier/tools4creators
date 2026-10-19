"""Low-level GIMP helpers shared by all ops (runs inside GIMP)."""
import traceback

import gi
gi.require_version("Gimp", "3.0")
gi.require_version("Gegl", "0.4")
from gi.repository import Gegl, Gimp, Gio

W, H = 1280, 720
PX = Gimp.Unit.pixel()


def color(hex_):
    return Gegl.Color.new(hex_)


# blend modes usable as "mode" in rect / gradient ops
MODES = {"normal": Gimp.LayerMode.NORMAL, "multiply": Gimp.LayerMode.MULTIPLY, "screen": Gimp.LayerMode.SCREEN,
         "overlay": Gimp.LayerMode.OVERLAY, "soft_light": Gimp.LayerMode.SOFTLIGHT,
         "color": Gimp.LayerMode.HSL_COLOR}


def new_layer(img, name, opacity=100, position=0, parent=None, mode="normal"):
    layer = Gimp.Layer.new(img, name, W, H, Gimp.ImageType.RGBA_IMAGE, opacity, MODES[mode])
    img.insert_layer(layer, parent, position)
    return layer


def fill_selection(img, layer, hex_):
    Gimp.context_set_foreground(color(hex_))
    layer.edit_fill(Gimp.FillType.FOREGROUND)
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


def add_outline(img, layer, width, hex_):
    """Solid outline: alpha of `layer` grown by `width`, filled on a new layer just below it."""
    img.select_item(Gimp.ChannelOps.REPLACE, layer)
    Gimp.Selection.grow(img, int(width))
    below = new_layer(img, layer.get_name() + " outline", position=img.get_item_position(layer) + 1)
    fill_selection(img, below, hex_)
    return below


def finish_shape(img, layer, op):
    """Shared outline/shadow handling for drawn shapes."""
    target = layer
    if op.get("outline"):
        target = add_outline(img, layer, op["outline"], op.get("outline_color", "#000000"))
    if op.get("shadow"):
        add_shadow(target)


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
    return layer
