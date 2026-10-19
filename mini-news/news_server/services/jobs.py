"""Background jobs for the slow GIMP renders, so the web app can show progress ("GIMP: 7/20")."""
import threading
import time
import traceback
import uuid

JOBS = {}
_lock = threading.Lock()


def start(fn, *args):
    """Run fn(job, *args) in a thread; fn updates job["done"] / job["total"] / job["items"]. Returns the job id."""
    job_id = uuid.uuid4().hex[:10]
    job = {"id": job_id, "status": "running", "done": 0, "total": 0, "items": {}, "error": None, "result": None,
           "started": time.time()}
    with _lock:
        JOBS[job_id] = job
        for old in [k for k, j in JOBS.items() if time.time() - j["started"] > 3600]:   # forget hour-old jobs
            JOBS.pop(old, None)

    def run():
        try:
            job["result"] = fn(job, *args)
            job["status"] = "done"
        except Exception as e:  # shown to the user in the page
            traceback.print_exc()
            job["error"], job["status"] = str(e), "error"

    threading.Thread(target=run, daemon=True).start()
    return job_id


def get(job_id):
    if job_id not in JOBS:
        raise KeyError(f"no job {job_id!r}")
    return JOBS[job_id]
