"""Davy Jones family: game art / logo collage behind, you on the right with a thin white outline,
heavy white title at the bottom-left, usually on dark translucent bars with a magenta accent bar."""
from .templates_common import ANTON, BLACK, MONT_BLACK, WHITE, YELLOW, darker_than

DJ_MAGENTA = "#FF2D8A"

# shared pieces of the davy family
DJ_PERSON = {"op": "person", "x": 1040, "top": 30, "height": 960, "outline": 6, "shadow": True}
BAND_AREA = [20, 460, 1010, 235]
DARK_BOX = {"box": "#1C0A2C", "opacity": 88, "text": WHITE}
COLOR_BOX = {"box": "$color", "text": "$on_color"}
DARK_COLOR_BOX = {"box": darker_than(0), "text": "$on_color"}  # line 1's box, darker
WHITE_BOX = {"box": WHITE, "text": "$on_white"}
ACCENT = {"color": DJ_MAGENTA, "width": 14}


def tint(opacity=55, mode="overlay", color="$color"):
    """Wash the background in the theme color."""
    return {"op": "rect", "name": "Color tint", "box": [0, 0, 1280, 720], "color": color, "mode": mode,
            "opacity": opacity}


def band(styles=(DARK_BOX,), area=BAND_AREA, **extra):
    """Title on dark bars with the magenta accent bar (one bar per line, sized to the text)."""
    return {"op": "ribbons", "text": "{title}", "box": area, "styles": list(styles), "accent": ACCENT,
            "max_size": 110, "pad": [18, 10], "same_size": True, "shadow": True, **extra}


BOTTOM_SHADE = {"op": "gradient", "name": "Bottom shade", "color": BLACK, "start": [0, 720], "end": [0, 430],
                "opacity": 65}

