"""Install the "CASA NOVA Mic": a virtual microphone with AI noise suppression, EQ, compressor and limiter.

  python3 studio.py mic install              # process the default mic
  python3 studio.py mic install --default    # ...and make "CASA NOVA Mic" the default input
  python3 studio.py mic install --mic NODE   # process a specific mic (names: python3 studio.py mic mics)
  python3 studio.py mic test                 # 10 s test: records raw + processed at once and checks every effect
  python3 studio.py mic status | mics | uninstall

Then pick "CASA NOVA Mic" as the audio input in OBS, Discord, etc.
Presets (--preset): studio (default: DeepFilterNet noise/echo removal, broadcast EQ, two compressors, limiter)
or basic (RNNoise + simple EQ + one compressor, lighter on CPU).
Tuning: --makeup (studio: input gain dB; basic: makeup gain dB), --denoise and --gate (studio), --vad (basic),
--notch 77,990 (remove hum / whine tones; `mic test` finds them).
The chains are in studio_server/mic/studio.conf and basic.conf.
"""
import argparse
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

from ..paths import MIC, OUTPUT

TEMPLATES = {"studio": MIC / "studio.conf", "basic": MIC / "basic.conf"}
CONF = Path.home() / ".config" / "pipewire" / "pipewire.conf.d" / "casanova-mic.conf"
LADSPA_DIR = Path.home() / ".local" / "lib" / "ladspa"
RNNOISE = LADSPA_DIR / "librnnoise_ladspa.so"
RNNOISE_URL = "https://github.com/werman/noise-suppression-for-voice/releases/download/v1.10/linux-rnnoise.zip"
RNNOISE_SHA256 = "811390b6eb6e28dde023c70590c74d26e74ebb2e595bcf4b95af2341db160e99"
DEEPFILTER = LADSPA_DIR / "libdeep_filter_ladspa.so"
DEEPFILTER_URL = ("https://github.com/Rikorose/DeepFilterNet/releases/download/v0.5.6/"
                  "libdeep_filter_ladspa-0.5.6-x86_64-unknown-linux-gnu.so")
DEEPFILTER_SHA256 = "2ca3205c2911d389604a826a240e745597d50252b5cab81c8248252b335e2236"
SWH = {"SC4M": "sc4m_1916.so", "LIMITER": "fast_lookahead_limiter_1913.so", "AMP": "amp_1181.so",
       "GATE_PLUGIN": "gate_1410.so"}
SWH_DIRS = [Path("/usr/lib/ladspa"), Path("/usr/lib/x86_64-linux-gnu/ladspa"), Path("/usr/lib64/ladspa")]
NODE = "casanova_mic"


def run(*cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, capture_output=True, **kw).stdout


def find_swh(name):
    for d in SWH_DIRS:
        if (d / name).is_file():
            return d / name
    raise RuntimeError(f"{name} not found. Install the LADSPA plugins with:  sudo apt install swh-plugins")


def install_rnnoise():
    if RNNOISE.is_file():
        return
    print("downloading RNNoise plugin (werman/noise-suppression-for-voice v1.10)...")
    data = urllib.request.urlopen(RNNOISE_URL, timeout=60).read()
    if hashlib.sha256(data).hexdigest() != RNNOISE_SHA256:
        raise RuntimeError("RNNoise download checksum mismatch, not installing it")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        so = z.read("linux-rnnoise/ladspa/librnnoise_ladspa.so")
    LADSPA_DIR.mkdir(parents=True, exist_ok=True)
    RNNOISE.write_bytes(so)


def install_deepfilter():
    if DEEPFILTER.is_file():
        return
    print("downloading DeepFilterNet plugin (Rikorose/DeepFilterNet v0.5.6, ~50 MB)...")
    data = urllib.request.urlopen(DEEPFILTER_URL, timeout=300).read()
    if hashlib.sha256(data).hexdigest() != DEEPFILTER_SHA256:
        raise RuntimeError("DeepFilterNet download checksum mismatch, not installing it")
    LADSPA_DIR.mkdir(parents=True, exist_ok=True)
    DEEPFILTER.write_bytes(data)


