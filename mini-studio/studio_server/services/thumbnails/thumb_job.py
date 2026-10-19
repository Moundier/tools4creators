"""Turn a template + the user's text/images into a render job (plain data for gimp_render.py)."""
import random
import re
from pathlib import Path

from ..cutout import face_info
from .templates import TEMPLATES
from .templates_common import darker, theme_for


def substitute(obj, values, theme):
    """Fill {placeholders} in text and $theme colors anywhere in the ops."""
    if isinstance(obj, dict):
        return {k: substitute(v, values, theme) for k, v in obj.items()}
    if isinstance(obj, list):
        return [substitute(v, values, theme) for v in obj]
    if isinstance(obj, str):
        if obj.startswith("$") and obj[1:] in theme:
            return theme[obj[1:]]
        return re.sub(r"\{(\w+)\}", lambda m: values.get(m.group(1), ""), obj)
    return obj


def resolve_darker(ops):
    """Ribbon styles like {"box": darker_than(0)} -> darker hex of that line's (already themed) value."""
    for op in ops:
        styles = op.get("styles", [])
        for st in styles:
            for key, v in st.items():
                if isinstance(v, dict) and "darker_than" in v:
                    st[key] = darker(styles[v["darker_than"]][key], v["k"])
    return ops


def title_lines(title):
    """'INSIDE / CAPCOM' -> ('INSIDE', 'CAPCOM'). Without '/': short titles put the last word on line 2,
    long ones are cut into two halves of similar length."""
    if "/" in title:
        parts = [p.strip() for p in title.split("/")]
        return parts[0], " ".join(parts[1:])
    words = title.split()
    if len(words) < 2:
        return title, ""
    if len(title) <= 16:
        return " ".join(words[:-1]), words[-1]
    cut = min(range(1, len(words)), key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))))
    return " ".join(words[:cut]), " ".join(words[cut:])


def too_long(name, title):
    """Characters over the template's recommended maximum (0 = fine)."""
    limit = TEMPLATES[name].get("max_chars")
    n = len(" ".join(title.replace("/", " ").split()))  # ignore "/" and extra spaces
    return max(0, n - limit) if limit else 0


def build_job(name, args, out_base):
    tpl = TEMPLATES[name]
    values = dict(tpl["defaults"])
    values["title"] = args.title
    values["line1"], values["line2"] = title_lines(args.title)
    if args.subtitle is not None:
        values["subtitle"] = args.subtitle
    theme = theme_for(args.color or values.get("color", "purple"))
    images = {}
    for key in ("art", "art2"):
        if getattr(args, key):
            images[key] = str(Path(getattr(args, key)).resolve())
    if not args.no_logo and Path(args.logo).is_file():
        images["logo"] = str(Path(args.logo).resolve())
    person = str(Path(args.person).resolve())
    ops = [op for op in tpl["ops"] if not op.get("if_value") or values.get(op["if_value"], "").strip()]
    return {"ops": resolve_darker(substitute(ops, values, theme)), "base": tpl.get("base", "#111111"),
            "bg": str(Path(args.bg).resolve()), "person": person, "person_face": face_info(person),
            "images": images, "out": str(out_base),
            "seed": getattr(args, "seed", None) or random.randrange(1, 1 << 30),  # new random layouts each render
            "magazines": [{"title": m["title"], "path": str(Path(m["path"]).resolve())}
                          for m in getattr(args, "magazines", None) or [] if Path(m["path"]).is_file()]}
