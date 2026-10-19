"""POV family (TikTok-style "POV:" meme): the video frame over the whole canvas, black comic lettering
on a white bar at the top. Doesn't use your cutout."""
from .templates_common import BLACK, MOUSE_MEMOIRS, WHITE

POV_TEMPLATES = {
    "pov_bar": {
        "max_chars": 34,  # longer titles still fit, but get small
        "description": "Video frame + white bar on top with comic lettering (POV: VOCÊ VISITA RENAN SANTOS)",
        "defaults": {"color": "purple"},
        "ops": [
            {"op": "background"},
            {"op": "rect", "name": "Top bar", "box": [0, 0, 1280, 100], "color": WHITE},
            {"op": "text", "text": "{title}", "box": [24, -8, 1232, 116], "font": MOUSE_MEMOIRS, "color": BLACK,
             "align": "center", "valign": "middle", "max_size": 150, "max_lines": 1, "letter_spacing": 2,
             "outline": 2, "outline_color": BLACK},  # box taller than the bar: the font has tall line spacing
        ],
    },
}
