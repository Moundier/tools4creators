"""Every folder the project uses, in one place."""
import os
from pathlib import Path

PKG = Path(__file__).resolve().parent          # studio_server/
ROOT = PKG.parent                              # the project folder (mini-studio/)

# backend data, shipped inside studio_server/
ASSETS = PKG / "assets"                        # logo, placeholders, cutout + face caches
FONTS = PKG / "fonts"
MIC = PKG / "mic"                              # PipeWire filter-chain template
AI_MODELS = PKG / "ai_models"                  # rembg/, whisper/, yunet/ (downloaded on first use)
THUMBNAILS = PKG / "services" / "thumbnails"
GIMP_SCRIPTS = THUMBNAILS / "gimp"             # run inside GIMP (python-fu), not imported here

# your content and local setup, at the project root
VENV = ROOT / ".venv"
OUTPUT = ROOT / "output"                       # thumbnails made from the command line
WORK = Path(os.environ.get("STUDIO_WORK", ROOT / "work"))   # one folder per recording (web app)
SECRETS = ROOT / "secrets"                     # YouTube OAuth files
REFERENCES = ROOT / "references"
UI_DIST = ROOT / "studio-ui" / "dist" / "studio-ui" / "browser"
