"""Check the CASA NOVA Mic chain on a test recording: raw mic vs processed, recorded at the same time.

Every effect in the installed chain (studio_server/mic/studio.conf or basic.conf) gets a measurable check:
  denoise        background noise between words goes down, relative to the voice (DeepFilterNet or RNNoise)
  words kept     the noise removal doesn't eat your words
  hiss           (studio) the high "shhh" between words stays far below the voice (gate + low-pass 14 kHz)
  hum            no steady tone (hum / whine) left between words (notch filters; tones found in the raw mic)
  dropouts       no gaps in the audio (raw gaps: USB / cable; only processed: the CPU can't keep up)
  real time      (studio) DeepFilterNet kept up with the audio (no "Underrun detected" in the PipeWire journal)
  high-pass      rumble below 80-100 Hz goes down
  EQ presence    2.5-5 kHz goes up relative to the body of the voice
  compressor     loud moments get less gain than soft ones
  gain           the voice ends up at a good level for OBS / YouTube
  limiter        peaks never pass -1 dB
"""
import subprocess

import numpy as np

RATE = 48000
FRAME = RATE // 20          # 50 ms frames
FLOOR = -100.0              # dB used for digital silence
TARGET = (-24.0, -12.0)     # good speech level (frame RMS, dBFS) after the chain