DAVY_TEMPLATES = {
    "davy_band": {
        "max_chars": 46,  # longer titles still fit, but get small
        "description": "Logo collage + dark bars with accent (AS RADIOS DE / GTA 6 REVELADAS)",
        "defaults": {"color": "pink"},
        "ops": [
            {"op": "background"},
            tint(),
            {"op": "image", "key": "art", "box": [30, 20, 780, 430], "shadow": True},
            DJ_PERSON,
            band(),
        ],
    },
    "davy_alert": {
        "max_chars": 30,  # longer titles still fit, but get small
        "description": "Warning sign + white bar and color bar (VAZOU / DE NOVO)",
        "defaults": {"color": "purple"},
        "ops": [
            {"op": "background"},
            tint(35),
            {"op": "image", "key": "art", "box": [40, 10, 740, 420], "shadow": True},
            DJ_PERSON,
            {"op": "ribbons", "text": "{title}", "box": [20, 450, 860, 245], "styles": [WHITE_BOX, COLOR_BOX],
             "x_offsets": [118, 0], "max_size": 108, "auto_lines": 2, "max_lines": 2, "pad": [18, 10], "shadow": True},
            {"op": "poly", "points": [82, 466, 156, 594, 8, 594], "round": 10, "color": BLACK, "shadow": True},
            {"op": "poly", "points": [82, 488, 140, 584, 24, 584], "round": 6, "color": YELLOW},
            {"op": "text", "text": "!", "box": [66, 506, 32, 74], "font": MONT_BLACK, "color": BLACK,
             "align": "center", "valign": "middle", "max_size": 80, "max_lines": 1},
        ],
    },
    "davy_big": {
        "max_chars": 22,  # longer titles still fit, but get small
        "description": "Huge white words, no bars, red-washed art (A PLATINA)",
        "defaults": {"color": "red"},
        "ops": [
            {"op": "background"},
            tint(60),
            {"op": "image", "key": "art", "box": [40, 20, 720, 420], "shadow": True},
            BOTTOM_SHADE,
            DJ_PERSON,
            {"op": "text", "text": "{title}", "box": [26, 440, 900, 255], "font": MONT_BLACK, "color": WHITE,
             "valign": "bottom", "max_size": 210, "max_lines": 3, "line_spacing": -0.15, "outline": 3,
             "outline_color": "#1A0000", "shadow": True},
        ],
    },
    "davy_logos": {
        "max_chars": 46,  # longer titles still fit, but get small
        "description": "Two logos side by side + dark bars (GTA 6 NO PC POR / STREAMING NO XBOX?)",
        "defaults": {"color": "green"},
        "ops": [
            {"op": "background"},
            tint(),
            {"op": "image", "key": "art", "box": [30, 30, 400, 400], "align": "right", "shadow": True},
            {"op": "image", "key": "art2", "box": [450, 50, 360, 360], "align": "left", "shadow": True},
            DJ_PERSON,
            band(),
        ],
    },
    "davy_matrix": {
        "max_chars": 46,  # longer titles still fit, but get small
        "description": "Green code rain over dark art + dark bars (HACKER DE GTA 6 / VOLTOU, E AGORA?)",
        "defaults": {"color": "green"},
        "base": BLACK,
        "ops": [
            {"op": "background", "desaturate": True, "darken": 0.55},
            tint(100, "multiply", "#22FF66"),
            {"op": "matrix", "opacity": 85},
            {"op": "image", "key": "art", "box": [60, 20, 700, 430], "shadow": True},
            DJ_PERSON,
            band(),
        ],
    },
    "davy_split": {
        "max_chars": 42,  # longer titles still fit, but get small
        "description": "Photo panel on a color wall + 3 tilted ribbons (EA FC 27 / ESSE JOGO E / INACREDITAVEL)",
        "defaults": {"color": "red"},
        "ops": [
            {"op": "rect", "name": "Color wall", "box": [0, 0, 1280, 720], "color": "$color"},
            {"op": "gradient", "name": "Vignette", "color": BLACK, "start": [1280, 720], "end": [700, 200],
             "opacity": 55},
            {"op": "background", "box": [0, 0, 700, 420]},
            {"op": "rect", "name": "Panel edge", "box": [700, 0, 12, 420], "color": WHITE},
            {"op": "image", "key": "art", "box": [30, 20, 400, 200], "align": "left", "shadow": True},
            DJ_PERSON,
            {"op": "ribbons", "text": "{title}", "box": [24, 330, 800, 360], "styles": [COLOR_BOX, WHITE_BOX, DARK_COLOR_BOX],
             "auto_lines": 3, "max_size": 110, "pad": [20, 10], "tilt": -4, "shadow": True},
        ],
    },
    "davy_mono": {
        "max_chars": 46,  # longer titles still fit, but get small
        "description": "Black & white art, color logo, color bar over dark bar (GTA 6 NOVIDADES SOBRE / O MUNDO...)",
        "defaults": {"color": "purple"},
        "ops": [
            {"op": "background", "desaturate": True},
            {"op": "image", "key": "art", "box": [30, 20, 420, 330], "shadow": True},
            DJ_PERSON,
            band([COLOR_BOX, DARK_BOX]),
        ],
    },
    "davy_goty": {
        "max_chars": 30,  # longer titles still fit, but get small
        "description": "Outlined white words over art with a color glow (ONIMUSHA E / O MEU GOTY)",
        "defaults": {"color": "pink"},
        "ops": [
            {"op": "background"},
            {"op": "gradient", "name": "Color glow", "color": "$color", "start": [1280, 0], "end": [640, 420],
             "opacity": 75, "mode": "screen"},
            {"op": "image", "key": "art", "box": [40, 20, 700, 400], "shadow": True},
            BOTTOM_SHADE,
            DJ_PERSON,
            {"op": "text", "text": "{title}", "box": [26, 440, 860, 255], "font": MONT_BLACK, "color": WHITE,
             "valign": "bottom", "max_size": 170, "max_lines": 3, "line_spacing": -0.15, "outline": 9,
             "outline_color": BLACK, "shadow": True},
        ],
    },
    "davy_center": {
        "max_chars": 36,  # longer titles still fit, but get small
        "description": "You in the middle, logos on both sides + dark bars (ESSE JOGO / MELHOROU?)",
        "defaults": {"color": "teal"},
        "ops": [
            {"op": "background"},
            tint(40),
            {"op": "image", "key": "art", "box": [20, 40, 430, 340], "align": "left", "shadow": True},
            {"op": "image", "key": "art2", "box": [830, 40, 430, 340], "align": "right", "shadow": True},
            {**DJ_PERSON, "x": 620, "top": 40, "height": 940},
            band(area=[20, 480, 800, 215]),
        ],
    },
    "davy_quote": {
        "max_chars": 24,  # longer titles still fit, but get small
        "description": "Quote in big white letters on the left, you close-up on the right (\u201cISSO / NINGU\u00c9M FALA\u201d)",
        "defaults": {"color": "blue"},
        "ops": [
            {"op": "background", "darken": 0.15},
            {"op": "gradient", "name": "Text shade", "color": BLACK, "start": [0, 360], "end": [760, 360],
             "opacity": 55},
            {**DJ_PERSON, "x": 960, "top": 0, "height": 1150, "outline": 0},
            {"op": "text", "text": "“{title}”", "box": [30, 110, 680, 460], "font": ANTON, "color": WHITE,
             "align": "center", "valign": "middle", "max_size": 190, "max_lines": 3, "line_spacing": -0.05,
             "outline": 6, "outline_color": BLACK, "shadow": True},
        ],
    },
    "davy_quote_wash": {
        "max_chars": 32,  # longer titles still fit, but get small
        "description": "Quote in heavy white letters on a dark color-washed background, you outlined on the right "
                       "(“NÃO VIRE / CRIADOR DE / CONTEÚDO”)",
        "defaults": {"color": "red"},
        "ops": [
            {"op": "background", "desaturate": True, "blur": 6, "darken": 0.35},
            tint(100, "multiply"),
            {**DJ_PERSON, "x": 1010, "top": 0, "height": 1100, "outline": 8},
            {"op": "text", "text": "“{title}”", "box": [36, 60, 760, 600], "font": MONT_BLACK, "color": WHITE,
             "align": "left", "valign": "middle", "max_size": 150, "max_lines": 3, "line_spacing": -0.15,
             "shadow": True},
        ],
    },
}
