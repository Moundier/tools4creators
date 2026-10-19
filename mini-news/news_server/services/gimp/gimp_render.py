"""Entry point that runs INSIDE GIMP 3 (python-fu-eval batch interpreter). Do not run with plain python.

runner.py launches GIMP like:
    gimp-console -i --batch-interpreter=python-fu-eval \
        -b "exec(open('gimp_render.py').read(), {'JOB_PATH': '/tmp/job.json', 'ROOT': '/path/to/gimp'})" --quit

The job file is {"jobs": [...]}. Two kinds of job:
  {"type": "render", "width", "height", "base": "#hex", "ops": [...], "out": base path}
      -> <out>.xcf (layered, editable text) + <out>.jpg
  {"type": "export", "xcf": path, "out": base path}
      -> <out>.jpg from an .xcf you edited in GIMP
Each job prints JOB_OK <out> or JOB_FAIL <out> (after a traceback), as soon as it's done.

Code layout:
  gimp_helpers.py  layers, fills, gradients, shadows, fades
  gimp_ops.py      shape / ellipse / gradient / stripes / image ops
  gimp_text.py     the auto-fitting text op
  gimp_render.py   op registry + job loop (this file)
"""
import json
import sys
import traceback

sys.path.insert(0, ROOT)  # noqa: F821 - ROOT (this folder) is injected by runner.py (exec has no __file__)

import gi
gi.require_version("Gimp", "3.0")
from gi.repository import Gimp, Gio

from gimp_helpers import fill_selection, new_layer
from gimp_ops import op_ellipse, op_gradient, op_image, op_shape, op_stripes
from gimp_text import op_text

OPS = {"shape": op_shape, "ellipse": op_ellipse, "gradient": op_gradient, "stripes": op_stripes,
       "image": op_image, "text": op_text}


def save_jpg(img, out):
    flat = img.duplicate()
    flat.flatten()
    Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, flat, Gio.File.new_for_path(out + ".jpg"), None)
    flat.delete()


def render(job):
    img = Gimp.Image.new(job["width"], job["height"], Gimp.ImageBaseType.RGB)
    Gimp.context_push()
    Gimp.context_set_antialias(True)
    try:
        base = new_layer(img, "Base")
        Gimp.Selection.all(img)
        fill_selection(img, base, job.get("base", "#111111"))
        for op in job["ops"]:
            OPS[op["op"]](img, op, job)
        Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, img, Gio.File.new_for_path(job["out"] + ".xcf"), None)
        save_jpg(img, job["out"])
    finally:
        Gimp.context_pop()
        img.delete()


def export(job):
    img = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, Gio.File.new_for_path(job["xcf"]))
    try:
        save_jpg(img, job["out"])
    finally:
        img.delete()


with open(JOB_PATH) as fh:  # noqa: F821 - JOB_PATH is injected by runner.py
    for _job in json.load(fh)["jobs"]:
        try:
            (export if _job.get("type") == "export" else render)(_job)
            print("JOB_OK", _job["out"], flush=True)
        except Exception:
            traceback.print_exc()
            print("JOB_FAIL", _job["out"], flush=True)
