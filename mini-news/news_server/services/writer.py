"""Claude writes the posts, through Claude Code (`claude -p`, your Claude subscription; no API key).

Original wording in Brazilian Portuguese, the source credited, nothing invented.
A link: the article text is read here and sent to Claude, with every tool turned off.
A topic: Claude Code may use only WebSearch / WebFetch to find current facts, then writes from them.
The answer comes back as JSON validated against the Draft schema (`--json-schema`).
"""
import json
import shutil
import subprocess

from pydantic import BaseModel, Field, ValidationError

from ..paths import WORK

X_LIMIT = 280
TIMEOUT = 600            # a topic with web searches can take a few minutes
WEB_TOOLS = "WebSearch,WebFetch"

SYSTEM = """Você escreve posts de notícias para as redes sociais de um criador de conteúdo brasileiro.

Regras:
- Português do Brasil, tom jornalístico, claro e direto. Sem clickbait enganoso.
- Escreva com as suas próprias palavras. Nunca copie frases da fonte: as plataformas não pagam por conteúdo copiado ou só repostado.
- Use apenas fatos que estão na fonte. Não invente números, nomes, datas ou citações.
- Sempre credite a fonte pelo nome do veículo.
- Se a fonte for vaga, parcial, opinativa ou antiga, diga isso em `warnings`.
- Se o criador deu a opinião dele, use-a em `take` (pode melhorar a redação, sem mudar o sentido). Se não deu, escreva em `take` uma sugestão curta de opinião entre [colchetes], para ele editar.

Campos:
- headline: título curto para a imagem do post (máx. 70 caracteres, sem ponto final).
- x_text: post para o X com no máximo 230 caracteres (o link da fonte é adicionado depois). Fato principal + por que importa. Sem hashtags.
- facebook_text: 2 a 4 parágrafos curtos: o que aconteceu, contexto, por que importa, e termine com uma pergunta para os leitores comentarem. Mencione a fonte no texto.
- take: a opinião do criador, 1 a 2 frases.
- source_name / source_url: o veículo e o link de onde vieram os fatos.
- hashtags: 2 a 4 hashtags relevantes, sem o #.
- warnings: avisos para o criador revisar (pode ficar vazio).

Campos para a imagem vertical do post:
- kicker: rótulo curto em maiúsculas para a etiqueta, ex.: URGENTE, ECONOMIA, ESPORTE, CULTURA (máx. 14 caracteres).
- subhead: uma linha que complementa o título (máx. 90 caracteres).
- quote: só se a fonte traz uma citação real de alguém, copiada palavra por palavra (é a única exceção à regra de não copiar), com author (nome) e role (cargo ou quem é). Máx. 220 caracteres. Se não houver citação, deixe text vazio.
- numbers: até 3 números importantes que estão na fonte, cada um com value curto (ex.: "354,5 mi t", "+2,4%", "R$ 1,2 bi") e label curto que explica (máx. 40 caracteres). Lista vazia se não houver.
- points: 2 a 4 fatos-chave da notícia, com as suas palavras, cada um com no máximo 70 caracteres.
- question: a pergunta para os leitores comentarem (a mesma que fecha o texto do Facebook), máx. 90 caracteres.
- template: o melhor template de imagem para esta notícia, um destes ids:
  breaking (fato urgente), headline (manchete forte, sem foto), live (algo acontecendo agora), alert (alerta, risco,
  aviso), newspaper (notícia séria, política, economia), tv (estilo telejornal), photo / photo_full / photo_split /
  photo_frame (quando a foto da matéria conta a história), numbers (até 3 números), big_number (um número marcante),
  versus (comparação de 2 números), points (resumo em tópicos), explainer (explicar um tema), timeline (fatos em
  sequência), quote (citação forte), quote_photo (citação + foto de quem falou), opinion (opinião do criador),
  question (assunto que gera debate)."""


