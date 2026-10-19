"""Post to a Facebook Page (Graph API): the card image as a photo post, the text as its caption.

secrets/facebook.json:
  {"page_id": "...", "page_token": "..."}
page_token: a long-lived *Page* access token (not your user token) from a Meta app with the
pages_manage_posts, pages_read_engagement and pages_show_list permissions (see secrets/README.txt).
"""
import json

import requests

from ..paths import SECRETS

GRAPH = "https://graph.facebook.com/v26.0"


def _keys():
    f = SECRETS / "facebook.json"
    if not f.is_file():
        raise RuntimeError(f"Facebook keys missing: create {f} (see secrets/README.txt)")
    k = json.loads(f.read_text())
    if not k.get("page_id") or not k.get("page_token"):
        raise RuntimeError(f"{f} needs page_id and page_token")
    return k


def post(text, image, dry_run=False):
    """-> {"id", "url"} of the new post."""
    if dry_run:
        print(f"[dry-run] Facebook: POST {GRAPH}/<page_id>/photos ({image})\n{text}\n")
        return {}
    k = _keys()
    with open(image, "rb") as f:
        r = requests.post(f"{GRAPH}/{k['page_id']}/photos", files={"source": f},
                          data={"caption": text, "access_token": k["page_token"]}, timeout=60)
    if r.status_code >= 300:
        raise RuntimeError(f"Facebook post failed ({r.status_code}): {r.text[:400]}")
    data = r.json()
    post_id = data.get("post_id") or data["id"]
    return {"id": post_id, "url": f"https://www.facebook.com/{post_id}"}
