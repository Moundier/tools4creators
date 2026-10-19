"""Make YouTube thumbnails by driving GIMP 3 headlessly.

Examples:
  python3 studio.py thumb --list
  python3 studio.py thumb -t ribbon_duo --title "BRASIL / CONVENCEU?" --bg art.jpg --person me.png
  python3 studio.py thumb -t ribbon_stack --color red --title "SPIDER MAN / UM NOVO DIA / TRAILER INCRIVEL"
  python3 studio.py thumb -t documentary --title "INSIDE / CAPCOM" --subtitle "1996|VERY RARE|ENGLISH SUBTITLES"
  python3 studio.py thumb --all --title "VAZAMENTO / DE GTA 6" --art gta_logo.png

In --title, "/" starts a new ribbon (ribbon_*) or line (documentary*).
"""
import argparse
import re
from pathlib import Path

from ...paths import ASSETS, OUTPUT
from ..cutout import ensure_cutout
from .gimp_runner import run_jobs
from .templates import TEMPLATES, THEMES
from .thumb_job import build_job, too_long

DEFAULT_BG = ASSETS / "placeholder_bg.jpg"
DEFAULT_PERSON = ASSETS / "placeholder_person.png"
DEFAULT_LOGO = ASSETS / "logo.png"


def color_arg(c):
    if c in THEMES or re.fullmatch(r"#?[0-9A-Fa-f]{6}", c):
        return c
    raise argparse.ArgumentTypeError(f"{c!r}: use one of {', '.join(sorted(THEMES))} or #RRGGBB")


def main(argv=None):
    p = argparse.ArgumentParser(prog="studio.py thumb", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-t", "--template", choices=sorted(TEMPLATES), help="template to use")
    p.add_argument("--all", action="store_true", help="render every template")
    p.add_argument("--list", action="store_true", help="list templates and exit")
    p.add_argument("--title", default="ISSO MUDOU / TUDO", help='title; "/" separates ribbons / lines')
    p.add_argument("--subtitle", help='documentary info line, parts separated by "|" (middle part is red)')
    p.add_argument("--color", type=color_arg,
                   help="color theme (%s) or any #RRGGBB; default depends on template" % ", ".join(sorted(THEMES)))
    p.add_argument("--bg", default=str(DEFAULT_BG), help="background photo / game art")
    p.add_argument("--person", default=str(DEFAULT_PERSON),
                   help="photo of you; without transparency the background is removed with rembg")
    p.add_argument("--no-cut", action="store_true", help="use --person as-is, don't remove its background")
    p.add_argument("--art", help="optional logo/title image (game logo, company logo...)")
    p.add_argument("--art2", help="optional second logo (davy_logos and davy_center show it)")
    p.add_argument("--logo", default=str(DEFAULT_LOGO), help="channel logo (only templates with the logo op show it)")
    p.add_argument("--no-logo", action="store_true", help="don't show the channel logo")
    p.add_argument("--magazine", action="append", default=[], metavar="TITLE|IMAGE",
                   help='news image for the collage magazines, e.g. "GTA 6 ADIADO|gta.jpg" (repeat it)')
    p.add_argument("--seed", type=int, help="repeat a random layout (collage magazines); default: new each run")
    p.add_argument("-o", "--out", help="output path without extension (single template) or folder (--all)")
    args = p.parse_args(argv)

    if args.list:
        for name, tpl in TEMPLATES.items():
            print(f"  {name:18} {tpl['description']}")
        return
    if not args.template and not args.all:
        p.error("choose --template NAME or --all (see --list)")
    for f in [args.bg, args.person] + [f for f in (args.art, args.art2) if f]:
        if not Path(f).is_file():
            p.error(f"file not found: {f} (run `python3 studio.py placeholders` for the defaults)")

    args.magazines = []
    for m in args.magazine:
        title, _, path = m.rpartition("|")
        if not Path(path).is_file():
            p.error(f"file not found: {path}")
        args.magazines.append({"title": title.strip(), "path": path})

    if not args.no_cut:
        args.person = str(ensure_cutout(args.person))

    names = list(TEMPLATES) if args.all else [args.template]
    if args.all or not args.out:
        out_dir = Path(args.out or OUTPUT).resolve()
        bases = [out_dir / n for n in names]
    else:
        bases = [Path(args.out).resolve()]
    for b in bases:
        b.parent.mkdir(parents=True, exist_ok=True)

    for n in names:
        if too_long(n, args.title):
            print(f"note: {n} looks best with titles up to {TEMPLATES[n]['max_chars']} characters "
                  f"(this one is {too_long(n, args.title)} over)")
    jobs = [build_job(n, args, b) for n, b in zip(names, bases)]
    for path in run_jobs(jobs):
        print("created", path, "(+ .xcf)")
