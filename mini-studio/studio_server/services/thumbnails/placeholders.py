"""Generate placeholder images so the templates can be tested without real photos.

  studio_server/assets/placeholder_bg.jpg      1920x1080 colorful abstract background
  studio_server/assets/placeholder_person.png  900x1200 head-and-shoulders silhouette, transparent background
  studio_server/assets/placeholder_art.png     transparent "GAME" logo, stands in for --art
  studio_server/assets/placeholder_art2.png    round badge, stands in for --art2
  studio_server/assets/logo.png                CASA NOVA logo cut from references/ (only if missing)

Replace them (or pass --bg / --person / --art / --art2 / --logo to `studio.py thumb`) with your own images.
"""
import argparse

from ...paths import ASSETS
from .brand_logo import LOGO_SRC, make_logo
from .placeholder_images import make_art, make_art2, make_background, make_person


def main(argv=None):
    argparse.ArgumentParser(prog="studio.py placeholders", description=__doc__,
                            formatter_class=argparse.RawDescriptionHelpFormatter).parse_args(argv)
    ASSETS.mkdir(exist_ok=True)
    make_background(ASSETS / "placeholder_bg.jpg")
    make_person(ASSETS / "placeholder_person.png")
    make_art(ASSETS / "placeholder_art.png")
    make_art2(ASSETS / "placeholder_art2.png")
    print("wrote placeholder_bg.jpg, placeholder_person.png, placeholder_art.png, placeholder_art2.png")
    if LOGO_SRC.is_file() and not (ASSETS / "logo.png").exists():
        make_logo(LOGO_SRC, ASSETS / "logo.png")
        print("wrote logo.png from", LOGO_SRC.name)
