"""Where things live."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # mini-news/
VENV = ROOT / ".venv"
SECRETS = ROOT / "secrets"                       # x.json, facebook.json (never shared)
WORK = ROOT / "work"
DRAFTS = WORK / "drafts"                         # <id>.json, one per post
CARDS = WORK / "cards"                           # <id>.png, the image attached to the post
PHOTOS = WORK / "photos"                         # <id>.jpg: the article photo, or one you uploaded
STYLES = ROOT / "styles"                         # <id>.json image styles + assets/ (backgrounds, logos, fonts)
UI = Path(__file__).resolve().parent / "ui"
FONT = Path.home() / ".local/share/fonts/Montserrat-Bold.ttf"   # static Bold (the variable one renders Thin)
