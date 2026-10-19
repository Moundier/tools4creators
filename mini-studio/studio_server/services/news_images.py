"""Find one picture per news headline with Claude Code (headless `claude -p` with web search), for the
collage magazines. Downloads are checked with PIL and cached per headline in the project's news/ folder."""
import hashlib
import io
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path

SCHEMA = {
    "type": "object",
    "properties": {"items": {"type": "array", "items": {
        "type": "object",
        "properties": {"news": {"type": "string"}, "headline": {"type": "string"},
                       "urls": {"type": "array", "items": {"type": "string"}}},
        "required": ["news", "headline", "urls"]}}},
    "required": ["items"],
}

PROMPT = """For each news topic below, find pictures that illustrate it, for a YouTube thumbnail collage.
Search the web for recent news articles about each topic and give up to 5 DIRECT image URLs per topic
(the file itself: .jpg/.png/.webp, e.g. an article's og:image), landscape, at least 800 px wide, no logos
alone, no stock watermarks. You can use curl to read an article's HTML and pick its og:image.
Also write a magazine-cover headline for each topic, in Brazilian Portuguese, from what the news says:
uppercase, a small line and a big line separated by " / " (like "DISCO POLÊMICO DE / GTA VI"), the big
line 1-2 words, under 30 characters in total.
Return the topics in the same order, with the topic text exactly as given.

Topics:
{topics}"""

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def slug(text):
    return hashlib.sha1(text.strip().lower().encode()).hexdigest()[:12]


def ask_claude(topics, timeout=900):
    """{topic: {"urls": [image urls], "headline": "SMALL / BIG"}} from one headless Claude Code run."""
    if not shutil.which("claude"):
        raise RuntimeError("Claude Code (`claude`) isn't installed or not on PATH")
    cmd = ["claude", "-p", PROMPT.format(topics="\n".join(f"- {' '.join(t.replace('/', ' ').split())}" for t in topics)),
           "--output-format", "json", "--json-schema", json.dumps(SCHEMA),
           "--allowedTools", "WebSearch", "WebFetch", "Bash(curl:*)"]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if out.returncode != 0:
        raise RuntimeError("Claude Code failed: " + (out.stderr or out.stdout).strip()[-400:])
    res = json.loads(out.stdout)
    data = res.get("structured_output")
    if data is None:  # older CLI: the JSON is in the text result
        text = res.get("result", "")
        data = json.loads(text[text.find("{"):text.rfind("}") + 1])
    items = data.get("items", [])
    found = {i["news"].strip(): i for i in items}
    # match by position too, in case Claude reworded a topic
    return {t: found.get(t.strip()) or (items[k] if k < len(items) else {"urls": [], "headline": ""})
            for k, t in enumerate(topics)}


def download(url, out, min_side=300):
    """Save `url` as JPEG at `out` if it is a real image big enough. Returns True on success."""
    from PIL import Image

    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "image/*,*/*"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read(25 * 1024 * 1024)
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception:
        return False
    if min(im.size) < min_side:
        return False
    im.convert("RGB").save(out, "JPEG", quality=90)
    return True


def find_images(topics, folder, report=None):
    """[{"text", "file", "title"}] for each topic: file = picture name in `folder` (None when nothing usable
    was found), title = the cover headline Claude wrote. Topics with both cached aren't searched again."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    cache_file = folder / "headlines.json"
    headlines = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.is_file() else {}
    topics = [t.strip() for t in topics if t.strip()]
    pic = lambda t: folder / f"{slug(t)}.jpg"
    missing = [t for t in topics if not pic(t).is_file() or slug(t) not in headlines]
    if missing:
        if report:
            report(None, f"Claude Code is searching images for {len(missing)} news")
        found = ask_claude(missing)
        for t in missing:
            if report:
                report(None, f"downloading: {t}")
            headlines[slug(t)] = found[t].get("headline", "").strip()
            if not pic(t).is_file():
                for u in found[t].get("urls") or []:
                    if download(u, pic(t)):
                        break
        cache_file.write_text(json.dumps(headlines, ensure_ascii=False, indent=1), encoding="utf-8")
    return [{"text": t, "file": pic(t).name if pic(t).is_file() else None, "title": headlines.get(slug(t), "")}
            for t in topics]
