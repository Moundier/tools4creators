# mini-news

Paste a news link (or write a topic). Claude (through Claude Code, on your Claude subscription) writes an original post in Brazilian Portuguese plus a vertical (9:16) TV-news style image.
You go through 6 steps in the web app (source → template → style → text → preview → publish), **approve** it, and it's
published to **X** and a **Facebook Page**.

Why these two: they're the platforms that pay for text/image posts and work for a creator in Brazil
(X: Original Content Rewards; Facebook: Content Monetization). YouTube and TikTok only pay for video: that's
mini-studio's job. Both X and Meta exclude reposted or aggregated content from payouts, so every post is written in
your own words, credits the source, and carries your opinion. Nothing is published without your approval.

## Setup
```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```
Claude Code must be installed and logged in (`claude` works in a terminal). No API key: each draft runs
`claude -p` headless, which counts toward your Claude plan's usage.
Then the X and Facebook keys: follow `secrets/README.txt` (`secrets/x.json`, `secrets/facebook.json`).
The images use the static font `~/.local/share/fonts/Montserrat-Bold.ttf` (already installed for mini-studio).
## Styles: how the images look (wizard step 3, "Estilo")
Step 3 works like mini-studio's thumbnail step: a settings card on the left, the GIMP result on the right.
Pick a style (or **Duplicar** to make a variant), choose a **Cor** (azul, roxo, verde, rosa, vermelho, laranja,
turquesa, amarelo), the format, upload a background and a logo, set the channel texts, then **Renderizar com este
estilo**. "Mais ajustes" has every color, the background opacity / darkening, fonts, sizes and per-template JSON.
A style is shared: changing it changes every draft that uses it. A style sets:
| | |
|---|---|
| format | `9:16` (1080×1920) or `4:5` (1080×1350) |
| colors | accent (tabs), breaking tab, background gradient, headline plate, text on the plate, source bar / number boxes, text, secondary text, numbers, quote mark |
| background image | your image behind everything, with opacity, darkening and the diagonal stripes on/off |
| logo | your logo: next to the channel badge (`top`), `top-left`, `top-right` or `none`, and its height |
| fonts | .ttf / .otf for titles and for body text (default: Montserrat Bold; variable fonts are set to Bold) |
| sizes | multipliers (0.5–2) for headline, subhead, quote, numbers, labels, tabs |
| texts | channel name, badge next to it ("NEWS"), footer line, "FONTE:" prefix, show date / badge |
| per template | JSON overrides for one template, e.g. `{"breaking": {"colors": {"accent": ["#ff0000", "#990000"]}}}` |

Styles are files in `styles/<id>.json` (only `default` exists at first; it can't be deleted), uploads in
`styles/assets/`.

## Templates (20, drawn by GIMP)
Every image is drawn by **GIMP 3** in the background (like mini-studio's thumbnails), so each one is also saved as a
layered **`.xcf`** with real, editable text layers. In steps 4 and 5 of the wizard:
- **Abrir no GIMP** opens the image's `.xcf` in GIMP. Fix whatever is out of place, save with **Ctrl+S**.
- **Usar versão do GIMP** turns your saved `.xcf` into the image that gets published (approving does it too).
- Changing the text, template, style or photo afterwards redraws the image and would replace your GIMP edits, so
  the page asks first; the edited version is kept as `work/cards/<id>.xcf.bak` (the original as `.xcf.orig`).

| category | templates | needs |
|---|---|---|
| Título | Breaking news · Manchete · Ao vivo · Alerta · Jornal · TV | – |
| Foto | Foto + título · Foto inteira · Foto dividida · Foto moldura | a photo (the article's, or upload your own: news photos are copyrighted) |
| Dados | Números · Número gigante · Comparação (2 numbers) · Pontos-chave · Entenda · Linha do tempo | numbers / key points |
| Voz | Citação · Citação + foto · Opinião · Pergunta | a real quote / your opinion (without Claude's [suggestion]) / a question |

Claude fills everything they use (kicker, subhead, quote, numbers, key points, question) and suggests the template.
Step 2 draws all the templates the story can use in 6 GIMP processes at once (~14 s for 20, ~39 s in a single
session; the grid fills in as they're done); picking one reuses its preview. `MINI_NEWS_GIMP_WORKERS=N` changes the
number of processes (each uses ~0.7 GB of RAM; above 6 the gain is small: 8 → ~13 s, 10 → ~12.5 s). In 9:16, X and Facebook feeds crop to about 4:5, so everything that must be
read sits in the middle 1080×1350; logo, channel badge, date and footer line are above and below it.

Requires GIMP 3 (`flatpak install flathub org.gimp.GIMP`, or a native `gimp-console`).

## Use
```
python3 news.py                                   # web app (the 5-step wizard): http://127.0.0.1:8010
python3 news.py draft https://site.com/noticia --take "minha opinião"
python3 news.py draft "tema da notícia"           # Claude searches the web first
python3 news.py draft <link> --template quote      # choose the template yourself
python3 news.py render <id> --all                 # draw every template this draft can use (GIMP)
python3 news.py gimp <id>                         # open the image's .xcf in GIMP
python3 news.py gimp-apply <id>                   # use the .xcf you saved as the image to publish
python3 news.py list | show <id> | approve <id>
python3 news.py publish <id> --dry-run            # shows exactly what would be sent
python3 news.py publish <id> [--only x|facebook]
```
Status: `draft` → `approved` → `published`. Editing an approved post sends it back to `draft`.
If one platform fails, the post is `failed`; publishing again only retries the platform that failed.
Approve refuses while your opinion still has Claude's `[suggestion]` or the X post is over 280 characters.

## How it works
| file | does |
|---|---|
| `news_server/services/source.py` | link → article title, site, date, photo, main text (trafilatura) |
| `news_server/services/writer.py` | Claude Code headless (`claude -p --json-schema`): link → no tools, article text in the prompt; topic → only WebSearch / WebFetch allowed. Returns a `Draft` |
| `news_server/services/styles.py` | the styles: defaults, load / save / duplicate / delete, uploaded files |
| `news_server/services/templates/` | `base.py` (style context, layout per format, op builders: background, branding, tabs, plates, text) + one module per template, each returning a GIMP op list |
| `news_server/services/gimp/` | the GIMP engine (from mini-studio): `runner.py` starts GIMP headless / opens the GUI; `gimp_render.py` + helpers run inside GIMP: shapes, gradients, photos, auto-fitting text layers; `.xcf` + `.jpg` |
| `news_server/services/jobs.py` | background jobs (GIMP progress in the page) |
| `news_server/services/drafts.py` | `work/drafts/<id>.json`, approve / publish rules |
| `news_server/services/x_post.py` | X API v2: `/2/media/upload` + `/2/tweets` (OAuth 1.0a user keys) |
| `news_server/services/fb_post.py` | Graph API v26.0: `/{page-id}/photos` with the text as `caption` |
| `news_server/ui/index.html` | the web app: the 5-step wizard + drafts list (one page, no build step) |

Usage: a link draft takes ~20 s, a topic (with web searches) ~40 s to a few minutes, all on your Claude plan.
Posting on X needs an X API plan that allows writes; check its limits in the developer portal.

### How to remove paywalls
https://www.removepaywall.com/