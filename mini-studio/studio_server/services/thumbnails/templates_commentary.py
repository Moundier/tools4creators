"""Commentary family (Arquivos do Peter style): the video you react to as the background, condensed
headline on a white haze at the top-left, you at the bottom-left, speech bubble quoting the other person."""
from .templates_common import BLACK, MONT_BLACK_ITALIC, OSWALD_BOLD, WHITE

REVEAL_RED = "#E8231B"
REVEAL_YELLOW, REVEAL_ORANGE_RED = "#FBCF0E", "#F33413"  # the border gradient

COMMENTARY_TEMPLATES = {
    "commentary_bubble": {
        "max_chars": 36,  # longer titles still fit, but get small
        "description": "Headline on a white haze, you bottom-left, speech bubble from the second text "
                       "(AGORA QUER / QUER TRÉGUA / COM A DIREITA?)",
        "defaults": {"color": "purple"},
        "ops": [
            {"op": "background"},
            {"op": "gradient", "name": "White haze", "color": WHITE, "start": [0, 0], "end": [820, 460],
             "opacity": 92},
            {"op": "person", "x": 290, "top": 330, "height": 640, "outline": 6, "shadow": True},
            {"op": "rect", "name": "Frame left", "box": [0, 0, 14, 720], "color": "$color"},
            {"op": "rect", "name": "Frame bottom", "box": [0, 702, 1280, 18], "color": "$color"},
            {"op": "text", "text": "{title}", "box": [44, 24, 760, 330], "font": OSWALD_BOLD, "color": "$on_white",
             "valign": "top", "max_size": 140, "max_lines": 3, "line_spacing": -0.18, "outline": 4,
             "outline_color": WHITE, "manual_breaks": True},  # lines only where you put '/'
            # speech bubble (one shape: box + tail pointing up at the person in the video), only with a second text
            {"op": "poly", "name": "Speech bubble", "if_value": "subtitle", "round": 26, "color": WHITE,
             "points": [560, 490, 880, 490, 965, 360, 990, 490, 1120, 490, 1120, 640, 560, 640],
             "outline": 3, "outline_color": BLACK, "shadow": True},
            {"op": "text", "text": "{subtitle}", "if_value": "subtitle", "box": [578, 500, 524, 130],
             "font": MONT_BLACK_ITALIC, "color": BLACK, "align": "center", "valign": "middle", "max_size": 66,
             "max_lines": 2, "line_spacing": -0.1, "manual_breaks": True},
        ],
    },
    "commentary_reveal": {
        "max_chars": 40,  # the title isn't drawn: this one is all pictures
        "description": "No text: video frame in a red-orange border, channel logo tab top-left, detail circled "
                       "with a curved arrow, second logo zoomed in a circle, you big on the right (Ei Nerd style)",
        "defaults": {"color": "red"},
        "ops": [
            {"op": "background"},
            # the detail you point at: red ring + curved arrow (fixed spot, over the left side of the video)
            {"op": "ellipse", "name": "Detail ring", "box": [92, 372, 184, 150], "ring": 7, "color": REVEAL_RED,
             "shadow": True},
            {"op": "arrow", "name": "Detail arrow", "start": [215, 248], "via": [118, 238], "end": [118, 368],
             "width": 15, "color": REVEAL_RED, "shadow": True},
            # second logo / close-up in a ringed circle at the top, hanging off the top edge
            {"op": "ellipse", "name": "Zoom ring", "if_image": "art2", "box": [498, -16, 356, 356],
             "color": "#FFB547", "shadow": True},
            {"op": "image", "key": "art2", "box": [505, -9, 342, 342], "ellipse": True},
            {"op": "person", "x": 1050, "top": -40, "height": 1320, "shadow": True},
            {"op": "frame", "width": 20, "round": 30, "color": REVEAL_YELLOW, "color2": REVEAL_ORANGE_RED},  # fixed colors, ignores the theme
            # channel logo on a yellow trapezoid tab glued to the top-left corner (slanted right side);
            # its gradient matches the border where they meet (#FABE0F = the border at x=300)
            {"op": "poly", "name": "Logo tab", "if_image": "logo", "color": REVEAL_YELLOW, "color2": "#FABE0F",
             "points": [0, 0, 300, 0, 264, 82, 0, 82]},
            {"op": "image", "key": "logo", "box": [16, 8, 236, 66]},
        ],
    },
}
