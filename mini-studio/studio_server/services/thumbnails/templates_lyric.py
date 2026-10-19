"""Lyric video family (Dry Cell lyric video style): black-and-white photo over the whole canvas,
translucent color band at the bottom with the artist / song title, small label at the top right."""
from .templates_common import BLACK, MONT_XBOLD, WHITE

LYRIC_TEMPLATES = {
    "lyric_band": {
        "max_chars": 40,  # longer titles still fit, but get small
        "description": "Black-and-white photo, color band at the bottom with the title (DRY CELL / I REGRET (PEEWEE))",
        "defaults": {"color": "aqua", "subtitle": "LYRIC VIDEO"},
        "ops": [
            {"op": "background", "desaturate": True, "darken": 0.1},
            {"op": "rect", "name": "Title band", "box": [0, 530, 1280, 190], "color": "$color", "opacity": 62},
            {"op": "text", "text": "{title}", "box": [40, 540, 1200, 170], "font": MONT_XBOLD, "color": WHITE,
             "align": "center", "valign": "middle", "max_size": 84, "max_lines": 2, "line_spacing": -0.2,
             "shadow": True},
            {"op": "text", "text": "{subtitle}", "box": [880, 22, 375, 62], "font": MONT_XBOLD, "color": WHITE,
             "align": "right", "valign": "top", "max_size": 54, "max_lines": 1, "outline": 2,
             "outline_color": BLACK, "shadow": True},
        ],
    },
}
