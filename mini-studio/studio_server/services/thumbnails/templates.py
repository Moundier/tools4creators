"""The thumbnail templates, described as data.

Grouped in families, modeled on the user's references (one file each; each family is a tab in the Studio):
  ribbon_*       (templates_ribbon.py) game art background, you on the right with a thick white outline,
                 title in stacked (often tilted) colored ribbons at the bottom-left
  documentary*   (templates_documentary.py) black panel + photo fading into it, huge condensed headline,
                 yellow/blue word (or logo image), red-ruled info line
  davy_*         (templates_davy.py) Davy Jones style: art/logo collage, you on the right with a thin
                 white outline, white title on dark bars with a magenta accent bar (and 5 variations)
  lyric_*        (templates_lyric.py) lyric video: black-and-white photo, color band at the bottom with
                 the artist / song title, small label at the top right (no cutout)
  commentary_*   (templates_commentary.py) Arquivos do Peter style: the video you react to, condensed headline
                 on a white haze, you bottom-left, speech bubble with the second text; commentary_reveal
                 (Ei Nerd style): no text, bordered frame, circled detail + curved arrow, zoom circle
  pov_*          (templates_pov.py) "POV:" meme: video frame + black comic lettering on a white top bar (no cutout)
  large_*        (templates_large.py) Tiozao da Casa style: you on the left, tilted stack of huge outlined words,
                 *highlighted* phrase, yellow questions in a second font
  news_*         (templates_news.py) InfoMoney News style: navy panel + white condensed headline, news photo
                 in a ringed circle or behind a slanted edge (no cutout)
  collage_*      (templates_collage.py) DeByte podcast style: wall of warped magazine covers made from your
                 news list (images found by Claude Code), you in black and white in the middle
  trailer_*      (templates_trailer.py) Emanu Korok style: game footage, platform logo top-left, game logo
                 bottom-left, label box top-right (no cutout)

Canvas is 1280x720. Each template is a list of drawing ops executed bottom-to-top;
every op becomes one (or a few) named layers in the saved .xcf.

Op types (see gimp_render.py):
  background  photo scaled to cover `box` (default: whole canvas); optional blur / darken / fade,
              ellipse (clip the photo to a circle filling `box`), round (rounded panel corners)
  rect        filled rectangle            box=[x, y, w, h]
  poly        filled polygon              points=[x0, y0, x1, y1, ...], round=<corner px>, color2 (left-to-right gradient)
  gradient    color -> transparent        start=[x, y], end=[x, y]
  person      cutout photo                x=<center x>, top or bottom=<y>, height, outline, fade, desaturate
  image       optional extra image        key=art|art2|logo, box (contain fit), ellipse (cover + clip to a circle), cover + round (fill a tile)
  arrow       filled arrow                start, end, width, via=[x, y] (curved shaft)
  frame       border around the canvas    width, round (inner corners), color, color2 (diagonal gradient)
  text        auto-fitting text in box    text may contain {title} {line1} {line2} {subtitle}; '/' = line break
                                          manual_breaks: True = break only at '/' (otherwise one line, same size, may overflow)
  ribbons     stacked title ribbons       styles per line, tilt, small_words, accent bar,
                                          highlight (*words* color), align center, "box": None = text only,
                                          lead_icon "warning" (sign left of line 1, lead_gap px wide; line sizes and breaks unchanged)
  matrix      green 'code rain' columns
  magazines   warped magazine covers      one per news image (job["magazines"]), scattered over a cols x rows grid + extra

Any op can have `if_image: "art"` / `unless_image: "art"` to depend on an optional image,
and `if_value: "subtitle"` to be left out when that text is empty.
"$color", "$on_color" and "$on_white" are replaced with the chosen --color theme.
"""

from .templates_common import THEMES  # noqa: F401 - re-exported for make_thumb / the API
from .templates_commentary import COMMENTARY_TEMPLATES
from .templates_davy import DAVY_TEMPLATES
from .templates_documentary import DOCUMENTARY_TEMPLATES
from .templates_large import LARGE_TEMPLATES
from .templates_lyric import LYRIC_TEMPLATES
from .templates_news import NEWS_TEMPLATES
from .templates_collage import COLLAGE_TEMPLATES
from .templates_pov import POV_TEMPLATES
from .templates_trailer import TRAILER_TEMPLATES
from .templates_ribbon import RIBBON_TEMPLATES

# a new family = a new templates_<family>.py + one line here
FAMILIES = {
    "ribbon": {"label": "Ribbon", "templates": RIBBON_TEMPLATES},
    "documentary": {"label": "Documentary", "templates": DOCUMENTARY_TEMPLATES},
    "davy": {"label": "Davy Jones", "templates": DAVY_TEMPLATES},
    "lyric": {"label": "Lyric Video", "templates": LYRIC_TEMPLATES},
    "commentary": {"label": "Commentary", "templates": COMMENTARY_TEMPLATES},
    "pov": {"label": "POV", "templates": POV_TEMPLATES},
    "large": {"label": "Large lettering", "templates": LARGE_TEMPLATES},
    "news": {"label": "News", "templates": NEWS_TEMPLATES},
    "trailer": {"label": "Trailer", "templates": TRAILER_TEMPLATES},
    "collage": {"label": "Collage", "templates": COLLAGE_TEMPLATES},
}
TEMPLATES = {n: t for f in FAMILIES.values() for n, t in f["templates"].items()}
FAMILY_OF = {n: fid for fid, f in FAMILIES.items() for n in f["templates"]}
