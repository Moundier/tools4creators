"""`python3 news.py <command>`: the web app and the commands behind it."""
import argparse
import json
import sys
import threading
import webbrowser

USAGE = """python3 news.py [--port N] [--no-browser]     web app
python3 news.py draft <link or "topic"> [--take "your opinion"] [--template breaking|photo|quote|numbers] [--style <id>]
python3 news.py render <id> [--template ...]     redraw the image with GIMP (all 20 templates: --all)
python3 news.py gimp <id>                         open the image's .xcf in GIMP to fix it by hand
python3 news.py gimp-apply <id>                   use the .xcf you saved in GIMP as the image to publish
python3 news.py list
python3 news.py show <id>
python3 news.py edit <id> [--headline ..] [--x-text ..] [--facebook-text ..] [--take ..] [--kicker ..] [--subhead ..]
python3 news.py delete <id>
python3 news.py approve <id>
python3 news.py publish <id> [--dry-run] [--only x|facebook]"""


def serve(argv):
    p = argparse.ArgumentParser(prog="news.py", usage=USAGE)
    p.add_argument("--port", type=int, default=8010)
    p.add_argument("--no-browser", action="store_true")
    args = p.parse_args(argv)
    import uvicorn

    url = f"http://127.0.0.1:{args.port}"
    if not args.no_browser:
        threading.Timer(1.5, webbrowser.open, [url]).start()
    print(f"mini-news: {url}  (Ctrl+C to stop)")
    uvicorn.run("news_server.app:app", host="127.0.0.1", port=args.port, log_level="warning")


def show(d):
    from .services import writer

    print(f"{d['id']}  [{d['status']}]  {d['headline']}")
    print(f"\n--- X ({writer.x_length(d)}/{writer.X_LIMIT}) ---\n{writer.x_post_text(d)}")
    print(f"\n--- Facebook ---\n{writer.facebook_post_text(d)}")
    from .services import drafts, templates

    print(f"\nimage ({d.get('template')}): {templates.card_path(d)}")
    for w in drafts.warnings(d):
        print(f"\n! {w}")
    for name, p in d.get("published", {}).items():
        print(f"\npublished on {name}: {p.get('url')}")
    for name, e in (d.get("errors") or {}).items():
        print(f"\nerror on {name}: {e}")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0] if argv and not argv[0].startswith("-") else None
    if cmd is None:
        return serve(argv)
    from .services import drafts
    from .services import templates
    from .services.templates import TEMPLATES, available, render as templates_render, render_many

    p = argparse.ArgumentParser(prog=f"news.py {cmd}", usage=USAGE)
    try:
        if cmd == "draft":
            p.add_argument("text")
            p.add_argument("--take", default="", help="your opinion on the news, used in the post")
            p.add_argument("--template", choices=list(TEMPLATES), help="image template (default: Claude's pick)")
            p.add_argument("--style", default="default", help="image style (styles/<id>.json; default: default)")
            a = p.parse_args(argv[1:])
            d = drafts.create(a.text, a.take, a.template, print, a.style)
            print()
            show(d)
            print(f"\nnext: python3 news.py approve {d['id']}   (or edit it in the web app: python3 news.py)")
        elif cmd == "render":
            p.add_argument("id")
            p.add_argument("--template", choices=list(TEMPLATES))
            p.add_argument("--all", action="store_true", help="draw every template this draft can use")
            a = p.parse_args(argv[1:])
            d = drafts.load(a.id)
            if a.all:
                n = len(available(d))
                print(f"GIMP is drawing {n} templates...")
                done = []
                for t, path in render_many(d, on_done=lambda t, ok: (done.append(t), print(
                        f"  {len(done)}/{n} {t:12} {'ok' if ok else 'FAILED'}"))).items():
                    print(f"{t:12} {path}")
            else:
                d = drafts.update(a.id, {"template": a.template}, force=True) if a.template else d
                print(templates_render(d) if not a.template else templates.card_path(d))
        elif cmd == "gimp":
            p.add_argument("id")
            d = drafts.gimp_open(p.parse_args(argv[1:]).id)
            print(f"opening {templates.card_path(d, 'xcf')} in GIMP. Fix it, save it (Ctrl+S), then:\n"
                  f"  python3 news.py gimp-apply {d['id']}")
        elif cmd == "gimp-apply":
            p.add_argument("id")
            d = drafts.gimp_apply(p.parse_args(argv[1:]).id)
            print(f"{templates.card_path(d)} updated from your .xcf")
        elif cmd == "list":
            for d in drafts.all_drafts():
                print(f"{d['id']}  {d['status']:9}  {d['headline']}")
        elif cmd == "show":
            p.add_argument("id")
            show(drafts.load(p.parse_args(argv[1:]).id))
        elif cmd == "edit":
            p.add_argument("id")
            for f in ("headline", "x_text", "facebook_text", "take", "kicker", "subhead", "source_name", "source_url"):
                p.add_argument("--" + f.replace("_", "-"), dest=f)
            a = vars(p.parse_args(argv[1:]))
            fields = {k: v for k, v in a.items() if k != "id" and v is not None}
            if not fields:
                sys.exit("nothing to change: pass at least one --field (or edit it in the web app)")
            show(drafts.update(a["id"], fields))
        elif cmd == "delete":
            p.add_argument("id")
            a = p.parse_args(argv[1:])
            drafts.delete(a.id)
            print(f"{a.id} deleted")
        elif cmd == "approve":
            p.add_argument("id")
            d = drafts.approve(p.parse_args(argv[1:]).id)
            print(f"{d['id']} approved. next: python3 news.py publish {d['id']}")
        elif cmd == "publish":
            p.add_argument("id")
            p.add_argument("--dry-run", action="store_true", help="show what would be sent, send nothing")
            p.add_argument("--only", choices=["x", "facebook"])
            a = p.parse_args(argv[1:])
            r = drafts.publish(a.id, a.only, a.dry_run)
            if a.dry_run:
                print(json.dumps(r, ensure_ascii=False))
            else:
                show(r)
        else:
            sys.exit(f"unknown command {cmd!r}\n\n{USAGE}")
    except (KeyError, ValueError, RuntimeError) as e:
        sys.exit(f"error: {e}")
