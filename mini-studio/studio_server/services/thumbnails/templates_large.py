"""Large lettering family (Tiozao da Casa style): you close-up on the left, a tilted stack of huge
outlined words on the right, each line as wide as the column, one phrase highlighted in color, and
yellow questions under it in a second, condensed font (from the second text)."""
from .templates_common import BARLOW_BLACK_ITALIC, BLACK, MONT_BLACK_ITALIC, WHITE, YELLOW

# text-only "ribbons": no box, thick black outline
OUTLINED_WHITE = {"box": None, "text": WHITE, "outline": 9, "outline_color": BLACK}
OUTLINED_YELLOW = {"box": None, "text": YELLOW, "outline": 8, "outline_color": BLACK}

LARGE_TEMPLATES = {
    "large_stack": {
        "max_chars": 40,  # longer titles still fit, but get small
        "description": "Tilted stack of huge outlined words, *highlighted* phrase, yellow questions from the "
                       "second text (COMPREI UM / LOTE COM / *+100 JOGOS* / DE PS3!)",
        "defaults": {"color": "red"},
        "ops": [
            {"op": "background", "darken": 0.1},
            {"op": "person", "x": 300, "top": 20, "height": 1080, "outline": 0, "shadow": True},
            {"op": "ribbons", "text": "{title}", "box": [580, 20, 680, 450], "styles": [OUTLINED_WHITE],
             "font": MONT_BLACK_ITALIC, "highlight": "$color", "align": "center", "auto_lines": 4,
             "max_lines": 4, "max_size": 128, "pad": [12, 2], "tilt": -5, "shadow": True},
            {"op": "ribbons", "text": "{subtitle}", "if_value": "subtitle", "box": [600, 470, 640, 220],
             "styles": [OUTLINED_YELLOW], "font": BARLOW_BLACK_ITALIC, "align": "center", "max_lines": 2,
             "max_size": 110, "pad": [12, 0], "tilt": -5, "shadow": True},
        ],
    },
}
