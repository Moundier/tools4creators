"""Upload a video to YouTube with its thumbnail, subtitles, description and schedule.

  python3 studio.py upload video.mkv --title "GTA 6 VAZOU de novo" --thumb output/davy_alert.png \\
      --description-file desc.txt --tags "gta 6,gta vi" --schedule "2026-10-15 18:00"
  python3 studio.py upload short.mp4 --title "..." --shorts
  python3 studio.py upload video.mkv --dry-run          # show what would be sent, no upload

Every option can also live in a sidecar file video.json next to the video (keys: title,
description, tags, thumb, srt, schedule, privacy, playlist, category); command-line options win.
video.srt next to the video is uploaded automatically as Portuguese subtitles.

One-time setup: see "YouTube upload" in README.md (Google Cloud project + secrets/client_secret.json).
NOTE: until your Google Cloud project passes YouTube's API audit, Google keeps videos uploaded
through the API private (scheduled ones too). Upload, thumbnail and subtitles still work.
"""
import argparse
import datetime as dt
import json
import sys
import tempfile
from pathlib import Path

from ..paths import SECRETS

CLIENT_SECRET = SECRETS / "client_secret.json"


def token_file():
    """The YouTube login of the current channel (secrets/channels/<id>/token.json)."""
    from ..models import channel
    return channel.token_path()
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl"]
GAMING = "20"
THUMB_MAX = 2 * 1024 * 1024  # YouTube thumbnail size limit


FIELDS = ("title", "description", "tags", "thumb", "srt", "schedule", "privacy", "playlist", "category")


def build_opts(video, sidecar=True, shorts=False, **fields):
    """Upload options: defaults < sidecar video.json < fields. Raises ValueError on bad input."""
    video = Path(video)
    opts = {"privacy": "private", "category": GAMING, "tags": []}
    side = video.with_suffix(".json")
    if sidecar and side.is_file() and not side.name.endswith(".words.json"):
        opts.update(json.loads(side.read_text(encoding="utf-8")))
    opts.update({k: v for k, v in fields.items() if k in FIELDS and v is not None})
    if isinstance(opts["tags"], str):
        opts["tags"] = [t.strip() for t in opts["tags"].split(",") if t.strip()]
    if "srt" not in opts and video.with_suffix(".srt").is_file():
        opts["srt"] = str(video.with_suffix(".srt"))
    if shorts and "#shorts" not in opts.get("description", "").lower():
        opts["description"] = (opts.get("description", "") + "\n\n#Shorts").strip()
    if not opts.get("title"):
        raise ValueError("a title is required")
    if len(opts["title"]) > 100:
        raise ValueError(f"title is {len(opts['title'])} characters; YouTube allows 100")
    for key in ("thumb", "srt"):
        if opts.get(key) and not Path(opts[key]).is_file():
            raise ValueError(f"{key} file not found: {opts[key]}")
    video_body(opts)  # validates the schedule
    return opts


def publish_at(text):
    """'2026-10-15 18:00' (local time) -> RFC 3339 UTC, must be in the future."""
    when = dt.datetime.strptime(text, "%Y-%m-%d %H:%M").astimezone()
    if when <= dt.datetime.now().astimezone():
        raise ValueError(f"schedule {text} is in the past")
    return when.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def video_body(opts):
    status = {"privacyStatus": opts["privacy"], "selfDeclaredMadeForKids": False}
    if opts.get("schedule"):
        status.update(privacyStatus="private", publishAt=publish_at(opts["schedule"]))
    return {
        "snippet": {"title": opts["title"], "description": opts.get("description", ""), "tags": opts["tags"],
                    "categoryId": str(opts["category"]), "defaultLanguage": "pt-BR",
                    "defaultAudioLanguage": "pt-BR"},
        "status": status,
    }


def youtube_client():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    if not CLIENT_SECRET.is_file():
        raise RuntimeError(f"missing {CLIENT_SECRET}; see 'YouTube upload' in README.md for the one-time setup")
    token = token_file()
    creds = Credentials.from_authorized_user_file(str(token), SCOPES) if token.is_file() else None
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif not creds or not creds.valid:
        print("opening the browser to log in to your YouTube account...")
        creds = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES).run_local_server(port=0)
    token.parent.mkdir(parents=True, exist_ok=True)
    token.write_text(creds.to_json())
    token.chmod(0o600)
    return build("youtube", "v3", credentials=creds)


