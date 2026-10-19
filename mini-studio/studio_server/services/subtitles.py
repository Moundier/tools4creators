"""Make subtitles for a video with Whisper (local AI speech-to-text, runs offline).

  python3 studio.py subtitles video.mkv                    # -> video.srt + video.words.json
  python3 studio.py subtitles video.mkv --model medium     # slower, more accurate
  python3 studio.py subtitles video.mkv --device cuda      # use the NVIDIA GPU

video.srt         upload it to YouTube (studio.py upload --srt) or load it in your editor
video.words.json  every word with its start/end time, used by `studio.py shorts` for animated captions
Models download into studio_server/ai_models/whisper/ the first time (small: ~480 MB, medium: ~1.5 GB).
"""
import argparse
import json
import os
import subprocess
import tempfile
import wave
from pathlib import Path

from ..paths import AI_MODELS

MODELS = AI_MODELS / "whisper"
MAX_LINE = 42  # characters per subtitle line, 2 lines per cue


def extract_audio(path, start=None, end=None):
    """16 kHz mono WAV of the video (or of start..end seconds) in a temp file."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    cmd = ["ffmpeg", "-v", "error", "-y"]
    if start is not None:
        cmd += ["-ss", str(start)]
    if end is not None:
        cmd += ["-to", str(end)]
    cmd += ["-i", str(path), "-vn", "-ac", "1", "-ar", "16000", tmp.name]
    subprocess.run(cmd, check=True)
    return tmp.name


def transcribe(path, model="small", lang="pt", device="cpu", start=None, end=None, report=None):
    """Words of the video as [{"word", "start", "end"}] in seconds of the original video.

    report(progress 0-1, message): optional progress callback.
    """
    import numpy as np
    from faster_whisper import WhisperModel

    wav = extract_audio(path, start, end)
    try:
        compute = "float16" if device == "cuda" else "int8"
        whisper = WhisperModel(model, device=device, compute_type=compute, download_root=str(MODELS))
        with wave.open(wav) as fh:  # pass samples directly (faster-whisper's own decoder breaks on new PyAV)
            audio = np.frombuffer(fh.readframes(fh.getnframes()), np.int16).astype(np.float32) / 32768
        segments, _ = whisper.transcribe(audio, language=lang, word_timestamps=True, vad_filter=True)
        offset, total = start or 0, max(len(audio) / 16000, 0.001)
        words = []
        for seg in segments:
            if report:
                report(min(1.0, seg.end / total), "transcribing")
            for w in seg.words:
                text = w.word.strip()
                if text:
                    words.append({"word": text, "start": round(w.start + offset, 3), "end": round(w.end + offset, 3)})
        return words
    finally:
        os.unlink(wav)


def group_cues(words, max_chars=2 * MAX_LINE, max_gap=0.6, max_len=6.0):
    """Group words into subtitle cues, breaking on pauses, sentence ends and length."""
    cues, cur = [], []
    for w in words:
        if cur:
            text = " ".join(x["word"] for x in cur)
            if (w["start"] - cur[-1]["end"] > max_gap or len(text) + 1 + len(w["word"]) > max_chars
                    or w["end"] - cur[0]["start"] > max_len
                    or (cur[-1]["word"][-1] in ".?!" and len(text) > 20)):
                cues.append(cur)
                cur = []
        cur.append(w)
    if cur:
        cues.append(cur)
    return cues


def two_lines(text):
    """Split a cue into at most 2 lines, as balanced as possible."""
    if len(text) <= MAX_LINE:
        return text
    words = text.split()
    best = min(range(1, len(words)), key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))))
    return " ".join(words[:best]) + "\n" + " ".join(words[best:])


def srt_time(t):
    ms = round(t * 1000)
    return "%02d:%02d:%02d,%03d" % (ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)


def to_srt(words):
    return cues_to_srt(cues_from_words(words))


def cues_from_words(words):
    """Editable cues [{"start", "end", "text"}] (what the .srt contains)."""
    return [{"start": c[0]["start"], "end": c[-1]["end"], "text": two_lines(" ".join(w["word"] for w in c))}
            for c in group_cues(words)]


def cues_to_srt(cues):
    return "\n".join(f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c['text'].strip()}\n"
                     for i, c in enumerate(cues, 1))


def parse_srt(text):
    """.srt text -> cues [{"start", "end", "text"}]."""
    def secs(t):
        h, m, rest = t.strip().replace(".", ",").split(":")
        s, ms = rest.split(",")
        return round(int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000, 3)
    cues = []
    for block in text.replace("\r", "").strip().split("\n\n"):
        lines = [l for l in block.split("\n") if l.strip()]
        times = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if times is None:
            continue
        a, b = lines[times].split("-->")
        cues.append({"start": secs(a), "end": secs(b), "text": "\n".join(lines[times + 1:])})
    return cues


def main(argv=None):
    p = argparse.ArgumentParser(prog="studio.py subtitles", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video")
    p.add_argument("--model", default="small", help="tiny, base, small (default), medium, large-v3")
    p.add_argument("--lang", default="pt", help="spoken language (default: pt)")
    p.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    args = p.parse_args(argv)

    video = Path(args.video)
    print(f"transcribing {video.name} with whisper {args.model} ({args.device})...")
    words = transcribe(video, args.model, args.lang, args.device)
    srt, js = video.with_suffix(".srt"), video.with_suffix(".words.json")
    srt.write_text(to_srt(words), encoding="utf-8")
    js.write_text("[\n" + ",\n".join(json.dumps(w, ensure_ascii=False) for w in words) + "\n]\n", encoding="utf-8")
    print(f"wrote {srt} and {js} ({len(words)} words)")
