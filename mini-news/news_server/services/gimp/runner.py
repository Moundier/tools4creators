"""Launch GIMP 3 headlessly and run render / export jobs through gimp_render.py.

A batch is split over several GIMP processes running at the same time (GIMP's batch work uses about one core, so
20 templates in parallel workers take a fraction of one session's time). MINI_NEWS_GIMP_WORKERS=1 = one session.
Also opens an .xcf in the GIMP app, so you can fix a template by hand."""
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
TIMEOUT = 300   # seconds per GIMP process (one batch of 20 templates takes well under a minute)
WORKERS = int(os.environ.get("MINI_NEWS_GIMP_WORKERS") or min(6, max(1, (os.cpu_count() or 2) // 2)))


def gimp_console():
    """Prefer a native gimp-console; fall back to the Flathub GIMP."""
    for exe in ("gimp-console-3.2", "gimp-console-3.0", "gimp-console-3", "gimp-console"):
        if shutil.which(exe):
            return [exe]
    if shutil.which("flatpak") and subprocess.run(["flatpak", "info", "org.gimp.GIMP"], capture_output=True).returncode == 0:
        return ["flatpak", "run", "--command=gimp-console", "org.gimp.GIMP"]
    raise RuntimeError("GIMP 3 not found. Install it with: flatpak install flathub org.gimp.GIMP")


def gimp_app():
    for exe in ("gimp-3.2", "gimp-3.0", "gimp-3", "gimp"):
        if shutil.which(exe):
            return [exe]
    if shutil.which("flatpak"):
        return ["flatpak", "run", "org.gimp.GIMP"]
    raise RuntimeError("GIMP 3 not found. Install it with: flatpak install flathub org.gimp.GIMP")


def _session(jobs, report, log):
    """Run some jobs in one GIMP process; report(out, ok) as each one finishes."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", prefix="newsjob_", dir="/tmp", delete=False) as fh:
        json.dump({"jobs": jobs}, fh)
        job_path = fh.name
    # gimp/*.py run inside GIMP's own Python; ROOT tells gimp_render.py where its sibling modules are
    script = (f"exec(open({str(SCRIPTS / 'gimp_render.py')!r}).read(), "
              f"{{'JOB_PATH': {job_path!r}, 'ROOT': {str(SCRIPTS)!r}}})")
    cmd = gimp_console() + ["-i", "--batch-interpreter=python-fu-eval", "-b", script, "--quit"]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        timer = threading.Timer(TIMEOUT, proc.kill)
        timer.start()
        for line in proc.stdout:   # JOB_OK / JOB_FAIL lines arrive as GIMP finishes each image
            log.append(line)
            m = re.match(r"JOB_(OK|FAIL) (.+)", line.strip())
            if m:
                report(m.group(2), m.group(1) == "OK")
        proc.wait()
        timer.cancel()
    except OSError as e:
        log.append(f"could not start GIMP: {e}\n")
    finally:
        os.unlink(job_path)


def run_jobs(jobs, on_done=None):
    """Run the jobs in up to WORKERS GIMP processes at once. on_done(out, ok) is called as each one finishes
    (for progress). Returns {out: True/False}. Raises RuntimeError only when no job could be rendered."""
    results, log, lock = {}, [], threading.Lock()

    def report(out, ok):
        with lock:   # several GIMP processes report at once: keep progress counters consistent
            results[out] = ok
            if on_done:
                on_done(out, ok)

    n = max(1, min(WORKERS, len(jobs)))
    chunks = [jobs[i::n] for i in range(n)]   # round-robin: the heavy photo templates are spread out
    if n == 1:
        _session(jobs, report, log)
    else:
        threads = [threading.Thread(target=_session, args=(chunk, report, log), daemon=True) for chunk in chunks]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    for j in jobs:
        results.setdefault(j["out"], False)
    if not any(results.values()) and jobs:
        raise RuntimeError("GIMP couldn't render: " + "".join(log)[-800:])
    return results


def open_in_gimp(xcf):
    """Open the .xcf in the GIMP app (detached: it keeps running after mini-news stops)."""
    subprocess.Popen(gimp_app() + [str(xcf)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
