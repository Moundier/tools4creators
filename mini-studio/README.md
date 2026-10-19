# mini-studio: CASA NOVA YouTube toolkit
Record -> subtitles -> Shorts -> thumbnail -> upload, from the Studio web app or the command line.

## Stack
- Python 3 - FastAPI - uvicorn
- Angular 20 (Node 22, plain CSS)
- GIMP 3 (headless python-fu)
- ffmpeg
- PipeWire (+ swh-plugins)
- OBS Studio
- YouTube Data API v3 (google-api-python-client, OAuth)

## AI stack
- **rembg + BiRefNet portrait**: cuts you out of any photo
- **OpenCV YuNet**: finds your face, so every template frames it the same
- **faster-whisper**: offline speech to text (`.srt` + word timings)
- **DeepFilterNet**: mic noise and echo removal (studio preset)
- **RNNoise**: lighter mic denoise (basic preset)

## Setup
```bash
flatpak install flathub org.gimp.GIMP                                  # GIMP 3.x
cp studio_server/fonts/*.ttf ~/.local/share/fonts/ && fc-cache -f
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
sudo apt install swh-plugins ffmpeg
python3 studio.py placeholders                                          # test images + logo
nvm use 22 && cd studio-ui && npm install && npm run build              # web UI
```

## Generate
```bash
python3 studio.py                                   # Studio web app: http://127.0.0.1:8000
python3 studio.py subtitles ep.mkv                  # ep.srt + ep.words.json
python3 studio.py shorts ep.mkv --start 8:10 --end 8:52 --face 1280,720,640,360
python3 studio.py cutout me.jpg -o me.png
python3 studio.py thumb --list
python3 studio.py thumb -t ribbon_alert --title "VAZAMENTO / DE GTA 6" --bg bg.jpg --person me.jpg --art logo.png
python3 studio.py thumb --all --title "VAZAMENTO / DE GTA 6"          # every template into output/
python3 studio.py upload ep.mkv --title "..." --thumb thumb.png --schedule "2026-10-20 18:00"
python3 studio.py mic install                       # mic test | status | mics | uninstall
python3 studio.py obs                               # OBS profiles + scenes (OBS closed)
```
Thumb flags:
- `--title`: `/` = line break
- `--subtitle`: second text
- `--color`: purple - green - blue - aqua - pink - red - teal - orange - yellow
- `--bg`: background photo
- `--person`: photo of you
- `--art` / `--art2`: logos
- `--magazine "TITLE|image.jpg"`: news cover for `collage_magazines` (repeat it; in the Studio, Claude Code finds the images)
- `-o`: output path

## New template
1. Pick or add a family file: `studio_server/services/thumbnails/templates_<family>.py`
2. Add an entry with `max_chars`, `description`, `defaults` and `ops` (drawn bottom to top on 1280×720)
3. For a new family, import it and add it to `FAMILIES` in `templates.py`; it becomes a Studio tab
4. Ops: background - rect - poly - ellipse - gradient - arrow - frame - person - image - text - ribbons - matrix (options listed in the `templates.py` docstring)
5. Render it: `python3 studio.py thumb -t <name> --title "..."` -> `output/<name>.png` + `.xcf`
6. Restart `python3 studio.py` to see it in the Studio

## YouTube login
1. console.cloud.google.com -> new project -> enable **YouTube Data API v3**
2. OAuth consent screen: External, add yourself as a test user
3. Credentials -> OAuth client ID -> Desktop app -> save as `secrets/client_secret.json`
4. First upload (or Settings -> Connect YouTube) opens the login. Unaudited API projects upload as **private** only.
