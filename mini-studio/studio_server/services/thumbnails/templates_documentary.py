"""Documentary family (INSIDE CAPCOM style): black panel + photo fading into it, huge condensed
headline, yellow/blue word (or logo image), red-ruled info line."""
from .templates_common import ANTON, BLACK, DOC_BLUE, DOC_RED, MONT_BLACK, WHITE, YELLOW


def doc_text(x, w):
    """Documentary headline block for a black panel starting at x with width w."""
    return [
        {"op": "text", "text": "{line1}", "box": [x + 40, 40, w - 80, 275], "font": ANTON,
         "color": WHITE, "align": "center", "valign": "bottom", "max_size": 260, "max_lines": 1,
         "letter_spacing": 4},
        {"op": "text", "text": "{line2}", "unless_image": "art", "box": [x + 20, 310, w - 40, 240],
         "font": MONT_BLACK, "color": YELLOW, "outline": 12, "outline_color": DOC_BLUE,
         "align": "center", "valign": "middle", "max_size": 230, "max_lines": 1, "shadow": True},
        {"op": "image", "key": "art", "if_image": "art", "box": [x + 30, 330, w - 60, 200], "shadow": True},
        {"op": "rect", "box": [x + 30, 552, w - 60, 4], "color": DOC_RED},
        {"op": "text", "text": "{subtitle}", "box": [x + 40, 568, w - 80, 64], "font": ANTON,
         "color": WHITE, "parts": [WHITE, DOC_RED, WHITE], "align": "center", "valign": "middle",
         "max_size": 56, "max_lines": 1},
        {"op": "rect", "box": [x + 30, 644, w - 60, 4], "color": DOC_RED},
    ]


DOCUMENTARY_TEMPLATES = {
    "documentary": {
        "max_chars": 24,  # longer titles still fit, but get small
        "description": "INSIDE CAPCOM look: black panel, photo fading in from the right",
        "defaults": {"subtitle": "2026 | EXCLUSIVO | LEGENDADO"},
        "base": BLACK,
        "ops": [
            {"op": "background", "box": [560, 0, 720, 720], "fade": {"from": [600, 0], "to": [800, 0]}},
            *doc_text(0, 700),
            # {"op": "image", "key": "logo", "box": [1170, 22, 90, 84], "align": "right", "shadow": True},  # channel logo: uncomment to show it
        ],
    },
    "documentary_cutout": {
        "max_chars": 24,  # longer titles still fit, but get small
        "description": "Documentary panel with your cutout on the right over the darkened photo",
        "defaults": {"subtitle": "2026 | EXCLUSIVO | LEGENDADO"},
        "base": BLACK,
        "ops": [
            {"op": "background", "darken": 0.35, "box": [520, 0, 760, 720],
             "fade": {"from": [560, 0], "to": [780, 0]}},
            {"op": "person", "x": 1010, "bottom": 720, "height": 700, "shadow": True},
            *doc_text(0, 700),
            # {"op": "image", "key": "logo", "box": [1170, 22, 90, 84], "align": "right", "shadow": True},  # channel logo: uncomment to show it
        ],
    },
    "documentary_mirror": {
        "max_chars": 24,  # longer titles still fit, but get small
        "description": "Mirrored documentary: photo on the left, text panel on the right",
        "defaults": {"subtitle": "2026 | EXCLUSIVO | LEGENDADO"},
        "base": BLACK,
        "ops": [
            {"op": "background", "box": [0, 0, 720, 720], "fade": {"from": [680, 0], "to": [480, 0]}},
            *doc_text(580, 700),
            # {"op": "image", "key": "logo", "box": [22, 22, 90, 84], "align": "left", "shadow": True},  # channel logo: uncomment to show it
        ],
    },
}
