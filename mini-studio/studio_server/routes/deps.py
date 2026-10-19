"""Helpers shared by the route modules."""
from fastapi import HTTPException

from ..models import project as projects


def project_or_404(pid):
    try:
        p = projects.load(pid)
    except KeyError:
        p = None
    if not p:
        raise HTTPException(404, "project not found")
    return p


def bad_request(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except (ValueError, KeyError) as e:
        raise HTTPException(400, str(e))


def require_youtube(dry_run):
    """Fail fast (instead of in the job) when a real upload can't log in."""
    from ..services.youtube_upload import CLIENT_SECRET
    if not dry_run and not CLIENT_SECRET.is_file():
        raise HTTPException(400, f"YouTube is not set up: save your Google OAuth file as {CLIENT_SECRET} "
                                 "(see README, 'YouTube upload'), or use a dry run")
