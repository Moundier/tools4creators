"""Launch GIMP 3 headlessly and run a list of render jobs through gimp_render.py."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

from ...paths import GIMP_SCRIPTS


def gimp_command():
    """Prefer a native gimp-console; fall back to the Flathub GIMP."""
    for exe in ("gimp-console-3.2", "gimp-console-3.0", "gimp-console-3", "gimp-console"):
        if shutil.which(exe):
            return [exe]
    if shutil.which("flatpak"):
        return ["flatpak", "run", "--command=gimp-console", "org.gimp.GIMP"]
    sys.exit("GIMP 3 not found. Install it with: flatpak install flathub org.gimp.GIMP")


def run_jobs(jobs):
    """Render the jobs in one GIMP session. Returns the created PNG paths; exits if any job failed."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", prefix="thumbjob_", dir="/tmp", delete=False) as fh:
        json.dump({"jobs": jobs}, fh)
        job_path = fh.name

    # gimp/*.py run inside GIMP's own Python; ROOT tells gimp_render.py where its sibling modules are
    script = (f"exec(open({str(GIMP_SCRIPTS / 'gimp_render.py')!r}).read(), "
              f"{{'JOB_PATH': {job_path!r}, 'ROOT': {str(GIMP_SCRIPTS)!r}}})")
    cmd = gimp_command() + ["-i", "--batch-interpreter=python-fu-eval", "-b", script, "--quit"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    finally:
        os.unlink(job_path)

    output = proc.stdout + proc.stderr
    ok = re.findall(r"THUMB_OK (.+)", output)
    if len(ok) != len(jobs):
        print(output, file=sys.stderr)
        for path in ok:
            print("created", path, "(+ .xcf)")
        sys.exit(f"{len(jobs) - len(ok)} thumbnail(s) failed")
    return ok
