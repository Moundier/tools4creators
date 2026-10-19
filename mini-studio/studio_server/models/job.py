"""Background jobs (Whisper, rembg, GIMP, ffmpeg, uploads) with progress for the UI to poll."""
import contextvars
import itertools
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

from . import channel

_jobs = {}
_ids = itertools.count(1)
_lock = threading.Lock()
# heavy CPU work runs one at a time; uploads get their own lane so they don't wait for renders
_pools = {"work": ThreadPoolExecutor(1, thread_name_prefix="work"),
          "upload": ThreadPoolExecutor(1, thread_name_prefix="upload"),
          "mic": ThreadPoolExecutor(1, thread_name_prefix="mic")}  # mic test/install: never wait behind a render


def submit(kind, project, fn, *args, lane="work", **kwargs):
    """Run fn(report, *args, **kwargs) in the background; returns the job dict.
    The job runs with a copy of the caller's context, so it keeps the channel that started it."""
    job = {"id": str(next(_ids)), "kind": kind, "project": project, "channel": channel.current.get(), "status": "queued", "progress": None,
           "message": "waiting", "log": [], "result": None, "error": None, "created": time.time()}
    with _lock:
        _jobs[job["id"]] = job

    def report(progress=None, message=None):
        if progress is not None:
            job["progress"] = round(float(progress), 3)
        if message and message != job["message"]:
            job["message"] = message
            job["log"].append(message)

    def run():
        job["status"] = "running"
        report(None, "started")
        try:
            job["result"] = fn(report, *args, **kwargs)
            job["status"], job["progress"] = "done", 1.0
            report(None, "done")
        except BaseException as e:  # includes SystemExit from CLI helpers
            traceback.print_exc()
            job["status"], job["error"] = "error", str(e) or e.__class__.__name__

    _pools[lane].submit(contextvars.copy_context().run, run)
    return job


def get(job_id):
    return _jobs.get(job_id)


def running_for(pid):
    """Unfinished jobs for this recording in any channel."""
    return [j for j in _jobs.values() if j["project"] == pid and j["status"] in ("queued", "running")]


def for_project(pid):
    return [j for j in _jobs.values() if j["project"] == pid and j["channel"] == channel.current.get()
            and j["status"] in ("queued", "running")]
