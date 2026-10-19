"""Remove the background from a person photo with rembg (AI model: birefnet-portrait).

  python3 studio.py cutout photo.jpg                # -> studio_server/assets/cutouts/photo_<hash>.png
  python3 studio.py cutout photo.jpg -o me.png
  python3 studio.py cutout photo.jpg --model u2net_human_seg   # older, faster model

`studio.py thumb` calls ensure_cutout() automatically when --person has no transparency.
The models download into studio_server/ai_models/ on first use (rembg ~1 GB, face detector 230 KB).
"""
import argparse
import hashlib
import json
import os
import urllib.request
from pathlib import Path

from PIL import Image

from ..paths import AI_MODELS, ASSETS

MODEL = "birefnet-portrait"  # best rembg model for people: clean hair edges, ignores busy backgrounds
CACHE = ASSETS / "cutouts"
FACE_CACHE = CACHE / "faces"
YUNET = AI_MODELS / "yunet" / "face_detection_yunet_2023mar.onnx"   # OpenCV's face detector
YUNET_URL = ("https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/"
             "face_detection_yunet_2023mar.onnx")
YUNET_SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"


def has_transparency(path):
    """True if the image already has see-through pixels (an existing cutout)."""
    img = Image.open(path)
    if "A" not in img.getbands() and "transparency" not in img.info:
        return False
    return img.convert("RGBA").getchannel("A").getextrema()[0] < 250


def cached_path(src, model=MODEL):
    digest = hashlib.sha1(Path(src).read_bytes() + model.encode()).hexdigest()[:10]
    return CACHE / f"{Path(src).stem}_{digest}.png"


def clean_mask(img):
    """Solid person, soft edges, no floating bits of background (keeps the biggest region: the person)."""
    import numpy as np
    from scipy import ndimage

    alpha = np.asarray(img.getchannel("A")).astype(np.float32)
    # the model leaves the person ~97% opaque and a faint haze around: make solid solid, keep the soft edge
    alpha = np.clip((alpha - 10) * 255 / (235 - 10), 0, 255)
    labels, count = ndimage.label(alpha > 128)
    if count > 1:
        sizes = ndimage.sum(np.ones_like(alpha), labels, range(1, count + 1))
        keep = ndimage.binary_dilation(labels == int(np.argmax(sizes)) + 1, iterations=6)  # + its soft edge
        alpha = np.where(keep, alpha, 0)
    out = img.copy()
    out.putalpha(Image.fromarray(alpha.astype(np.uint8)))
    return out


def _face_key(path):
    return FACE_CACHE / (hashlib.sha1(Path(path).read_bytes()).hexdigest()[:16] + ".json")


def detect_face(path):
    """Biggest face in the image as {"box": [x, y, w, h], "size": [w, h]} (pixels), or None."""
    import cv2
    import numpy as np

    if not YUNET.is_file():
        data = urllib.request.urlopen(YUNET_URL, timeout=60).read()
        if hashlib.sha256(data).hexdigest() != YUNET_SHA256:
            raise RuntimeError("face model download checksum mismatch")
        YUNET.parent.mkdir(parents=True, exist_ok=True)
        YUNET.write_bytes(data)
    img = Image.open(path).convert("RGBA")
    flat = Image.new("RGBA", img.size, (128, 128, 128, 255))  # cutouts: transparent -> gray
    flat.alpha_composite(img)
    bgr = cv2.cvtColor(np.asarray(flat.convert("RGB")), cv2.COLOR_RGB2BGR)
    h, w = bgr.shape[:2]
    scale = min(1.0, 1024 / max(w, h))  # YuNet is fast on <= 1024 px
    if scale < 1:
        bgr = cv2.resize(bgr, (round(w * scale), round(h * scale)))
    detector = cv2.FaceDetectorYN.create(str(YUNET), "", (bgr.shape[1], bgr.shape[0]), 0.7)
    _, faces = detector.detect(bgr)
    if faces is None or not len(faces):
        return None
    x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])[:4] / scale
    return {"box": [round(float(v)) for v in (x, y, fw, fh)], "size": [w, h]}


def face_info(path):
    """Cached detect_face(): None if no face was found."""
    key = _face_key(path)
    if not key.is_file():
        FACE_CACHE.mkdir(parents=True, exist_ok=True)
        key.write_text(json.dumps(detect_face(path)))
    return json.loads(key.read_text())


def remove_background(src, dst, model=MODEL):
    """Run rembg on src and save a transparent PNG to dst."""
    os.environ.setdefault("U2NET_HOME", str(AI_MODELS / "rembg"))  # weights go in ai_models/rembg/models/<name>/
    from rembg import new_session, remove
    photo = Image.open(src).convert("RGB")
    out = clean_mask(remove(photo, session=new_session(model)))  # soft alpha: no binary post-processing
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    out.save(dst)


def ensure_cutout(src, force=False):
    """Return a transparent version of src: src itself if already cut out, else a cached rembg result."""
    if not force and has_transparency(src):
        return Path(src)
    dst = cached_path(src)
    if not dst.is_file():
        print(f"removing background from {Path(src).name} ({MODEL})...")
        remove_background(src, dst)
    return dst


def main(argv=None):
    p = argparse.ArgumentParser(prog="studio.py cutout", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("photo", help="photo of a person (any background)")
    p.add_argument("-o", "--out", help="output PNG (default: studio_server/assets/cutouts/<name>_<hash>.png)")
    p.add_argument("--model", default=MODEL, help=f"rembg model (default {MODEL})")
    p.add_argument("--face", action="store_true", help="only find the face (prints its box)")
    args = p.parse_args(argv)
    if args.face:
        print(json.dumps(face_info(args.photo)))
    elif args.out:
        remove_background(args.photo, args.out, args.model)
        print("wrote", args.out)
    else:
        print("wrote", ensure_cutout(args.photo, force=True))