def nodes():
    """{node name: (id, description, media class)} from pw-dump."""
    out = {}
    text = run("pw-dump").strip()
    objects, _ = json.JSONDecoder().raw_decode(text)  # right after a restart pw-dump can print extra data
    for obj in objects:
        props = (obj.get("info") or {}).get("props") or {}
        if obj.get("type") == "PipeWire:Interface:Node" and "node.name" in props:
            out[props["node.name"]] = (obj["id"], props.get("node.description", ""), props.get("media.class", ""))
    return out


def sources():
    """[(node name, description)] of the real microphones."""
    return [(n, d) for n, (_, d, cls) in nodes().items() if cls == "Audio/Source" and n != NODE]


def restart_pipewire():
    print("restarting PipeWire (audio stops for a second)...")
    subprocess.run(["systemctl", "--user", "restart", "pipewire", "pipewire-pulse", "wireplumber"], check=True)
    for _ in range(20):  # wait for the new node to appear
        time.sleep(0.5)
        if node_present():
            return True
    return False


def node_present():
    try:
        return NODE in nodes()
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return False


def default_source():
    for line in run("wpctl", "inspect", "@DEFAULT_AUDIO_SOURCE@").splitlines():
        if "node.name" in line:
            return line.split("=", 1)[1].strip().strip('"')
    return "?"


DEFAULT_PRESET = "studio"
DEFAULT_VAD, DEFAULT_DENOISE = 60.0, 100.0
DEFAULT_MAKEUP = {"studio": 12.0, "basic": 6.0}   # studio: input gain before the compressors; basic: makeup gain
DEFAULT_GATE = -60.0                              # studio: below this (dB, before the gain) the gate lowers the hiss
NOTCH_AT = {"studio": ("hp2:Out", "boom:In"), "basic": ("highpass:Out", "mud:In")}  # where the notches go
MAX_NOTCHES = 4


def notch_graph(preset, freqs):
    """(nodes, links) text for the notch filters between NOTCH_AT[preset] (a plain link when there are none)."""
    src, dst = NOTCH_AT[preset]
    nodes, links, prev = [], [], src
    for i, f in enumerate(freqs, 1):
        nodes.append(f'                    {{ type = builtin  name = notch{i}  label = bq_notch  '
                     f'control = {{ "Freq" = {f:.1f}  "Q" = 8.0 }} }}')
        links.append(f'                    {{ output = "{prev}"  input = "notch{i}:In" }}')
        prev = f"notch{i}:Out"
    links.append(f'                    {{ output = "{prev}"  input = "{dst}" }}')
    return "\n".join(nodes), "\n".join(links)


def check_tuning(vad, makeup, denoise, gate, notch):
    """ValueError if a setting is out of range."""
    if not (0 <= vad <= 99 and 0 <= makeup <= 30 and 0 <= denoise <= 100 and -80 <= gate <= -30):
        raise ValueError("vad must be 0-99 %, gain 0-30 dB, denoise 0-100 dB and gate -80 to -30 dB")
    if len(notch) > MAX_NOTCHES or not all(40 <= f <= 8000 for f in notch):
        raise ValueError(f"notch: up to {MAX_NOTCHES} frequencies, 40-8000 Hz")


def install(preset=DEFAULT_PRESET, vad=DEFAULT_VAD, makeup=None, mic=None, default=False, denoise=DEFAULT_DENOISE,
            gate=DEFAULT_GATE, notch=()):
    """Write the filter-chain config and restart PipeWire. Raises RuntimeError / ValueError on problems."""
    if preset not in TEMPLATES:
        raise ValueError(f"preset must be one of {', '.join(TEMPLATES)}")
    makeup = DEFAULT_MAKEUP[preset] if makeup is None else makeup
    notch = sorted({round(float(f)) for f in notch})
    if mic and mic not in [n for n, _ in sources()]:
        raise ValueError(f"unknown mic {mic!r}; see: python3 studio.py mic mics")
    check_tuning(vad, makeup, denoise, gate, notch)
    if preset == "studio":
        install_deepfilter()
    else:
        install_rnnoise()
    conf = TEMPLATES[preset].read_text()
    notch_nodes, notch_links = notch_graph(preset, notch)
    values = {"RNNOISE": str(RNNOISE), "DEEPFILTER": str(DEEPFILTER), "VAD": f"{vad:.1f}",
              "DENOISE": f"{denoise:.1f}", "MAKEUP": f"{makeup:.1f}", "GATE": f"{gate:.1f}",
              "NOTCH_NODES": notch_nodes, "NOTCH_LINKS": notch_links,
              "TARGET": f'target.object = "{mic}"' if mic else "",
              **{k: str(find_swh(v)) for k, v in SWH.items()}}
    conf = re.sub(r"@(\w+)@", lambda m: values[m.group(1)], conf)
    CONF.parent.mkdir(parents=True, exist_ok=True)
    CONF.write_text(conf)
    print("wrote", CONF)
    if not restart_pipewire():
        raise RuntimeError("'CASA NOVA Mic' did not appear. Check: journalctl --user -u pipewire -n 50")
    if default:
        set_default()


