"""The 20 news image templates, drawn by GIMP (editable .xcf + .jpg). Each module has NAME, CATEGORY,
NEEDS (data it requires) and ops(draft, ctx) -> GIMP op list. How they look comes from the draft's style."""
import re
import shutil

from ...paths import CARDS, PHOTOS
from ..gimp import runner
from . import (alert, big_number, breaking, explainer, headline, live, newspaper, numbers, opinion, photo,
               photo_frame, photo_full, photo_split, points, question, quote, quote_photo, timeline, tv, versus)
from .base import Ctx

TEMPLATES = {m.__name__.rsplit(".", 1)[-1]: m for m in (
    breaking, headline, live, alert, newspaper, tv,                 # Título
    photo, photo_full, photo_split, photo_frame,                    # Foto
    numbers, big_number, versus, points, explainer, timeline,       # Dados
    quote, quote_photo, opinion, question)}                         # Voz
CATEGORIES = ["Título", "Foto", "Dados", "Voz"]
NEED_LABELS = {"photo": "foto", "quote": "citação", "numbers": "números", "numbers2": "2 números",
               "points": "pontos-chave", "take": "sua opinião (sem a [sugestão])", "question": "pergunta"}

SAMPLE = {   # for the style editor's previews when there's no draft open
    "id": "_sample", "headline": "Senado aprova fim da escala 6x1; jornada vai cair para 40 horas", "kicker": "TRABALHO",
    "subhead": "Escala 5x2 e 42h semanais 60 dias após a promulgação; 40h ao fim de 14 meses",
    "source_name": "Agência Brasil",
    "quote": {"text": "Um dia para resolver mil coisas e a gente fica perdida. Ainda mais quando a gente é mãe.",
              "author": "Adrielle Barbosa de Aquino", "role": "garçonete, trabalha na escala 6x1"},
    "numbers": [{"value": "42h", "label": "jornada semanal após 60 dias"}, {"value": "40h", "label": "ao fim de 14 meses"},
                {"value": "73%", "label": "apoiam o fim da 6x1"}],
    "points": ["Empresas terão 60 dias para dar duas folgas por semana", "Jornada cai de 44 para 42 horas no início",
               "Limite de 40 horas vale 12 meses depois", "Pequenas empresas podem ter regras próprias"],
    "question": "Você trabalha ou já trabalhou na escala 6x1?",
    "take": "É uma mudança histórica para quem só tinha o domingo para viver.",
}


def _has(d, need):
    if need == "photo":
        return (PHOTOS / f"{d['id']}.jpg").is_file()
    if need == "quote":
        return bool((d.get("quote") or {}).get("text", "").strip())
    if need == "numbers":
        return bool(d.get("numbers"))
    if need == "numbers2":
        return len(d.get("numbers") or []) >= 2
    if need == "points":
        return len(d.get("points") or []) >= 2
    if need == "take":
        take = (d.get("take") or "").strip()
        return bool(take) and not re.search(r"\[[^\]]+\]", take)
    if need == "question":
        return bool((d.get("question") or "").strip())
    return True


def available(d):
    """Templates this draft has the data for (no quote -> no Quote card, no photo -> no Photo...)."""
    return [t for t, m in TEMPLATES.items() if all(_has(d, n) for n in m.NEEDS)]


def missing(d, template):
    return [NEED_LABELS[n] for n in TEMPLATES[template].NEEDS if not _has(d, n)]


def listing():
    return [{"id": t, "name": m.NAME, "category": m.CATEGORY, "needs": [NEED_LABELS[n] for n in m.NEEDS]}
            for t, m in TEMPLATES.items()]


def card_path(d, ext="jpg"):
    """The image that gets published (and its editable .xcf)."""
    return CARDS / f"{d['id']}.{ext}"


def preview_path(d, template, ext="jpg"):
    return CARDS / f"{d['id']}-{template}.{ext}"


def job(d, template, out_base, style=None):
    """GIMP job for one template. Uses the draft's own style copy, or the saved style `style` when given."""
    c = Ctx(style or d.get("style") or "default", template, None if style else d.get("style_data"))
    return {"type": "render", "width": c.W, "height": c.H, "base": c.c["background"][-1],
            "ops": TEMPLATES[template].ops(d, c), "out": str(out_base)}


def render_many(d, which=None, style=None, on_done=None, prefix=None):
    """Draw several templates in one GIMP session -> {template: jpg path or None}. on_done(template, ok)."""
    which = [t for t in (which or available(d)) if t in available(d)]
    CARDS.mkdir(parents=True, exist_ok=True)
    outs = {t: CARDS / f"{prefix or d['id']}-{t}" for t in which}
    back = {str(o): t for t, o in outs.items()}
    res = runner.run_jobs([job(d, t, o, style) for t, o in outs.items()],
                          (lambda out, ok: on_done(back[out], ok)) if on_done else None)
    return {t: o.with_suffix(".jpg") if res.get(str(o)) else None for t, o in outs.items()}


def render(d, template=None, style=None):
    """Draw the draft's image (its template + style) -> <id>.jpg + <id>.xcf. Returns the jpg path."""
    template = template or d.get("template") or "breaking"
    if template not in available(d):
        template = "breaking"
    out = CARDS / d["id"]
    CARDS.mkdir(parents=True, exist_ok=True)
    if not runner.run_jobs([job(d, template, out, style)]).get(str(out)):
        raise RuntimeError(f"GIMP couldn't draw the {template!r} template")
    return out.with_suffix(".jpg")


def use_preview(d, template):
    """Make an already rendered preview the draft's image (no new render). False if there's no preview."""
    src_jpg, src_xcf = preview_path(d, template), preview_path(d, template, "xcf")
    if not (src_jpg.is_file() and src_xcf.is_file()):
        return False
    shutil.copy(src_jpg, card_path(d))
    shutil.copy(src_xcf, card_path(d, "xcf"))
    return True


def export_xcf(d):
    """Your edited <id>.xcf -> <id>.jpg (the image that gets published)."""
    out = CARDS / d["id"]
    if not runner.run_jobs([{"type": "export", "xcf": str(card_path(d, "xcf")), "out": str(out)}]).get(str(out)):
        raise RuntimeError("GIMP couldn't export the .xcf")
    return out.with_suffix(".jpg")


def sample():
    """The sample story, with a photo if any draft has one (photo templates need it)."""
    d = dict(SAMPLE)
    target = PHOTOS / "_sample.jpg"
    if not target.is_file():
        src = next(iter(sorted(PHOTOS.glob("2*.jpg"))), None) if PHOTOS.is_dir() else None
        if src:
            shutil.copy(src, target)
    return d


def style_previews(style_id, d=None, which=None, on_done=None):
    """Templates drawn with a style, on a draft (or the sample story) -> {template: jpg path}."""
    d = d or sample()
    return {t: p for t, p in render_many(d, which, style_id, on_done, prefix=f"_style-{style_id}-{d['id']}").items()
            if p}
