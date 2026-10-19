"""Cut the CASA NOVA channel logo out of its reference screenshot."""

from PIL import Image, ImageDraw

from ...paths import REFERENCES

# The logo is turned off in every template: its ops are commented out in templates_ribbon.py and
# templates_documentary.py (search for "channel logo"). Uncomment them to show it again.

LOGO_SRC = REFERENCES / "img" / "Screenshot from 2026-09-06 23-36-26.png"


def make_logo(src, path):
    """Crop the channel logo badge (green frame on black) and round its corners."""
    im = Image.open(src).convert("RGB")
    bright = im.convert("L").point(lambda v: 255 if v > 60 else 0)
    im = im.crop(bright.getbbox()).convert("RGBA")
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=im.width // 16, fill=255)
    im.putalpha(mask)
    im.save(path)