def set_default():
    """Make CASA NOVA Mic the system default input (retries while PipeWire settles after a restart)."""
    for _ in range(10):
        try:
            run("wpctl", "set-default", str(nodes()[NODE][0]))
            return
        except (KeyError, ValueError, subprocess.CalledProcessError):
            time.sleep(0.5)
    raise RuntimeError("could not make CASA NOVA Mic the default input")


def read_config():
    """Settings of the installed chain: {"installed", "preset", "vad", "denoise", "makeup", "gate", "notch", "mic"}."""
    if not CONF.is_file():
        return {"installed": False, "preset": None, "vad": None, "denoise": None, "makeup": None, "gate": None,
                "notch": [], "mic": None}
    text = CONF.read_text()
    num = lambda pat: float(m.group(1)) if (m := re.search(pat, text)) else None
    mic = re.search(r'target\.object = "([^"]+)"', text)
    preset = m.group(1) if (m := re.search(r"^# preset: (\w+)", text, re.M)) else "basic"
    makeup = num(r'"Amps gain \(dB\)" = ([\d.]+)') if preset == "studio" else num(r'"Makeup gain \(dB\)" = ([\d.]+)')
    return {"installed": True, "preset": preset, "vad": num(r'"VAD Threshold \(%\)" = ([\d.]+)'),
            "denoise": num(r'"Attenuation Limit \(dB\)" = ([\d.]+)'), "makeup": makeup,
            "gate": num(r'"Threshold \(dB\)" = (-?[\d.]+)'),
            "notch": [float(f) for f in re.findall(r'label = bq_notch\s+control = \{ "Freq" = ([\d.]+)', text)],
            "mic": mic.group(1) if mic else None}


def raw_source():
    """The physical mic the chain listens to (the configured one, or the default input)."""
    cfg, mics = read_config(), dict(sources())
    if cfg["mic"] in mics:
        return cfg["mic"]
    default = default_source()
    return default if default in mics else next(iter(mics), None)


def status():
    cfg, mics = read_config(), dict(sources())
    raw = raw_source()
    return {**cfg, "running": node_present(), "rnnoise": RNNOISE.is_file(), "deepfilter": DEEPFILTER.is_file(),
            "default_source": default_source(),
            "is_default": default_source() == NODE, "raw_source": raw, "raw_source_name": mics.get(raw, raw),
            "sources": [{"name": n, "description": d} for n, d in mics.items()]}


def cmd_install(args):
    try:
        notch = [float(f) for f in args.notch.split(",") if f.strip()] if args.notch else []
        install(args.preset, args.vad, args.makeup, args.mic, args.default, args.denoise, args.gate, notch)
    except (RuntimeError, ValueError) as e:
        sys.exit(str(e))
    print('ready: choose "CASA NOVA Mic" as the input in OBS / Discord'
          + (" (it is now the default input)" if args.default else ""))


def cmd_uninstall(args):
    if CONF.exists():
        CONF.unlink()
        print("removed", CONF)
    restart_pipewire()
    print("CASA NOVA Mic removed" if not node_present() else "warning: node still present")


