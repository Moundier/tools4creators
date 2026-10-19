"""News family (InfoMoney News style): navy panel with a white condensed headline on the left, the news
photo on the right, in a ringed circle or behind a slanted edge. Uses the background photo, not your cutout."""
from .templates_common import BARLOW_BOLD, WHITE

NEWS_NAVY = "#0A1450"
NEWS_GLOW = "#2446B8"


def headline(w):
    """White condensed headline in a left column `w` px wide."""
    return {"op": "text", "text": "{title}", "box": [56, 120, w, 480], "font": BARLOW_BOLD, "color": WHITE,
            "valign": "middle", "max_size": 124, "max_lines": 4, "line_spacing": -0.12, "letter_spacing": 1,
            "shadow": True}


NEWS_TEMPLATES = {
    "news_circle": {
        "max_chars": 44,  # longer titles still fit, but get small
        "description": "Navy panel + headline, photo in a ringed circle on the right (ESCALA 6X1: / APENAS UM / "
                       "SENADOR VOTA / CONTRA PEC)",
        "defaults": {"color": "blue"},
        "ops": [
            {"op": "rect", "name": "Navy", "box": [0, 0, 1280, 720], "color": NEWS_NAVY},
            {"op": "gradient", "name": "Glow", "color": NEWS_GLOW, "start": [380, 380], "end": [-200, -100],
             "opacity": 28},
            {"op": "ellipse", "name": "Ring", "box": [606, -94, 888, 888], "ring": 22, "color": "$color"},
            {"op": "background", "box": [640, -60, 820, 820], "ellipse": True},
            headline(560),
        ],
    },
    "news_diagonal": {
        "max_chars": 36,  # longer titles still fit, but get small
        "description": "Navy panel with a slanted edge + headline, photo on the right (É O FIM DA / ESCALA 6X1)",
        "defaults": {"color": "blue"},
        "ops": [
            {"op": "background", "box": [600, 0, 680, 720]},  # centered in the part the panel leaves visible
            {"op": "poly", "name": "Navy panel", "points": [0, 0, 800, 0, 620, 720, 0, 720], "color": NEWS_NAVY},
            {"op": "poly", "name": "Edge", "points": [800, 0, 816, 0, 636, 720, 620, 720], "color": "$color"},
            headline(540),
        ],
    },
}
