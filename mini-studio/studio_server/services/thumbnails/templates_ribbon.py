"""Ribbon family (Gameplayrj style): game art background, you on the right with a thick
white outline, title in stacked (often tilted) colored ribbons at the bottom-left."""
from .templates_common import WHITE, darker_than

# shared pieces of the ribbon family
PERSON_RIGHT = {"op": "person", "x": 975, "top": 60, "height": 1000, "outline": 12, "shadow": True}
ART_TOP_LEFT = {"op": "image", "key": "art", "box": [24, 24, 520, 280], "align": "left", "shadow": True}  # game logo, top-left corner
RIBBON_AREA = [26, 330, 700, 330]
LOGO_TOP_LEFT = {"op": "image", "key": "logo", "box": [22, 22, 112, 104], "align": "left", "shadow": True}

COLOR_BOX = {"box": "$color", "text": "$on_color"}
WHITE_BOX = {"box": WHITE, "text": "$on_white"}
DARK_COLOR_BOX = {"box": darker_than(0), "text": "$on_color"}  # line 1's box, darker


RIBBON_TEMPLATES = {
    "ribbon_duo": {
        "max_chars": 40,  # longer titles still fit, but get small
        "description": "Color ribbon + white ribbon, tilted (BRASIL / CONVENCEU?)",
        "defaults": {"color": "purple"},
        "ops": [
            {"op": "background"},
            ART_TOP_LEFT,
            PERSON_RIGHT,
            {"op": "ribbons", "text": "{title}", "box": RIBBON_AREA, "styles": [COLOR_BOX, WHITE_BOX, DARK_COLOR_BOX],
             "max_size": 140, "tilt": -4, "shadow": True},
            # LOGO_TOP_LEFT,  # channel logo: uncomment to show it
        ],
    },
    "ribbon_stack": {
        "max_chars": 40,  # longer titles still fit, but get small
        "description": "Up to 3 same-color ribbons, tilted (SHREK 5 / PRIMEIRO / TRAILER)",
        "defaults": {"color": "green"},
        "ops": [
            {"op": "background"},
            ART_TOP_LEFT,
            PERSON_RIGHT,
            {"op": "ribbons", "text": "{title}", "box": RIBBON_AREA, "styles": [COLOR_BOX, {"box": darker_than(0, 0.86), "text": "$on_color"}, DARK_COLOR_BOX],
             "auto_lines": 3, "max_size": 115, "x_offsets": [0, 14, 28], "tilt": -4, "shadow": True},
            # LOGO_TOP_LEFT,  # channel logo: uncomment to show it
        ],
    },
    "ribbon_alert": {
        "max_chars": 34,  # longer titles still fit, but get small
        "description": "Warning sign + flat full-width bands (VAZAMENTO / DE GTA 6)",
        "defaults": {"color": "purple"},
        "ops": [
            {"op": "background"},
            {**ART_TOP_LEFT, "box": [24, 24, 460, 230]},
            PERSON_RIGHT,
            {"op": "ribbons", "text": "{title}", "box": [30, 470, 720, 250], "styles": [WHITE_BOX, COLOR_BOX, {"box": darker_than(1), "text": "$on_color"}],
             "max_size": 120, "pad": [20, 16], "bleed_left": True,
             "lead_icon": "warning", "lead_gap": 150},  # warning sign left of line 1
            # LOGO_TOP_LEFT,  # channel logo: uncomment to show it
        ],
    },
    "ribbon_vs": {
        "max_chars": 36,  # longer titles still fit, but get small
        "description": "Comparison: 'A vs' ribbon + white ribbon (MESSI vs / CRISTIANO RONALDO)",
        "defaults": {"color": "blue"},
        "ops": [
            {"op": "background"},
            ART_TOP_LEFT,
            PERSON_RIGHT,
            {"op": "ribbons", "text": "{title}", "box": RIBBON_AREA, "styles": [COLOR_BOX, WHITE_BOX, DARK_COLOR_BOX],
             "small_words": ["VS", "X"], "max_size": 120, "tilt": -4, "shadow": True},
            # LOGO_TOP_LEFT,  # channel logo: uncomment to show it
        ],
    },
    "ribbon_question": {
        "max_chars": 32,  # longer titles still fit, but get small
        "description": "Yellow text on dark translucent ribbons (SEREI / CAMPEAO?)",
        "defaults": {"color": "yellow"},
        "ops": [
            {"op": "background"},
            ART_TOP_LEFT,
            PERSON_RIGHT,
            {"op": "ribbons", "text": "{title}", "box": RIBBON_AREA,
             "styles": [{"box": "#101010", "opacity": 78, "text": "$color", "outline": 4}],
             "max_size": 130, "tilt": -4, "shadow": True},
            # LOGO_TOP_LEFT,  # channel logo: uncomment to show it
        ],
    },
}
