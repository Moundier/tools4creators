#!/usr/bin/env python3
"""CASA NOVA Studio: the web app and every tool behind it. All the code is in studio_server/.

  python3 studio.py                          # web app on http://127.0.0.1:8000 (opens the browser)
  python3 studio.py thumb -t davy_band --title "VAZOU / DE NOVO" --person me.jpg
  python3 studio.py cutout me.jpg -o me.png
  python3 studio.py subtitles video.mkv
  python3 studio.py shorts video.mkv --start 8:10 --end 8:52 --face 1280,720,640,360
  python3 studio.py upload video.mkv --title "..." --thumb thumb.png --schedule "2026-10-15 18:00"
  python3 studio.py mic install
  python3 studio.py placeholders
  python3 studio.py -h                       # list of commands
"""
from studio_server.venv_tools import ensure_venv

ensure_venv()  # restarts this command under .venv/bin/python when needed

from studio_server.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
