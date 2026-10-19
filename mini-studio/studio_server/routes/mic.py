"""CASA NOVA Mic: status, a 10-second test that checks every effect, and (re)install with new settings."""
from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse

from ..models import job as jobs
from ..models import settings
from ..services import mic_setup

router = APIRouter(prefix="/api/mic")
TEST_DIR = settings.WORK / "mic_test"
WHISPER_MODELS = ("tiny", "base", "small", "medium", "large-v3")


@router.get("/status")
def status():
    try:
        return mic_setup.status()
    except Exception as e:  # pw-dump / wpctl missing or PipeWire down
        raise HTTPException(500, f"could not read the audio setup: {e}")


def _test(report, seconds):
    import time

    from ..services.mic_check import analyze

    start = time.time()
    raw, clean = mic_setup.record_pair(seconds, TEST_DIR, report=report)
    report(None, "analyzing")
    return analyze(raw, clean, mic_setup.read_config(), mic_setup.underruns(start))


@router.post("/test")
def test(body: dict = Body(default={})):
    seconds = int(body.get("seconds", 10))
    if not 5 <= seconds <= 30:
        raise HTTPException(400, "seconds must be 5-30")
    if not mic_setup.node_present():
        raise HTTPException(400, "CASA NOVA Mic is not running: install it first")
    return jobs.submit("mic_test", None, _test, seconds, lane="mic")


@router.post("/install")
def install(body: dict = Body(default={})):
    cfg = mic_setup.read_config()
    preset = body.get("preset") or cfg["preset"] or mic_setup.DEFAULT_PRESET
    if preset not in mic_setup.TEMPLATES:
        raise HTTPException(400, f"preset must be one of {', '.join(mic_setup.TEMPLATES)}")
    same = preset == cfg["preset"]  # switching preset resets the gain to that preset's default
    vad = float(body.get("vad") or cfg["vad"] or mic_setup.DEFAULT_VAD)
    denoise = float(body.get("denoise") or cfg["denoise"] or mic_setup.DEFAULT_DENOISE)
    makeup = body.get("makeup", cfg["makeup"] if same else None)
    makeup = None if makeup is None else float(makeup)
    gate = float(body.get("gate") or cfg["gate"] or mic_setup.DEFAULT_GATE)
    notch = body.get("notch", cfg["notch"]) or []
    try:
        notch = [float(f) for f in notch]
        mic_setup.check_tuning(vad, makeup or 0, denoise, gate, notch)
    except (TypeError, ValueError) as e:
        raise HTTPException(400, str(e))
    mic = body.get("mic", cfg["mic"])  # default: keep the mic chosen before
    default = bool(body.get("default", mic_setup.default_source() == mic_setup.NODE))

    def run(report):
        report(None, "downloading DeepFilterNet (first time) and restarting audio" if preset == "studio"
               else "restarting audio")
        mic_setup.install(preset, vad, makeup, mic or None, default, denoise, gate, notch)
        return mic_setup.status()
    return jobs.submit("mic_install", None, run, lane="mic")


def _transcribe(report, model):
    import time

    from ..services.subtitles import transcribe

    out = {"model": model}
    for i, name in enumerate(("raw", "clean")):
        report(i / 2, f"whisper {model}: {'raw mic' if name == 'raw' else 'CASA NOVA Mic'}")
        t = time.time()
        words = transcribe(TEST_DIR / f"{name}.wav", model=model,
                           report=lambda p, m=None, i=i: report((i + (p or 0)) / 2, None))
        out[name] = {"text": " ".join(w["word"] for w in words), "words": len(words),
                     "seconds": round(time.time() - t, 1)}
    return out


@router.post("/transcribe")
def transcribe_test(body: dict = Body(default={})):
    """Run Whisper on the last test recording (raw and clean) to see how well it understands you."""
    model = body.get("model") or settings.load()["whisper_model"]
    if model not in WHISPER_MODELS:
        raise HTTPException(400, f"model must be one of {', '.join(WHISPER_MODELS)}")
    if not all((TEST_DIR / n).is_file() for n in ("raw.wav", "clean.wav")):
        raise HTTPException(400, "record a microphone test first")
    return jobs.submit("whisper_test", None, _transcribe, model, lane="mic")


@router.get("/files/{name}")
def recording(name: str):
    if name not in ("raw.wav", "clean.wav") or not (TEST_DIR / name).is_file():
        raise HTTPException(404, "no test recording yet")
    return FileResponse(TEST_DIR / name, media_type="audio/wav", headers={"Cache-Control": "no-cache"})
