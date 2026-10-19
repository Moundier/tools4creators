"""CASA NOVA Studio backend: FastAPI app. API under /api (see routes/), the built Angular app at /.

  models/    state: channels, settings, projects (work/channels/<channel>/<id>/project.json), background jobs
  routes/    HTTP endpoints, one module per area
  services/  the work behind each wizard step (calls the project's command-line tools)
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from .models import channel
from .paths import UI_DIST
from .routes import channels, library, mic, projects, recordings, settings, steps



def _cookie(text):
    for part in text.split(";"):
        k, _, v = part.strip().partition("=")
        if k == "studio_channel":
            return v
    return None


class ChannelMiddleware:
    """Puts the request's channel into channel.current (plain ASGI, so the value reaches the endpoint and the jobs
    it starts). The X-Channel header wins; <img>/<video>/<audio> can't send headers, so the studio_channel cookie
    (set when a channel is chosen) is the fallback."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        cid = headers.get(b"x-channel", b"").decode() or _cookie(headers.get(b"cookie", b"").decode()) or None
        token = channel.current.set(cid)
        try:
            await self.app(scope, receive, send)
        finally:
            channel.current.reset(token)


app = FastAPI(title="CASA NOVA Studio")
app.add_middleware(ChannelMiddleware)
for module in (channels, recordings, projects, steps, library, settings, mic):
    app.include_router(module.router)


@app.exception_handler(channel.NoChannel)
def no_channel(request: Request, exc: channel.NoChannel):
    if exc.args and exc.args[0]:
        return JSONResponse({"detail": f"channel not found: {exc.args[0]}"}, status_code=404)
    return JSONResponse({"detail": "choose a channel first"}, status_code=400)


@app.get("/{path:path}", include_in_schema=False)
def ui(path: str):
    """The Angular app; unknown paths get index.html so client-side routes work. Registered last."""
    if path.startswith("api/"):
        raise HTTPException(404, "not found")
    if not UI_DIST.is_dir():
        return Response("Studio UI not built yet: cd studio-ui && npm install && npm run build", media_type="text/plain")
    f = (UI_DIST / path).resolve()
    if path and f.is_relative_to(UI_DIST.resolve()) and f.is_file():
        return FileResponse(f)
    return FileResponse(UI_DIST / "index.html")
