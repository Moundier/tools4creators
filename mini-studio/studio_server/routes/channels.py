"""Channels: list / add / rename / recolor / delete (the /browse page). These don't need X-Channel."""
from fastapi import APIRouter, Body, HTTPException

from ..models import channel
from .deps import bad_request

router = APIRouter(prefix="/api")


@router.get("/channels")
def list_channels():
    return {"channels": [channel.summary(c) for c in channel.all_channels()], "colors": channel.COLORS}


@router.post("/channels")
def add_channel(body: dict = Body(...)):
    return channel.summary(bad_request(channel.create, body.get("name"), body.get("color")))


def _known(cid):
    try:
        channel.load(cid)
    except channel.NoChannel:
        raise HTTPException(404, "channel not found")


@router.patch("/channels/{cid}")
def edit_channel(cid: str, body: dict = Body(...)):
    _known(cid)
    return channel.summary(bad_request(channel.update, cid, {k: body[k] for k in ("name", "color") if k in body}))


@router.delete("/channels/{cid}")
def delete_channel(cid: str):
    _known(cid)
    bad_request(channel.delete, cid)
    return {"deleted": cid}
