"""Trailer family (Emanu Korok style): the game footage over the whole canvas, platform logo top-left,
game logo bottom-left, condensed white label on a color box top-right. Doesn't use your cutout."""
from .templates_common import OSWALD_BOLD, WHITE

TRAILER_TEMPLATES = {
    "trailer_corner": {
        "max_chars": 44,  # longer titles still fit, but get small
        "description": "Game footage, platform logo (second logo) top-left, game logo bottom-left, label box "
                       "top-right (COMERCIAL JAPONÊS / LEGENDADO EM PT-BR)",
        "defaults": {"color": "red"},
        "ops": [
            {"op": "background"},
            # platform logo on a color square in the top-left corner (only its inner corner is rounded;
            # GIMP also rounds corners at the canvas edge, so two rects square those off)
            {"op": "poly", "name": "Platform logo box", "if_image": "art2", "round": 16, "color": "$color",
             "points": [0, 0, 200, 0, 200, 200, 0, 200], "shadow": True},
            {"op": "rect", "name": "Platform logo box corners", "if_image": "art2", "box": [0, 0, 200, 100],
             "color": "$color"},
            {"op": "rect", "name": "Platform logo box corners", "if_image": "art2", "box": [0, 0, 100, 200],
             "color": "$color"},
            {"op": "image", "key": "art2", "box": [18, 18, 164, 164]},
            {"op": "image", "key": "art", "box": [28, 430, 500, 270], "align": "left", "shadow": True},
            # label: compact lines on a rounded box that hugs them, flush with the right edge
            {"op": "text", "text": "{title}", "box": [760, 34, 490, 140], "font": OSWALD_BOLD, "color": WHITE,
             "align": "right", "justify": "left", "valign": "top", "max_size": 70, "max_lines": 2,
             "line_spacing": -0.32, "backdrop": {"color": "$color", "pad": [22, 12], "round": 14,
             "bleed_right": True, "underline": {"color": WHITE, "height": 4, "gap": 8}, "shadow": True}},
        ],
    },
}
