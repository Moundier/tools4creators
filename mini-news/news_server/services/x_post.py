"""Post to X (API v2): upload the card image, then the post with the image attached.

secrets/x.json (from developer.x.com: your app, with "Read and write" permission, "Keys and tokens" tab):
  {"api_key": "...", "api_secret": "...", "access_token": "...", "access_token_secret": "..."}
OAuth 1.0a user context: these keys don't expire, so there's no login step.
"""
import json

from requests_oauthlib import OAuth1Session

from ..paths import SECRETS

UPLOAD = "https://api.x.com/2/media/upload"
POST = "https://api.x.com/2/tweets"
KEYS = ("api_key", "api_secret", "access_token", "access_token_secret")


def session():
    f = SECRETS / "x.json"
    if not f.is_file():
        raise RuntimeError(f"X keys missing: create {f} (see secrets/README.txt)")
    k = json.loads(f.read_text())
    missing = [n for n in KEYS if not k.get(n)]
    if missing:
        raise RuntimeError(f"{f} is missing {', '.join(missing)}")
    return OAuth1Session(k["api_key"], k["api_secret"], k["access_token"], k["access_token_secret"])


def _ok(r, what):
    if r.status_code >= 300:
        raise RuntimeError(f"X {what} failed ({r.status_code}): {r.text[:400]}")
    return r.json()


def post(text, image=None, dry_run=False):
    """-> {"id", "url"} of the new post."""
    if dry_run:
        if image:
            print(f"[dry-run] X: POST {UPLOAD} (media_category=tweet_image, {image})")
        print(f"[dry-run] X: POST {POST}\n{text}\n")
        return {}
    s = session()
    body = {"text": text}
    if image:
        with open(image, "rb") as f:
            media = _ok(s.post(UPLOAD, files={"media": f}, data={"media_category": "tweet_image"}, timeout=60),
                        "image upload")
        body["media"] = {"media_ids": [media["data"]["id"]]}
    data = _ok(s.post(POST, json=body, timeout=30), "post")["data"]
    return {"id": data["id"], "url": f"https://x.com/i/web/status/{data['id']}"}
