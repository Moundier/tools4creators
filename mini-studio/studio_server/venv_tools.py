"""Run under the project venv (.venv), where the AI / Google / web packages are installed."""
import os
import sys
from pathlib import Path

from .paths import VENV

VENV_PY = VENV / "bin" / "python"
INSTALL_HINT = "python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"


def in_venv():
    return Path(sys.prefix).resolve() == VENV.resolve()


def ensure_venv():
    """Restart the current command with .venv/bin/python (plain `python3 studio.py ...` keeps working)."""
    if in_venv():
        return
    if not VENV_PY.is_file():
        print(f"warning: .venv not found; AI tools won't work. Install with:\n  {INSTALL_HINT}", file=sys.stderr)
        return
    os.execv(str(VENV_PY), [str(VENV_PY), os.path.abspath(sys.argv[0]), *sys.argv[1:]])
