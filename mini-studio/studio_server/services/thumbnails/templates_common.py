"""Colors, fonts and --color themes shared by all templates."""

WHITE = "#FFFFFF"
BLACK = "#000000"
YELLOW = "#FFCC00"
DOC_RED = "#E3121B"
DOC_BLUE = "#0B2A8A"

ANTON = "Anton Regular"
MONT_BLACK = "Montserrat Black"
MONT_XBOLD = "Montserrat ExtraBold"
MONT_BLACK_ITALIC = "Montserrat Black Italic"
OSWALD_BOLD = "Oswald Bold"
MOUSE_MEMOIRS = "Mouse Memoirs Regular"  # comic lettering (POV memes)
BARLOW_BLACK_ITALIC = "Barlow Condensed Black Italic"
BARLOW_BOLD = "Barlow Condensed Bold"

def darker(hex_, k=0.72):
    """Same hue, noticeably darker: each RGB channel scaled by k."""
    r, g, b = (int(hex_[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02X%02X%02X" % (round(r * k), round(g * k), round(b * k))


def darker_than(line, k=0.72):
    """Ribbon style value: a darker version of the same value on another line (0 = first line),
    e.g. {"box": darker_than(0)}. Resolved in thumb_job once the theme colors are filled in."""
    return {"darker_than": line, "k": k}


# --color themes: ribbon box color, text on that box, text on a white box
THEMES = {
    "purple": {"color": "#6B2A8F", "on_color": WHITE, "on_white": "#5A2178"},   # CASA NOVA purple
    "green":  {"color": "#2E9B45", "on_color": WHITE, "on_white": "#237A36"},   # CASA NOVA green
    "blue":   {"color": "#1E4FD8", "on_color": WHITE, "on_white": "#1A43B8"},
    "aqua":   {"color": "#1AA3E8", "on_color": WHITE, "on_white": "#1386C2"},   # lyric video blue
    "pink":   {"color": "#E0177D", "on_color": WHITE, "on_white": "#C2126B"},
    "red":    {"color": "#D62630", "on_color": WHITE, "on_white": "#C01F28"},
    "teal":   {"color": "#0F8A8F", "on_color": WHITE, "on_white": "#0B7277"},
    "orange": {"color": "#F07800", "on_color": WHITE, "on_white": "#D96A00"},
    "yellow": {"color": "#FFCC00", "on_color": "#111111", "on_white": "#111111"},
}


def theme_for(c):
    """A theme name, or any "#RRGGBB" from the color picker: text on it is white, or near-black on light colors."""
    if c in THEMES:
        return THEMES[c]
    c = "#" + c.lstrip("#").upper()
    r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
    if 0.299 * r + 0.587 * g + 0.114 * b > 165:  # light color: dark text, and dark text on white too
        return {"color": c, "on_color": "#111111", "on_white": "#111111"}
    return {"color": c, "on_color": WHITE, "on_white": darker(c, 0.85)}