def cmd_status(args):
    print("config:", CONF if CONF.exists() else "not installed")
    cfg = read_config()
    print("preset:", cfg["preset"] or "-", "| gain:", cfg["makeup"], "| denoise:", cfg["denoise"], "| vad:", cfg["vad"],
          "| gate:", cfg["gate"], "| notch:", ", ".join(f"{f:.0f} Hz" for f in cfg["notch"]) or "-")
    print("RNNoise plugin:", RNNOISE if RNNOISE.is_file() else "missing")
    print("DeepFilterNet plugin:", DEEPFILTER if DEEPFILTER.is_file() else "missing")
    print("CASA NOVA Mic:", "running" if node_present() else "not running")
    print("default input:", default_source())


def cmd_mics(args):
    for name, desc in sources():
        print(f"  {name}\n      {desc}")


def underruns(since):
    """How many times DeepFilterNet fell behind (clicks) since the unix time `since`; None if the journal can't be read."""
    try:
        out = run("journalctl", "--user", "-u", "pipewire", "--since", f"@{int(since)}", "--no-pager", "-o", "cat")
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.count("Underrun detected")


def record_pair(seconds, out_dir, raw=None, report=None):
    """Record the raw mic and the CASA NOVA Mic at the same time (same words in both). Returns (raw, clean) paths."""
    if not node_present():
        raise RuntimeError("CASA NOVA Mic is not running; install it first")
    raw = raw or raw_source()
    if not raw:
        raise RuntimeError("no microphone found")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = (out_dir / "raw.wav", out_dir / "clean.wav")
    procs = [subprocess.Popen(["pw-record", "--target", target, "--rate", "48000", "--channels", "1", str(path)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
             for target, path in zip((raw, NODE), paths)]
    try:
        for i in range(seconds * 10):
            time.sleep(0.1)
            if report:
                report((i + 1) / (seconds * 10), "recording")
            if any(p.poll() is not None for p in procs):
                raise RuntimeError("recording stopped early (is the microphone busy or unplugged?)")
    finally:
        for p in procs:
            p.terminate()
            p.wait()
    return paths


def cmd_test(args):
    from .mic_check import analyze

    print(f"Talk normally for ~{args.seconds - 3} s, then stay quiet for the last 3 s...")
    start = time.time()
    try:
        raw, clean = record_pair(args.seconds, OUTPUT / "mic_test", args.mic)
    except RuntimeError as e:
        sys.exit(str(e))
    result = analyze(raw, clean, read_config(), underruns(start))
    for c in result["checks"]:
        print(f"  {'OK ' if c['ok'] else '!! '} {c['title']}: {c['detail']}")
    if result["suggestion"]:
        print("\nsuggestion:", result["suggestion"]["command"])
    print(f"\nrecordings: {raw}  {clean}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="studio.py mic", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("install", help="install / update the CASA NOVA Mic")
    i.add_argument("--mic", help="mic node name to process (default: the system default mic)")
    i.add_argument("--default", action="store_true", help="make CASA NOVA Mic the default input")
    i.add_argument("--preset", choices=list(TEMPLATES), default=DEFAULT_PRESET,
                   help="studio: DeepFilterNet + broadcast EQ + 2 compressors (default); basic: RNNoise, lighter")
    i.add_argument("--makeup", type=float, help="studio: input gain dB (default 12); basic: makeup gain dB (default 6)")
    i.add_argument("--denoise", type=float, default=DEFAULT_DENOISE, help="studio: max noise removal in dB (default 100)")
    i.add_argument("--vad", type=float, default=DEFAULT_VAD, help="basic: noise gate threshold %% (higher = stricter)")
    i.add_argument("--gate", type=float, default=DEFAULT_GATE,
                   help="studio: hiss gate threshold dB before the gain (default -60; higher = stricter)")
    i.add_argument("--notch", help="hum / whine tones to remove, in Hz, comma separated (e.g. 77,990; max 4)")
    t = sub.add_parser("test", help="record raw + processed at once and check every effect")
    t.add_argument("--mic", help="raw mic node name (default: the one the chain listens to)")
    t.add_argument("--seconds", type=int, default=10)
    for name in ("uninstall", "status", "mics"):
        sub.add_parser(name)
    args = p.parse_args(argv)
    for tool in ("pw-dump", "wpctl", "pw-record"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found: sudo apt install pipewire-bin wireplumber")
    globals()["cmd_" + args.cmd](args)
