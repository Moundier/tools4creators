"""`python3 studio.py <command>`: the web app and every tool behind it."""
import argparse
import importlib
import sys
import threading
import webbrowser

COMMANDS = {  # command -> (module with main(argv), one-line help)
    "thumb": ("studio_server.services.thumbnails.make_thumb", "make thumbnails from the GIMP templates"),
    "placeholders": ("studio_server.services.thumbnails.placeholders", "create the test images and the logo"),
    "cutout": ("studio_server.services.cutout", "remove the background from a photo of you"),
    "subtitles": ("studio_server.services.subtitles", "make .srt subtitles with Whisper"),
    "shorts": ("studio_server.services.shorts", "cut a 9:16 Short with captions"),
    "upload": ("studio_server.services.youtube_upload", "upload a video to YouTube"),
    "mic": ("studio_server.services.mic_setup", "install / test the CASA NOVA Mic"),
    "obs": ("studio_server.services.obs_setup", "set up OBS: Gameplay, Live, Talk and News profiles + scenes"),
}

USAGE = "python3 studio.py [web options] | python3 studio.py <command> [options]\n\ncommands:\n" + "\n".join(
    f"  {name:13} {helptext}" for name, (_, helptext) in COMMANDS.items()) + \
    "\n\nwith no command, the web app starts. `python3 studio.py <command> -h` shows a command's options."


def serve(argv):
    p = argparse.ArgumentParser(prog="studio.py", usage=USAGE)
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--no-browser", action="store_true")
    args = p.parse_args(argv)
    import uvicorn

    url = f"http://127.0.0.1:{args.port}"
    if not args.no_browser:
        threading.Timer(1.5, webbrowser.open, [url]).start()
    print(f"CASA NOVA Studio: {url}  (Ctrl+C to stop)")
    uvicorn.run("studio_server.app:app", host="127.0.0.1", port=args.port, log_level="warning")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in COMMANDS:
        module = importlib.import_module(COMMANDS[argv[0]][0])
        return module.main(argv[1:])
    if argv and not argv[0].startswith("-") and argv[0] != "web":
        sys.exit(f"unknown command {argv[0]!r}\n\n{USAGE}")
    return serve(argv[1:] if argv[:1] == ["web"] else argv)
