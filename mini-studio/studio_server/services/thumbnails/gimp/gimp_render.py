"""Entry point that runs INSIDE GIMP 3 (python-fu-eval batch interpreter). Do not run with plain python.

gimp_runner.py launches GIMP like:
    gimp-console -i --batch-interpreter=python-fu-eval \
        -b "exec(open('gimp_render.py').read(), {'JOB_PATH': '/tmp/job.json', 'ROOT': '/path/to/project'})" --quit

The job file is {"jobs": [{"ops": [...], "bg": path, "person": path, "images": {key: path},
"base": "#hex", "out": base_path}, ...]} with all {title}/$color/... placeholders already substituted.
Each job produces <out>.xcf (layered, editable) and <out>.png (1280x720).

Code layout:
  gimp_helpers.py  layers, fills, outlines, shadows, fades
  gimp_ops.py      background / shapes / person / image ops
  gimp_text.py     text and ribbons ops
  gimp_render.py   op registry + render loop (this file)
"""
import json
import os
import sys
import traceback

sys.path.insert(0, ROOT)  # noqa: F821 - ROOT (this folder) is injected by gimp_runner.py (exec has no __file__)

import gi
gi.require_version("Gimp", "3.0")
from gi.repository import Gimp, Gio

from gimp_helpers import W, H, fill_selection, new_layer
from gimp_ops import (op_arrow, op_background, op_ellipse, op_frame, op_gradient, op_image, op_matrix,
                      op_person, op_poly, op_rect)
from gimp_magazines import op_magazines
from gimp_text import op_ribbons, op_text


OPS = {"background": op_background, "rect": op_rect, "poly": op_poly, "ellipse": op_ellipse,
       "gradient": op_gradient, "arrow": op_arrow, "person": op_person, "text": op_text,
       "image": op_image, "ribbons": op_ribbons, "matrix": op_matrix, "frame": op_frame,
       "magazines": op_magazines}


def wanted(op, job):
    """Ops can depend on an optional image: if_image / unless_image."""
    has = lambda k: bool(job.get("images", {}).get(k)) and os.path.isfile(job["images"][k])
    if "if_image" in op and not has(op["if_image"]):
        return False
    if "unless_image" in op and has(op["unless_image"]):
        return False
    return True


# ---------------------------------------------------------------- main

def render(job):
    img = Gimp.Image.new(W, H, Gimp.ImageBaseType.RGB)
    Gimp.context_push()
    Gimp.context_set_antialias(True)
    try:
        base = new_layer(img, "Base")
        Gimp.Selection.all(img)
        fill_selection(img, base, job.get("base", "#111111"))
        for op in job["ops"]:
            if wanted(op, job):
                OPS[op["op"]](img, op, job)
        Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, img, Gio.File.new_for_path(job["out"] + ".xcf"), None)
        flat = img.duplicate()
        flat.flatten()
        Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, flat, Gio.File.new_for_path(job["out"] + ".png"), None)
        flat.delete()
        print("THUMB_OK", job["out"] + ".png")
    except Exception:
        traceback.print_exc()
        print("THUMB_FAIL", job["out"])
    finally:
        Gimp.context_pop()
        img.delete()


with open(JOB_PATH) as fh:  # noqa: F821 - JOB_PATH is injected by gimp_runner.py
    for _job in json.load(fh)["jobs"]:
        render(_job)
