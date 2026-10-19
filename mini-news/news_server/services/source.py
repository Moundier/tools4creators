"""A news link -> its title, site and main text (the menus, ads and comments are left out)."""
from urllib.parse import urlparse

import requests
import trafilatura

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) mini-news/1.0", "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"}
MAX_CHARS = 30000   # a long article is plenty; the rest is usually related links and footers


def is_url(text):
    return urlparse(text.strip()).scheme in ("http", "https")


def fetch(url):
    """{url, title, site, date, image, text}. Raises RuntimeError when the page can't be read."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"could not open {url}: {e}") from e
    text = trafilatura.extract(r.text, url=url, include_comments=False, include_tables=False, favor_precision=True)
    if not text or len(text) < 200:
        raise RuntimeError(f"no article text found at {url} (paywall or a page built by JavaScript?)")
    meta = trafilatura.extract_metadata(r.text, default_url=url)
    site = (meta.sitename if meta else None) or urlparse(url).netloc.removeprefix("www.")
    return {"url": url, "title": (meta.title if meta else None) or "", "site": site,
            "date": (meta.date if meta else None) or "", "image": (meta.image if meta else None) or "",
            "text": text[:MAX_CHARS]}


def download_image(url, path):
    """Save the article's main photo (og:image) as a JPEG; False when there's none or it can't be read."""
    from io import BytesIO

    from PIL import Image

    if not url:
        return False
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGB")
    except (requests.RequestException, OSError):
        return False
    if min(img.size) < 300:   # an icon or logo, not a news photo
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, quality=92)
    return True