def upload_video(yt, path, body, report):
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    media = MediaFileUpload(str(path), chunksize=8 * 1024 * 1024, resumable=True)
    request = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    response, retries = None, 0
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                report(status.progress(), "uploading")
            retries = 0
        except HttpError as e:
            if e.resp.status not in (500, 502, 503, 504) or retries >= 5:
                raise
            retries += 1
            report(None, f"server error {e.resp.status}, retrying ({retries}/5)")
    report(1.0, "uploaded")
    return response["id"]


def thumbnail_file(path):
    """YouTube rejects thumbnails over 2 MB: re-save big PNGs as JPEG."""
    if Path(path).stat().st_size <= THUMB_MAX:
        return str(path)
    from PIL import Image
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    Image.open(path).convert("RGB").save(tmp.name, quality=90)
    return tmp.name


def upload(video, opts, report=None):
    """Upload `video` with `opts` (from build_opts). Returns {"id", "url", "studio"}.

    report(progress 0-1 or None, message): optional progress callback.
    """
    from googleapiclient.http import MediaFileUpload

    report = report or (lambda f, msg: print(msg if f is None else f"{msg} {f * 100:5.1f}%"))
    body = video_body(opts)
    yt = youtube_client()
    video_id = upload_video(yt, video, body, report)
    if opts.get("thumb"):
        yt.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail_file(opts["thumb"]))).execute()
        report(None, "thumbnail set")
    if opts.get("srt"):
        yt.captions().insert(part="snippet", body={"snippet": {"videoId": video_id, "language": "pt-BR",
                                                              "name": "Português", "isDraft": False}},
                             media_body=MediaFileUpload(opts["srt"], mimetype="application/octet-stream")).execute()
        report(None, "subtitles added")
    if opts.get("playlist"):
        yt.playlistItems().insert(part="snippet", body={"snippet": {
            "playlistId": opts["playlist"], "resourceId": {"kind": "youtube#video", "videoId": video_id}}}).execute()
        report(None, "added to playlist")
    return {"id": video_id, "url": "https://youtu.be/" + video_id,
            "studio": "https://studio.youtube.com/video/%s/edit" % video_id,
            "scheduled": body["status"].get("publishAt")}


def main(argv=None):
    p = argparse.ArgumentParser(prog="studio.py upload", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video")
    p.add_argument("--channel", help="channel id whose YouTube login to use (needed when there are several)")
    p.add_argument("--title")
    p.add_argument("--description-file", help="text file with the description")
    p.add_argument("--tags", help="comma-separated tags")
    p.add_argument("--thumb", help="thumbnail image (e.g. from `studio.py thumb`)")
    p.add_argument("--srt", help="subtitles file (default: <video>.srt if it exists)")
    p.add_argument("--schedule", help='publish time, local: "YYYY-MM-DD HH:MM" (video stays private until then)')
    p.add_argument("--privacy", choices=["private", "unlisted", "public"], help="default: private")
    p.add_argument("--playlist", help="playlist ID to add the video to")
    p.add_argument("--category", help="YouTube category id (default 20 = Gaming)")
    p.add_argument("--shorts", action="store_true", help="add #Shorts to the description")
    p.add_argument("--dry-run", action="store_true", help="print what would be uploaded and stop")
    args = p.parse_args(argv)
    if not Path(args.video).is_file():
        p.error(f"video not found: {args.video}")

    fields = {k: getattr(args, k, None) for k in FIELDS}
    if args.description_file:
        fields["description"] = Path(args.description_file).read_text(encoding="utf-8")
    try:
        opts = build_opts(args.video, shorts=args.shorts, **fields)
    except ValueError as e:
        p.error(str(e))
    if args.dry_run:
        print(json.dumps({"video": args.video, "body": video_body(opts), "thumbnail": opts.get("thumb"),
                          "subtitles": opts.get("srt"), "playlist": opts.get("playlist")}, indent=2, ensure_ascii=False))
        return

    from ..models import channel
    ids = [c["id"] for c in channel.all_channels()]
    cid = args.channel or (ids[0] if len(ids) == 1 else None)
    if cid not in ids:
        p.error(f"choose a channel with --channel: {', '.join(ids)}")
    channel.current.set(cid)
    try:
        result = upload(args.video, opts)
    except RuntimeError as e:
        sys.exit(str(e))
    print("uploaded:", result["url"])
    if result["scheduled"]:
        print("scheduled for", opts["schedule"], "(requires an audited API project to go public)")
    print("studio:", result["studio"])