class Quote(BaseModel):
    text: str = ""
    author: str = ""
    role: str = ""


class Number(BaseModel):
    value: str
    label: str


class Draft(BaseModel):
    headline: str
    x_text: str
    facebook_text: str
    take: str
    source_name: str
    source_url: str
    hashtags: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    kicker: str = "NOTÍCIA"
    subhead: str = ""
    quote: Quote = Field(default_factory=Quote)
    numbers: list[Number] = Field(default_factory=list, max_length=3)
    points: list[str] = Field(default_factory=list, max_length=4)
    question: str = ""
    template: str = "breaking"


def _claude(prompt, tools=""):
    """Run Claude Code headless and return the structured output (a dict matching Draft)."""
    exe = shutil.which("claude")
    if not exe:
        raise RuntimeError("Claude Code isn't installed (the `claude` command): https://claude.com/claude-code")
    cmd = [exe, "-p", prompt, "--output-format", "json", "--json-schema", json.dumps(Draft.model_json_schema()),
           "--system-prompt", SYSTEM, "--tools", tools, "--no-session-persistence", "--strict-mcp-config"]
    if tools:
        cmd += ["--allowedTools", tools]   # pre-approved: in -p mode nobody is there to click "allow"
    WORK.mkdir(parents=True, exist_ok=True)
    try:   # run from work/ so no project instructions (CLAUDE.md) get mixed into the post
        r = subprocess.run(cmd, cwd=WORK, capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Claude Code took more than {TIMEOUT // 60} minutes; try again")
    try:
        out = json.loads(r.stdout)
    except json.JSONDecodeError:
        msg = (r.stderr or r.stdout).strip()[-400:]
        raise RuntimeError(f"Claude Code failed: {msg or f'exit code {r.returncode}'}")
    if out.get("is_error") or out.get("subtype") != "success":
        raise RuntimeError(f"Claude Code failed ({out.get('subtype')}): {str(out.get('result'))[:400]}")
    return out.get("structured_output") or json.loads(out["result"])


def write(source_text, take=""):
    """Article text -> Draft (no tools: everything Claude needs is in the prompt)."""
    prompt = f"<fonte>\n{source_text}\n</fonte>\n\n"
    prompt += f"<opiniao_do_criador>\n{take}\n</opiniao_do_criador>\n\n" if take.strip() else ""
    prompt += "Escreva o rascunho do post a partir da fonte acima."
    return _validate(_claude(prompt))


def write_topic(topic, take=""):
    """Topic -> Draft: Claude Code searches the web for current, reliable reports first."""
    prompt = (f"Pesquise na web as notícias mais recentes e confiáveis sobre: {topic}\n"
              "Prefira veículos jornalísticos conhecidos; abra a matéria principal para conferir os fatos. "
              "Use essa matéria como fonte (source_name / source_url). Se as fontes discordarem, diga em warnings.\n\n")
    prompt += f"<opiniao_do_criador>\n{take}\n</opiniao_do_criador>\n\n" if take.strip() else ""
    prompt += "Depois escreva o rascunho do post."
    return _validate(_claude(prompt, WEB_TOOLS))


def _validate(data):
    try:
        return Draft.model_validate(data)
    except ValidationError as e:
        raise RuntimeError(f"Claude Code's answer didn't match the post format: {e}") from e


def x_post_text(d):
    """The final X post: text + the source link (X counts any link as 23 characters)."""
    return f"{d['x_text'].strip()}\n\n{d['source_url']}".strip()


def x_length(d):
    return len(d["x_text"].strip()) + (2 + 23 if d.get("source_url") else 0)


def facebook_post_text(d):
    tags = " ".join("#" + t.lstrip("#").replace(" ", "") for t in d.get("hashtags", []))
    parts = [d["facebook_text"].strip(), d.get("take", "").strip(), f"Fonte: {d['source_name']} {d['source_url']}".strip(), tags]
    return "\n\n".join(p for p in parts if p)
