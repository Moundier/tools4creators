"""Turn part of a 16:9 video into a 9:16 YouTube Short with animated captions.

  python3 studio.py shorts video.mkv --start 12:30 --end 13:15 --face 0,0,640,360 --title "VAZOU DE NOVO"
  python3 studio.py shorts video.mkv --start 75 --end 120 --layout center

--face x,y,w,h   where your facecam is in the video (pixels). The Short gets your face on top
                 and the gameplay below. Without it (--layout center) the frame is center-cropped.
--game x,y,w,h   which part of the video is the gameplay (default: the whole frame, center-cropped)
Captions: 2-3 words at a time, the spoken word in yellow. Words come from video.words.json
(made by subtitles.py); if it's missing, Whisper transcribes just this part.
Audio is normalized to -14 LUFS (YouTube loudness). Output: 1080x1920 H.264 MP4.
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from ..paths import FONTS

W, H = 1080, 1920
FACE_H = 768                       # facecam band height in the Short (40%)
FONT = "Montserrat Black"
WHITE, YELLOW, DARK = "&H00FFFFFF", "&H0000CCFF", "&H002C0A1C"  # ASS colors are &HAABBGGRR


def seconds(t):
    """'12:30' / '1:02:03' / '75.5' -> seconds."""
    total = 0.0
    for part in str(t).split(":"):
        total = total * 60 + float(part)
    return total


def video_size(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height", "-of", "csv=p=0", str(path)],
                         check=True, capture_output=True, text=True).stdout
    w, h = out.strip().split(",")[:2]
    return int(w), int(h)


def crop_to_aspect(x, y, w, h, aspect):
    """Largest box of the given w/h aspect centered inside (x, y, w, h)."""
    if w / h > aspect:
        nw = round(h * aspect)
        return x + (w - nw) // 2, y, nw, h
    nh = round(w / aspect)
    return x, y + (h - nh) // 2, w, nh


def video_filter(src_w, src_h, face, game, ass_path):
    even = lambda v: v - v % 2
    if face:
        fx, fy, fw, fh = crop_to_aspect(*face, W / FACE_H)
        gx, gy, gw, gh = crop_to_aspect(*(game or (0, 0, src_w, src_h)), W / (H - FACE_H))
        graph = (f"[0:v]split[a][b];"
                 f"[a]crop={even(fw)}:{even(fh)}:{fx}:{fy},scale={W}:{FACE_H}[face];"
                 f"[b]crop={even(gw)}:{even(gh)}:{gx}:{gy},scale={W}:{H - FACE_H}[game];"
                 f"[face][game]vstack,setsar=1")
    else:
        cw = even(min(src_w, round(src_h * W / H)))
        graph = f"[0:v]crop={cw}:{src_h}:{(src_w - cw) // 2}:0,scale={W}:{H},setsar=1"
    return graph + f",ass=filename={ass_path}:fontsdir={FONTS}[v]"


def ass_time(t):
    cs = max(0, round(t * 100))
    return "%d:%02d:%02d.%02d" % (cs // 360000, cs // 6000 % 60, cs // 100 % 60, cs % 100)


def caption_groups(words, max_words=3, max_chars=16, max_gap=0.5):
    groups, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or w["start"] - cur[-1]["end"] > max_gap
                    or len(" ".join(x["word"] for x in cur + [w])) > max_chars
                    or cur[-1]["word"][-1] in ".?!,"):
            groups.append(cur)
            cur = []
        cur.append(w)
    return groups + ([cur] if cur else [])


def make_ass(words, start, duration, caption_y, title):
    esc = lambda s: s.replace("\\", "").replace("{", "(").replace("}", ")")
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 0", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
        "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Cap,{FONT},118,{WHITE},{WHITE},&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,11,5,5,50,50,0,1",
        f"Style: Title,{FONT},72,{WHITE},{WHITE},{DARK},{DARK},-1,0,0,0,100,100,0,0,3,20,0,8,70,70,50,1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    if title:
        lines.append(f"Dialogue: 1,{ass_time(0)},{ass_time(min(3.0, duration))},Title,,0,0,0,,"
                     f"{{\\fad(150,250)}}{esc(title.upper())}")
    for group in caption_groups(words):
        g_end = group[-1]["end"]
        for i, w in enumerate(group):
            t0 = w["start"] - start
            t1 = (group[i + 1]["start"] if i + 1 < len(group) else g_end) - start
            text = " ".join((f"{{\\c{YELLOW}}}{esc(x['word'].upper())}{{\\c{WHITE}}}" if j == i
                             else esc(x["word"].upper())) for j, x in enumerate(group))
            pop = "\\fscx112\\fscy112\\t(0,90,\\fscx100\\fscy100)" if i == 0 else ""
            lines.append(f"Dialogue: 0,{ass_time(t0)},{ass_time(max(t1, t0 + 0.05))},Cap,,0,0,0,,"
                         f"{{\\pos({W // 2},{caption_y}){pop}}}{text}")
    return "\n".join(lines) + "\n"


def load_words(video, words_path, start, end, model):
    path = Path(words_path) if words_path else Path(video).with_suffix(".words.json")
    if path.is_file():
        words = json.loads(path.read_text(encoding="utf-8"))
    else:
        from .subtitles import transcribe
        print(f"no {path.name}; transcribing {start:.0f}s-{end:.0f}s with whisper {model}...")
        words = transcribe(video, model=model, start=start, end=end)
    return [w for w in words if w["start"] >= start - 0.05 and w["end"] <= end + 0.3]


def make_short(video, start, end, out, face=None, game=None, title=None, words=None, report=None):
    """Render a 1080x1920 Short of video[start:end] to `out`.

    face / game: [x, y, w, h] boxes in the video (face=None -> center crop).
    words: caption words (see load_words); None or [] -> no captions.
    report(progress 0-1, message): optional progress callback.
    """
    words = words or []
    duration = end - start
    caption_y = FACE_H if face else round(H * 0.68)
    src_w, src_h = video_size(video)
    with tempfile.TemporaryDirectory() as tmp:
        ass = Path(tmp) / "captions.ass"
        ass.write_text(make_ass(words, start, duration, caption_y, title), encoding="utf-8")
        cmd = ["ffmpeg", "-v", "error", "-nostats", "-progress", "pipe:1", "-y",
               "-ss", str(start), "-to", str(end), "-i", str(video),
               "-filter_complex", video_filter(src_w, src_h, face, game, ass), "-map", "[v]", "-map", "0:a?",
               "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
               "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30",
               "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for line in proc.stdout:  # ffmpeg -progress: key=value lines
            if line.startswith("out_time_us=") and report:
                try:
                    report(min(1.0, int(line.split("=")[1]) / 1e6 / duration), "rendering")
                except ValueError:
                    pass
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg failed: " + proc.stderr.read()[-800:])
    return Path(out)


def main(argv=None):
    p = argparse.ArgumentParser(prog="studio.py shorts", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video")
    p.add_argument("--start", required=True, help="start time (seconds or mm:ss)")
    p.add_argument("--end", required=True, help="end time (seconds or mm:ss)")
    p.add_argument("--face", help="facecam box in the video: x,y,w,h")
    p.add_argument("--game", help="gameplay box in the video: x,y,w,h (default: whole frame)")
    p.add_argument("--layout", choices=["face", "center"], help="center = plain center crop (default without --face)")
    p.add_argument("--title", help="banner shown at the top for the first 3 seconds")
    p.add_argument("--words", help="words JSON (default: <video>.words.json)")
    p.add_argument("--model", default="small", help="whisper model if transcription is needed")
    p.add_argument("--no-captions", action="store_true")
    p.add_argument("-o", "--out", help="output .mp4 (default: <video>_short_<start>.mp4)")
    args = p.parse_args(argv)

    start, end = seconds(args.start), seconds(args.end)
    if end <= start:
        p.error("--end must be after --start")
    duration = end - start
    if duration > 60:
        print(f"warning: {duration:.0f}s is longer than 60 s; YouTube may not treat it as a Short", file=sys.stderr)

    def box(value, name):
        b = [int(v) for v in value.split(",")] if value else None
        if b and len(b) != 4:
            p.error(f"--{name} needs x,y,w,h")
        return b

    face = box(args.face, "face") if args.layout != "center" else None
    game = box(args.game, "game")
    if args.layout == "face" and not face:
        p.error("--layout face needs --face x,y,w,h")

    words = [] if args.no_captions else load_words(args.video, args.words, start, end, args.model)
    out = Path(args.out or f"{Path(args.video).with_suffix('')}_short_{int(start)}.mp4")
    progress = lambda f, _msg: print(f"\rrendering... {f * 100:5.1f}%", end="", flush=True)
    make_short(args.video, start, end, out, face, game, args.title, words, progress)
    print(f"\ncreated {out} ({duration:.0f}s, {len(words)} caption words)")