def load(path):
    """Mono float samples (-1..1) at 48 kHz, decoded with ffmpeg."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(RATE), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def frame_db(x):
    n = len(x) // FRAME
    if n == 0:
        return np.array([FLOOR])
    rms = np.sqrt(np.mean(x[:n * FRAME].reshape(n, FRAME) ** 2, axis=1))
    return np.maximum(20 * np.log10(rms + 1e-10), FLOOR)


def band_db(x, lo, hi):
    """Energy of a frequency band (dB), averaged over 8192-sample windows."""
    win, total = 8192, None
    if len(x) < win:
        return FLOOR
    for i in range(0, len(x) - win, win // 2):
        spec = np.abs(np.fft.rfft(x[i:i + win] * np.hanning(win))) ** 2
        total = spec if total is None else total + spec
    freqs = np.fft.rfftfreq(win, 1 / RATE)
    return float(10 * np.log10(total[(freqs >= lo) & (freqs < hi)].sum() + 1e-12))


def band_level(x, lo, hi):
    """RMS level (dBFS) of the lo..hi Hz part of x."""
    if len(x) < 2:
        return FLOOR
    power = np.abs(np.fft.rfft(x)) ** 2
    freqs = np.fft.rfftfreq(len(x), 1 / RATE)
    share = power[(freqs >= lo) & (freqs < hi)].sum() / (power.sum() + 1e-20)
    return float(max(10 * np.log10(np.mean(x.astype(np.float64) ** 2) * share + 1e-20), FLOOR))


def tones(x, lo=40, hi=8000, prominence=15.0, limit=4):
    """Steady tones (hum, whine) in x: [(Hz, dB above the noise around it)], strongest first."""
    win = 16384
    if len(x) < win:
        return []
    spec = sum(np.abs(np.fft.rfft(x[i:i + win] * np.hanning(win))) ** 2 for i in range(0, len(x) - win + 1, win // 2))
    db = 10 * np.log10(spec + 1e-20)
    freqs = np.fft.rfftfreq(win, 1 / RATE)
    found = []
    for i in np.where((freqs >= lo) & (freqs <= hi))[0]:
        around = np.r_[db[max(0, i - 60):max(0, i - 4)], db[i + 5:i + 61]]
        rise = db[i] - np.median(around)
        if rise >= prominence and db[i] == db[max(0, i - 4):i + 5].max():
            found.append((float(freqs[i]), float(rise)))
    merged = []
    for f, r in sorted(found, key=lambda t: -t[1]):
        if all(abs(f - g) > 10 for g, _ in merged):
            merged.append((round(f), round(r, 1)))
    return merged[:limit]


def dropouts(x):
    """Gaps in x: runs of exact digital zero (>= 0.3 ms) with sound right before and after them."""
    zero = np.r_[0, (x == 0).astype(np.int8), 0]
    edges = np.diff(zero)
    starts, ends = np.where(edges == 1)[0], np.where(edges == -1)[0]
    n = 0
    for a, b in zip(starts, ends):
        if b - a >= 16 and a >= 100 and b + 100 <= len(x) and \
                np.abs(x[a - 100:a]).max() > 0.01 and np.abs(x[b:b + 100]).max() > 0.01:
            n += 1
    return n


def downsample(db, points=240):
    """Max per bucket so short words stay visible in the chart."""
    edges = np.linspace(0, len(db), min(points, len(db)) + 1).astype(int)
    return [round(float(max(db[a:b].max(), -80)), 1) for a, b in zip(edges, edges[1:]) if b > a]


def analyze(raw_path, clean_path, config, underruns=None):
    """underruns: "Underrun detected" lines DeepFilterNet logged during the test (None = unknown)."""
    raw, clean = load(raw_path), load(clean_path)
    lead = int(np.argmax(raw != 0)) if raw.any() else 0   # pw-record starts with a moment of digital zero
    n = min(len(raw), len(clean))
    raw, clean = raw[lead:n], clean[lead:n]
    n -= lead
    rdb, cdb = frame_db(raw), frame_db(clean)
    m = min(len(rdb), len(cdb))
    rdb, cdb = rdb[:m], cdb[:m]

    r_noise, c_noise = float(np.percentile(rdb, 10)), float(np.percentile(cdb, 10))
    speech = rdb > r_noise + 15                       # frames where you were talking (from the raw mic)
    has_voice = speech.sum() >= 10                    # at least half a second of talking
    peak = lambda x: float(20 * np.log10(np.abs(x).max() + 1e-10))
    metrics = {
        "raw": {"noise": round(r_noise, 1), "peak": round(peak(raw), 1),
                "speech": round(float(np.median(rdb[speech])), 1) if has_voice else None},
        "clean": {"noise": round(c_noise, 1), "peak": round(peak(clean), 1),
                  "speech": round(float(np.median(cdb[speech])), 1) if has_voice else None},
    }
    preset = config.get("preset") or "basic"
    studio = preset == "studio"
    vad, denoise = config.get("vad") or 60.0, config.get("denoise") or 100.0
    makeup = config.get("makeup") or (12.0 if studio else 6.0)
    gate = config.get("gate") or -60.0
    notch = [float(f) for f in config.get("notch") or []]
    checks, new_vad, new_denoise, new_makeup, new_gate, new_notch = [], vad, denoise, makeup, gate, list(notch)
    denoise_label = f"DeepFilterNet (max {denoise:.0f} dB)" if studio else "RNNoise + noise gate"
    gain_label = f"input gain {makeup:.0f} dB" if studio else f"makeup gain {makeup:.0f} dB"

    def check(key, title, ok, detail, effect):
        checks.append({"key": key, "title": title, "ok": bool(ok), "detail": detail, "effect": effect})

    if not has_voice:
        check("voice", "Voice detected", False,
              "Almost no talking was recorded. Talk normally during the test (stay quiet only at the end) and try again.", "test")
    # compare the noise to the voice: the chain adds gain, so absolute levels would hide what the denoiser did
    r_voice = metrics["raw"]["speech"] if has_voice else r_noise
    c_voice = metrics["clean"]["speech"] if has_voice else c_noise
    r_gap, c_gap = r_voice - r_noise, c_voice - c_noise
    noise_drop = c_gap - r_gap if has_voice else r_noise - c_noise
    check("noise", "Background noise removed", noise_drop >= 10,
          f"Noise between words: {r_gap:.0f} dB below your voice raw → "
          f"{'silence' if c_noise <= FLOOR + 1 else f'{c_gap:.0f} dB below'} processed ({noise_drop:.0f} dB better)."
          + ("" if noise_drop >= 10 else " Raise the noise removal." if studio else " Raise the noise gate (VAD)."),
          denoise_label)
    quiet = np.repeat(rdb <= r_noise + 6, FRAME)[:n]   # samples between words (from the raw mic)
    r_quiet, c_quiet = raw[:len(quiet)][quiet], clean[:len(quiet)][quiet]
    if has_voice:
        kept = float(np.mean(cdb[speech] > max(c_noise, FLOOR + 1) + 10))
        check("words", "Your words are kept", kept >= 0.85,
              f"{kept * 100:.0f}% of the talking came through the noise removal."
              + ("" if kept >= 0.85 else " Words are being cut: " + ("lower the noise removal." if studio else
                                                                     "lower the VAD threshold.")),
              denoise_label if studio else f"noise gate (VAD {vad:.0f}%)")
        if studio:
            if kept < 0.85:
                new_denoise = max(30.0, denoise - 30)
            elif noise_drop < 10:
                new_denoise = 100.0
        elif kept < 0.85:
            new_vad = max(20.0, vad - 15)
        elif noise_drop < 10:
            new_vad = min(95.0, vad + 15)

        if studio:
            hiss = band_level(c_quiet, 6000, 20000)
            hiss_gap = c_voice - hiss
            check("hiss", "No hiss (shhh) between words", hiss_gap >= 50 or hiss <= FLOOR + 1,
                  f"The high hiss between words is {hiss_gap:.0f} dB below your voice (good: 50+)."
                  + ("" if hiss_gap >= 50 else " Raise the gate so it lowers the hiss between words."),
                  f"gate {gate:.0f} dB + low-pass 14 kHz")
            soft = float(np.percentile(rdb[speech], 10))      # the softest words must still open the gate
            fit = float(np.clip(round(min(r_noise + 12, soft - 6)), -80, -30))
            if kept < 0.85:
                new_gate = max(-80.0, min(gate, fit) - 6)
            elif hiss_gap < 50 and hiss > FLOOR + 1:
                new_gate = max(gate, fit) if fit > gate else min(-30.0, gate + 6)

        lf_raw, lf_clean = band_db(raw, 20, 80), band_db(clean, 20, 80)
        body_raw, body_clean = band_db(raw, 300, 2500), band_db(clean, 300, 2500)
        lf_drop = (lf_raw - body_raw) - (lf_clean - body_clean)
        check("highpass", "Rumble below 80 Hz cut", lf_drop >= 3 or lf_raw - body_raw < -35,
              f"Low rumble is {lf_drop:.0f} dB lower relative to the voice."
              if lf_raw - body_raw >= -35 else "Your mic had almost no rumble to remove.",
              "high-pass 100 Hz" if studio else "high-pass 80 Hz")
        pres = (band_db(clean, 2500, 5000) - body_clean) - (band_db(raw, 2500, 5000) - body_raw)
        check("presence", "Voice clarity (presence) boosted", pres >= 0.5,
              f"2.5–5 kHz is {pres:+.1f} dB relative to the body of the voice.",
              "EQ +2.5 dB 4.5 kHz, −3 dB 320 Hz" if studio else "EQ +3 dB 3.5 kHz, −3 dB 300 Hz")
        # a compressor gives loud moments less gain than soft ones: gain falls as the input gets louder
        slope = float(np.polyfit(rdb[speech], cdb[speech] - rdb[speech], 1)[0])
        check("compressor", "Loud and soft words evened out", slope <= -0.1,
              f"Every 10 dB louder you speak gets {abs(slope) * 10:.1f} dB {'less' if slope < 0 else 'more'} boost."
              + ("" if slope <= -0.1 else " The voice may be too quiet to reach the compressor: raise the gain."),
              "leveler 2.5:1 + peak 4:1" if studio else "compressor 3:1")
        level = metrics["clean"]["speech"]
        good = TARGET[0] <= level <= TARGET[1]
        check("level", "Voice level is right", good,
              f"Your voice sits at {level:.0f} dBFS (good: {TARGET[0]:.0f} to {TARGET[1]:.0f})."
              + ("" if good else " Too quiet: raise the gain." if level < TARGET[0] else " Too loud: lower the gain."),
              gain_label)
        if not good:
            new_makeup = float(np.clip(round(makeup + (-18 - level)), 0, 30 if studio else 24))
    raw_tones = tones(r_quiet)
    left = [(f, r) for f, r in tones(c_quiet) if c_quiet.any()]
    raw_txt = ", ".join(f"{f} Hz" for f, _ in raw_tones)
    check("hum", "No hum or whine between words", not left,
          ("No steady tone left." if not left else
           "Steady tones still audible: " + ", ".join(f"{f} Hz (+{r:.0f} dB)" for f, r in left) + ".")
          + (f" The raw mic has tones at {raw_txt}: usually the laptop charger or USB (ground loop)." if raw_tones else ""),
          "notch " + ", ".join(f"{f:.0f} Hz" for f in notch) if notch else "notch filters (none yet)")
    if left:
        wanted = [f for f, _ in raw_tones] + [f for f, _ in left]
        for f in wanted:
            if len(new_notch) < 4 and all(abs(f - g) > 10 for g in new_notch):
                new_notch.append(float(f))

    r_drop, c_drop = dropouts(raw), dropouts(clean)
    check("dropouts", "No gaps in the audio", r_drop == 0 and c_drop == 0,
          "No gaps found." if r_drop == 0 and c_drop == 0 else
          f"{r_drop} gap(s) in the raw mic: the USB connection / cable drops audio (try another port, no hub)."
          if r_drop else f"{c_drop} gap(s) only in the processed audio: the computer can't keep up.",
          "USB / CPU")
    if studio and underruns is not None:
        # one underrun right after the stream starts is DeepFilterNet warming up; more means the CPU can't keep up
        check("realtime", "Noise removal keeps up in real time", underruns <= 1,
              "DeepFilterNet kept up the whole time." if underruns == 0 else
              "DeepFilterNet hiccuped once while starting (normal)." if underruns == 1 else
              f"DeepFilterNet fell behind {underruns} time(s) (clicks / choppy audio). "
              "Close heavy programs or use the Basic preset.", "DeepFilterNet")

    c_peak = metrics["clean"]["peak"]
    check("limiter", "Peaks stay under −1 dB", c_peak <= -0.5,
          f"Loudest peak: {metrics['raw']['peak']:.1f} dB raw → {c_peak:.1f} dB.", "limiter −1 dB")

    suggestion = None
    new_notch = sorted(round(f) for f in new_notch)
    if (new_vad, new_denoise, new_makeup, new_gate, new_notch) != (vad, denoise, makeup, gate, sorted(round(f) for f in notch)):
        extra = f"--denoise {new_denoise:.0f} --gate {new_gate:.0f}" if studio else f"--vad {new_vad:.0f}"
        if new_notch:
            extra += " --notch " + ",".join(str(f) for f in new_notch)
        suggestion = {"preset": preset, "vad": new_vad, "denoise": new_denoise, "makeup": new_makeup,
                      "gate": new_gate, "notch": new_notch,
                      "command": f"python3 studio.py mic install --preset {preset} {extra} --makeup {new_makeup:.0f}"}
    return {"checks": checks, "metrics": metrics, "suggestion": suggestion, "seconds": round(n / RATE, 1),
            "levels": {"raw": downsample(rdb), "clean": downsample(cdb)},
            "raw_issues": {"tones": [f for f, _ in raw_tones], "dropouts": r_drop}}
