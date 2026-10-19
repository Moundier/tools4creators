"""Set up OBS Studio for the channel: one profile + one scene collection per mode.

  python3 studio.py obs                  # write all 4 modes (OBS must be closed)
  python3 studio.py obs --only Talk      # rewrite one mode
  python3 studio.py obs --keep-old       # don't remove the old "Untitled" profile / scenes

Modes (each is a profile with its own output settings + a scene collection with the same name):
  Gameplay  1080p60, high quality recording     F1 Gameplay + cam (round cam, top left) · F2 Gameplay · F3 Me
  Live      1080p60, YouTube 8000 kbps + record F1 Starting soon · F2 Live · F3 Me · F4 Be right back
  Talk      1080p30, just you (DJI Pocket 3)    F1 Me · F2 Me (close)
  News      1080p30, screen + you               F1 Screen + me · F2 Screen · F3 Me
            TV-news graphics: scrolling ticker (crawl), lower third (name / topic), channel bug.
            Edit the text in ~/.config/obs-studio/mini-studio/news/{ticker,name,topic}.txt: OBS updates it live.
Everywhere: F9 record / stop, F10 pause / resume; in Live, F11 go live / end.

Video: DJI Pocket 3 (USB webcam mode). Mic: the DJI Mic paired to the Pocket 3 (Bluetooth), straight from its USB audio.
Recordings go to ~/Videos as H.264 (NVENC) hybrid MP4, where mini-studio picks them up.
Audio tracks: 1 = everything, 2 = voice only, 3 = game / PC sound.
Game scenes: "Capture board (Elgato)" (Elgato 4K X video) + "Game audio (Elgato)" (its USB audio, tracks 1 + 3).
Everything is backed up to ~/.config/obs-studio/backup-<date>/ first. App-menu shortcuts: "OBS · <mode>".
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

OBS = Path.home() / ".config" / "obs-studio"
BASIC = OBS / "basic"
ASSETS = OBS / "mini-studio"
APPS = Path.home() / ".local" / "share" / "applications"
VIDEOS = Path.home() / "Videos"
CAMERA = "/dev/v4l/by-id/usb-DJI_DJIPocket3_123456789ABCDEF-video-index0"
MIC = "alsa_input.usb-DJI_DJIPocket3_123456789ABCDEF-02.analog-stereo"   # DJI Mic via the Pocket 3 (not CASA NOVA)
BOARD = "/dev/v4l/by-id/usb-Elgato_Elgato_4K_X_A7SNB61831WG8M-video-index0"
GAME_AUDIO = "alsa_input.usb-Elgato_Elgato_4K_X_A7SNB61831WG8M-02.analog-stereo"
W, H = 1920, 1080
MJPEG = 1196444237                      # V4L2 fourcc 'MJPG'
ENCODER = "obs_nvenc_h264_tex"          # NVENC on the GPU; H.264 so browsers (mini-studio) can play it
MODES = ["Gameplay", "Live", "Talk", "News"]
CAM_BOX = (480, 270, 32)                # corner camera: width, height, margin from the edges
RADIUS = 22                             # rounded corners of the corner camera
HELPER = "· camera (rounded)"           # helper scene: last in the list, no hotkey, don't switch to it
ROUND_CAM = (340, 28)                   # Gameplay + cam: round camera diameter, margin from the top-left corner
ROUND_FEATHER = 110                     # px (at 1080 tall) over which the round camera fades into the game
HELPER_ROUND = "· camera (round)"
NEWS = ASSETS / "news"                  # News mode texts (ticker, lower third), edited by the user
NEWS_TEXT = {"ticker": "Bem-vindo ao {channel}  •  Edite ~/.config/obs-studio/mini-studio/news/ticker.txt para mudar as manchetes  •  ",
             "name": "Manchete principal", "topic": "Uma linha com os detalhes da notícia"}
# TV-news look (classic broadcast blue + silver, not the channel color)
NEWS_BLUE = ((48, 86, 255), (10, 26, 150))        # label tabs: gradient top -> bottom
NEWS_NAVY = ((16, 30, 96), (5, 11, 48))           # ticker strip
NEWS_SILVER = ((250, 251, 253), (214, 218, 226), (176, 182, 194))  # plates: top, middle, bottom
NEWS_INK = 0xFF4A1A0D                             # dark navy text on silver (0xAABBGGRR)
TICKER_H, TICKER_LABEL = 60, 300        # ticker bar height; width of the "ÚLTIMAS" tab on its left
LOWER_THIRD = (40, 826, 1240, 180)      # x, y, w, h of the lower-third image, just above the ticker
BUG_MARGIN = 32                         # channel badge, top right

# mixer bitmasks: track 1 = everything, 2 = voice, 3 = game / PC
VOICE_TRACKS, GAME_TRACKS = 0b011, 0b101


# ---------------------------------------------------------------- images (masks, frames, live screens)

def font(size):
    from PIL import ImageFont
    for path in (Path.home() / ".local/share/fonts/Montserrat-Variable.ttf",):
        if path.is_file():
            f = ImageFont.truetype(str(path), size)
            try:
                f.set_variation_by_name("Black")
            except (OSError, ValueError):
                pass
            return f
    return ImageFont.load_default(size)


def make_assets(color):
    """Rounded mask + thin frame for the corner camera, and the 'Starting soon' / 'Be right back' screens."""
    from PIL import Image, ImageDraw, ImageFilter

    ASSETS.mkdir(parents=True, exist_ok=True)
    w, h, _ = CAM_BOX
    s = 4  # draw big, then shrink: smooth edges
    mask = Image.new("L", (w * s, h * s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w * s - 1, h * s - 1], RADIUS * s, fill=255)
    mask = mask.resize((w, h), Image.LANCZOS)
    Image.merge("RGBA", (mask, mask, mask, mask)).save(ASSETS / "cam_mask.png")

    frame = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    ImageDraw.Draw(frame).rounded_rectangle([0, 0, w * s - 1, h * s - 1], RADIUS * s, outline=(255, 255, 255, 230),
                                            width=3 * s)
    frame.resize((w, h), Image.LANCZOS).save(ASSETS / "cam_frame.png")

    shadow = Image.new("RGBA", (w + 80, h + 80), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([40, 48, w + 40, h + 48], RADIUS, fill=(0, 0, 0, 150))
    shadow.filter(ImageFilter.GaussianBlur(18)).save(ASSETS / "cam_shadow.png")

    # round camera: a circle in the middle of the 1920x1080 helper scene whose edge fades out
    r = H // 2 - ROUND_FEATHER // 2
    circle = Image.new("L", (W, H), 0)
    ImageDraw.Draw(circle).ellipse([W / 2 - r, H / 2 - r, W / 2 + r, H / 2 + r], fill=255)
    circle = circle.filter(ImageFilter.GaussianBlur(ROUND_FEATHER / 2.5))
    Image.merge("RGBA", (circle, circle, circle, circle)).save(ASSETS / "cam_round_mask.png")

    rgb = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
    for name, title, sub in (("starting", "STARTING SOON", "a live já vai começar"),
                             ("brb", "BE RIGHT BACK", "volto já")):
        bg = Image.new("RGB", (W, H), (15, 15, 15))
        glow = Image.new("RGB", (W, H), rgb)
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).ellipse([-W * 0.25, -H * 0.9, W * 1.25, H * 0.55], fill=110)
        bg.paste(glow, (0, 0), m.filter(ImageFilter.GaussianBlur(180)))
        d = ImageDraw.Draw(bg)
        f1, f2 = font(150), font(44)
        d.text((W / 2, H / 2 - 20), title, font=f1, fill=(245, 245, 245), anchor="ms")
        d.rounded_rectangle([W / 2 - 60, H / 2 + 20, W / 2 + 60, H / 2 + 28], 4, fill=rgb)
        d.text((W / 2, H / 2 + 110), sub.upper(), font=f2, fill=(170, 170, 170), anchor="ms")
        bg.save(ASSETS / f"{name}.png")
    make_news_assets()


def _gradient(w, h, stops):
    """RGBA image, vertical gradient through the color stops."""
    from PIL import Image
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1) * (len(stops) - 1)
        i = min(int(t), len(stops) - 2)
        c = [round(a + (b - a) * (t - i)) for a, b in zip(stops[i], stops[i + 1])]
        for x in range(w):
            px[x, y] = (*c, 255)
    return img


def _shape(canvas, box, slant, stops, shine=False, left_slant=None):
    """Paste a gradient parallelogram onto canvas. box = (x, y, w, h); slant = how far the right edge leans (px).
    left_slant: same for the left edge (None = straight). shine: lighter top half, like glossy TV graphics."""
    from PIL import Image, ImageDraw
    x, y, w, h = box
    s = 4
    ls = left_slant or 0
    mask = Image.new("L", (w * s, h * s), 0)
    ImageDraw.Draw(mask).polygon([(ls * s, 0), (w * s, 0), ((w - slant) * s, h * s), (0, h * s)], fill=255)
    mask = mask.resize((w, h), Image.LANCZOS)
    fill = _gradient(w, h, stops)
    if shine:
        gloss = Image.new("RGBA", (w, h), (255, 255, 255, 0))
        ImageDraw.Draw(gloss).rectangle([0, 0, w, h * 0.45], fill=(255, 255, 255, 38))
        fill = Image.alpha_composite(fill, gloss)
    canvas.paste(fill, (x, y), mask)


def make_news_assets(channel=None):
    """News mode, broadcast style (blue tabs, silver plates): ticker bar, lower third, channel badge,
    and the default texts (never overwritten). The texts that change live are OBS text sources on top."""
    from PIL import Image, ImageDraw

    name = channel or channel_name()
    channel = name.upper()
    white, ink = (255, 255, 255), (13, 26, 74)

    bar = Image.new("RGBA", (W, TICKER_H), (0, 0, 0, 0))
    _shape(bar, (TICKER_LABEL - 30, 0, W - TICKER_LABEL + 30, TICKER_H), 0, NEWS_NAVY)
    _shape(bar, (TICKER_LABEL - 30, 0, W - TICKER_LABEL + 30, 3), 0, NEWS_SILVER[:2])        # silver hairline
    _shape(bar, (0, 0, TICKER_LABEL, TICKER_H), 26, NEWS_BLUE, shine=True)
    ImageDraw.Draw(bar).text(((TICKER_LABEL - 26) / 2, TICKER_H / 2), "ÚLTIMAS", font=font(30), fill=white,
                             anchor="mm")
    bar.save(ASSETS / "news_ticker.png")

    _, _, w, h = LOWER_THIRD
    lt = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    _shape(lt, (24, 50, w - 24, 110), 34, NEWS_SILVER, left_slant=34)                       # silver plate
    _shape(lt, (330, 160, w - 380, 14), 10, NEWS_BLUE, left_slant=10)                       # blue strip under it
    tab_w = int(font(28).getlength(channel)) + 90
    _shape(lt, (40, 6, tab_w, 50), 22, NEWS_BLUE, shine=True, left_slant=22)                 # channel tab
    ImageDraw.Draw(lt).text((40 + tab_w / 2, 31), channel, font=font(28), fill=white, anchor="mm")
    lt.save(ASSETS / "news_lower_third.png")

    f = font(30)
    left_w, right_w, bh = int(f.getlength(channel)) + 56, int(f.getlength("NEWS")) + 60, 62
    bug = Image.new("RGBA", (left_w + right_w, bh), (0, 0, 0, 0))
    _shape(bug, (left_w - 20, 0, right_w + 20, bh), 0, NEWS_SILVER)
    _shape(bug, (0, 0, left_w, bh), 18, NEWS_BLUE, shine=True)
    d = ImageDraw.Draw(bug)
    d.text(((left_w - 18) / 2, bh / 2), channel, font=f, fill=white, anchor="mm")
    d.text((left_w + right_w / 2 - 4, bh / 2), "NEWS", font=f, fill=ink, anchor="mm")
    bug.save(ASSETS / "news_bug.png")

    NEWS.mkdir(parents=True, exist_ok=True)
    for name, text in NEWS_TEXT.items():
        f = NEWS / f"{name}.txt"
        if not f.exists():
            f.write_text(text.format(channel=name), encoding="utf-8")


# ---------------------------------------------------------------- scene collection JSON

def source(sid, name, settings=None, versioned=None, mixers=0, filters=None, hotkeys=None, muted=False):
    s = {"name": name, "uuid": str(uuid.uuid4()), "id": sid, "versioned_id": versioned or sid,
         "settings": settings or {}, "mixers": mixers, "sync": 0, "flags": 0, "volume": 1.0, "balance": 0.5,
         "enabled": True, "muted": muted, "push-to-mute": False, "push-to-mute-delay": 0, "push-to-talk": False,
         "push-to-talk-delay": 0, "hotkeys": hotkeys or {}, "deinterlace_mode": 0, "deinterlace_field_order": 0,
         "monitoring_type": 0, "private_settings": {}}
    if filters:
        s["filters"] = filters
    return s


def camera(name="DJI Pocket 3"):
    return source("v4l2_input", name, {"device_id": CAMERA, "input": 0, "pixelformat": MJPEG,
                                       "resolution": (W << 16) | H, "framerate": (1 << 16) | 30,
                                       "buffering": False, "auto_reset": True})


def rounded_camera(cam):
    """A helper scene with the camera full size and a rounded-corner mask on the whole scene.
    The camera can only be opened once, so the corner shots use this scene instead of a second camera source;
    the mask is stretched over 1920x1080 and shrinks with it, so the corners stay round at any size."""
    mask = source("mask_filter", "Rounded corners", {"type": "mask_alpha_filter.effect",
                                                     "image_path": str(ASSETS / "cam_mask.png"), "stretch": True},
                  versioned="mask_filter_v2")
    sc = scene(HELPER, None, [(cam, {"box": (W, H)})])
    sc["filters"] = [mask]
    return sc


def round_camera(cam):
    """Helper scene: the camera as a 1080x1080 square in the middle, masked to a circle with a soft edge.
    Scenes using it crop its 420 px sides away, so only the square is left."""
    mask = source("mask_filter", "Round, soft edge", {"type": "mask_alpha_filter.effect",
                                                      "image_path": str(ASSETS / "cam_round_mask.png"), "stretch": True},
                  versioned="mask_filter_v2")
    sc = scene(HELPER_ROUND, None, [(cam, {"pos": ((W - H) // 2, 0), "box": (H, H)})])
    sc["filters"] = [mask]
    return sc


def round_cam(helper):
    d, m = ROUND_CAM
    side = (W - H) // 2
    return [(helper, {"pos": (m, m), "box": (d, d), "crop": (side, 0, side, 0)})]


def image(name, file):
    return source("image_source", name, {"file": str(file), "unload": False})


def item(src, iid, pos=(0, 0), box=None, fit="cover", crop=(0, 0, 0, 0), visible=True):
    """A scene item. box=(w, h): the source is scaled into it (cover = fill and crop, fit = letterbox)."""
    it = {"name": src["name"], "source_uuid": src["uuid"], "visible": visible, "locked": False, "rot": 0.0,
          "align": 5, "bounds_type": 0, "bounds_align": 0, "bounds_crop": False,
          "crop_left": crop[0], "crop_top": crop[1], "crop_right": crop[2], "crop_bottom": crop[3], "id": iid,
          "group_item_backup": False, "pos": {"x": float(pos[0]), "y": float(pos[1])},
          "scale": {"x": 1.0, "y": 1.0}, "bounds": {"x": 0.0, "y": 0.0}, "scale_filter": "disable",
          "blend_method": "default", "blend_type": "normal", "show_transition": {"duration": 0},
          "hide_transition": {"duration": 0}, "private_settings": {}}
    if box:
        it.update(bounds_type=3 if fit == "cover" else 2, bounds_crop=fit == "cover",
                  bounds={"x": float(box[0]), "y": float(box[1])})
    return it


def scene(name, key, layers):
    """layers: [(source, item kwargs), ...] bottom to top."""
    items = [item(src, i + 1, **kw) for i, (src, kw) in enumerate(layers)]
    return source("scene", name, {"id_counter": len(items), "custom_size": False, "items": items},
                  hotkeys={"OBSBasic.SelectScene": [{"key": f"OBS_KEY_F{key}"}] if key else []})


def text_file(name, file, size, color=0xFFFFFFFF, filters=None):
    """FreeType text read from a file: OBS reloads it when the file changes. color is 0xAABBGGRR.
    Needs the static Montserrat-Bold.ttf in ~/.local/share/fonts: OBS's FreeType text can't pick a weight in the
    variable Montserrat, so with only that file it draws the default (Thin) weight."""
    return source("text_ft2_source", name, {"from_file": True, "text_file": str(file), "color1": color,
                                            "color2": color, "outline": False, "drop_shadow": False,
                                            "word_wrap": False, "antialiasing": True,
                                            "font": {"face": "Montserrat", "style": "Bold", "size": size,
                                                     "flags": 1}},
                  versioned="text_ft2_source_v2", filters=filters)


def news_overlay():
    """Helper scene over every News shot: the scrolling ticker (crawl) at the bottom + the channel bug.
    Returns (scene, its sources): the sources must be listed in the collection too, or OBS drops them."""
    from PIL import Image
    scroll = source("scroll_filter", "Crawl", {"speed_x": 110.0, "speed_y": 0.0, "limit_cx": True,
                                              "cx": W - TICKER_LABEL - 4, "limit_cy": False, "loop": True})
    ticker = text_file("Ticker text", NEWS / "ticker.txt", 30, filters=[scroll])
    bar, bug = image("Ticker bar", ASSETS / "news_ticker.png"), image("Channel bug", ASSETS / "news_bug.png")
    bw = Image.open(ASSETS / "news_bug.png").width if (ASSETS / "news_bug.png").exists() else 300
    m, y = BUG_MARGIN, H - TICKER_H
    sc = scene("· news overlay", None, [(bar, {"pos": (0, y)}), (ticker, {"pos": (TICKER_LABEL + 4, y + 11)}),
                                        (bug, {"pos": (W - m - bw, m)})])
    return sc, [bar, ticker, bug]


def lower_third():
    """Helper scene: name / topic plate (chyron) above the ticker. Hide it with the eye icon in the scene.
    Returns (scene, its sources), like news_overlay()."""
    x, y, _, _ = LOWER_THIRD
    plate = image("Lower third plate", ASSETS / "news_lower_third.png")
    name = text_file("Lower third name", NEWS / "name.txt", 50, color=NEWS_INK)
    topic = text_file("Lower third topic", NEWS / "topic.txt", 26, color=NEWS_INK)
    sc = scene("· lower third", None, [(plate, {"pos": (x, y)}), (name, {"pos": (x + 82, y + 56)}),
                                       (topic, {"pos": (x + 84, y + 118)})])
    return sc, [plate, name, topic]


def corner_cam(cam, shadow, frame, bottom=0):
    """bottom: extra space kept free under the camera (the News ticker)."""
    w, h, m = CAM_BOX
    x, y = W - m - w, H - m - h - bottom
    return [(shadow, {"pos": (x - 40, y - 40)}), (cam, {"pos": (x, y), "box": (w, h)}), (frame, {"pos": (x, y)})]


def collection(mode):
    """(sources, scene names in order, desktop audio on?) for a mode."""
    full = camera()
    corner, shadow, frame = rounded_camera(full), image("Cam shadow", ASSETS / "cam_shadow.png"), image(
        "Cam frame", ASSETS / "cam_frame.png")
    board = source("v4l2_input", "Capture board (Elgato)", {"device_id": BOARD, "input": 0})
    screen = source("xshm_input", "Screen", {"screen": 0, "show_cursor": True, "advanced": False},
                    versioned="xshm_input_v2")
    me = lambda key: scene("Me", key, [(full, {"box": (W, H)})])
    if mode == "Gameplay":  # round camera with a soft edge, top left
        roundc = round_camera(full)
        scenes = [scene("Gameplay + cam", 1, [(board, {"box": (W, H), "fit": "fit"}), *round_cam(roundc)]),
                  scene("Gameplay", 2, [(board, {"box": (W, H), "fit": "fit"})]),
                  me(3)]
        extra, desktop = [board, full, roundc], False
    elif mode == "Live":
        starting, brb = image("Starting soon", ASSETS / "starting.png"), image("Be right back", ASSETS / "brb.png")
        scenes = [scene("Starting soon", 1, [(starting, {})]),
                  scene("Live", 2, [(board, {"box": (W, H), "fit": "fit"}), *corner_cam(corner, shadow, frame)]),
                  me(3),
                  scene("Be right back", 4, [(brb, {})])]
        extra, desktop = [starting, brb, board, full, corner, shadow, frame], False
    elif mode == "Talk":
        # 1.25x closer: crop 192 px each side, more from the bottom than the top so the head stays in frame
        scenes = [me(1), scene("Me (close)", 2, [(full, {"box": (W, H), "crop": (192, 60, 192, 156)})])]
        extra, desktop = [full], False
    else:  # News
        (overlay, overlay_parts), (lower, lower_parts) = news_overlay(), lower_third()
        scenes = [scene("Screen + me", 1, [(screen, {}), *corner_cam(corner, shadow, frame, bottom=TICKER_H),
                                           (lower, {}), (overlay, {})]),
                  scene("Screen", 2, [(screen, {}), (overlay, {})]),
                  scene("Me", 3, [(full, {"box": (W, H)}), (lower, {}), (overlay, {})])]
        extra, desktop = [screen, full, corner, shadow, frame, *lower_parts, *overlay_parts, lower, overlay], True
    for helper in [src for src in extra if src["id"] == "scene"]:  # helper scenes go last in the list
        extra.remove(helper)
        scenes.append(helper)
    return extra + scenes, [s["name"] for s in scenes], desktop


def collection_json(mode):
    sources, order, desktop = collection(mode)
    audio_hotkeys = {"libobs.mute": [], "libobs.unmute": [], "libobs.push-to-mute": [], "libobs.push-to-talk": []}
    mic = source("pulse_input_capture", "Mic (DJI)", {"device_id": MIC}, mixers=VOICE_TRACKS,
                 hotkeys=audio_hotkeys)
    devices = {"AuxAudioDevice1": mic}
    if mode in ("Gameplay", "Live"):  # the capture card's video source has no sound: its audio is a separate device
        devices["AuxAudioDevice2"] = source("pulse_input_capture", "Game audio (Elgato)", {"device_id": GAME_AUDIO},
                                            mixers=GAME_TRACKS, hotkeys=audio_hotkeys)
    if desktop:  # PC sound only in News (videos on the blogs); the game's sound comes from the capture board
        devices["DesktopAudioDevice1"] = source("pulse_output_capture", "Desktop Audio", {"device_id": "default"},
                                                mixers=GAME_TRACKS, hotkeys=audio_hotkeys)
    return {"name": mode, **devices, "sources": sources, "groups": [],
            "scene_order": [{"name": n} for n in order], "current_scene": order[0],
            "current_program_scene": order[0], "canvases": [], "current_transition": "Fade",
            "transition_duration": 250, "transitions": [],
            "quick_transitions": [{"name": "Cut", "duration": 250, "hotkeys": [], "id": 1, "fade_to_black": False},
                                  {"name": "Fade", "duration": 250, "hotkeys": [], "id": 2, "fade_to_black": False}],
            "preview_locked": False, "scaling_enabled": False, "scaling_level": 0, "scaling_off_x": 0.0,
            "scaling_off_y": 0.0, "virtual-camera": {"type2": 3}, "modules": {}, "resolution": {"x": W, "y": H},
            "version": 2}


# ---------------------------------------------------------------- profiles (output settings)

def hotkey(key):
    return json.dumps({"bindings": [{"key": key}]})


def profile_files(mode):
    """{filename: text} for the profile folder."""
    fps = 60 if mode in ("Gameplay", "Live") else 30
    live = mode == "Live"
    hotkeys = {"OBSBasic.StartRecording": "OBS_KEY_F9", "OBSBasic.StopRecording": "OBS_KEY_F9",
               "OBSBasic.PauseRecording": "OBS_KEY_F10", "OBSBasic.UnpauseRecording": "OBS_KEY_F10"}
    if live:
        hotkeys.update({"OBSBasic.StartStreaming": "OBS_KEY_F11", "OBSBasic.StopStreaming": "OBS_KEY_F11"})
    ini = f"""[General]
Name={mode}

[Output]
Mode=Advanced
FilenameFormatting=%CCYY-%MM-%DD %hh-%mm-%ss
DelayEnable=false
Reconnect=true
RetryDelay=2
MaxRetries=25

[AdvOut]
ApplyServiceSettings=true
Encoder={ENCODER}
TrackIndex=1
RecType=Standard
RecFilePath={VIDEOS}
RecFormat2=hybrid_mp4
RecEncoder={ENCODER}
RecTracks=7
RecUseRescale=false
RecSplitFile=false
AudioEncoder=ffmpeg_aac
RecAudioEncoder=ffmpeg_aac
Track1Bitrate=192
Track2Bitrate=192
Track3Bitrate=192
Track1Name=Mix
Track2Name=Voice
Track3Name=Game / PC
RecRB=false

[Video]
BaseCX={W}
BaseCY={H}
OutputCX={W}
OutputCY={H}
FPSType=0
FPSCommon={fps}
ScaleType=lanczos
ColorFormat=NV12
ColorSpace=709
ColorRange=Partial

[Audio]
SampleRate=48000
ChannelSetup=Stereo
DesktopDevice1={"default" if mode == "News" else "disabled"}
AuxDevice1={MIC}
AuxDevice2={GAME_AUDIO if mode in ("Gameplay", "Live") else "disabled"}

[Hotkeys]
""" + "".join(f"{k}={hotkey(v)}\n" for k, v in hotkeys.items())
    # CQP 20: smaller files than 18 with no visible difference. Keep p5 / qres / no lookahead: the RTX 3050 runs up to
    # 3 encodes at once (main + source-record game + cam) and p7 / fullres / lookahead made it skip ~25% of the frames
    record = {"rate_control": "CQP", "cqp": 20, "preset2": "p5", "tune": "hq", "multipass": "qres",
              "profile": "high", "keyint_sec": 2, "bf": 2, "adaptive_quantization": True, "lookahead": False}
    stream = {"rate_control": "CBR", "bitrate": 8000, "preset2": "p5", "tune": "hq", "multipass": "qres",
              "profile": "high", "keyint_sec": 2, "bf": 2, "adaptive_quantization": True, "lookahead": False}
    service = {"type": "rtmp_common", "settings": {"service": "YouTube - RTMPS", "protocol": "RTMPS",
                                                    "server": "rtmps://a.rtmps.youtube.com:443/live2", "key": ""}}
    files = {"basic.ini": ini, "recordEncoder.json": json.dumps(record, indent=2),
             "streamEncoder.json": json.dumps(stream, indent=2)}
    if live:  # only Live streams; YouTube elsewhere would open its login panel for nothing
        files["service.json"] = json.dumps(service, indent=2)
    return files


# ---------------------------------------------------------------- the rest of the setup

def set_user_ini(mode):
    """Open OBS on `mode`, and record automatically while live (the Live profile keeps a copy for Shorts)."""
    f = OBS / "user.ini"
    text = f.read_text(encoding="utf-8") if f.is_file() else ""
    values = {"Basic": {"Profile": mode, "ProfileDir": mode, "SceneCollection": mode, "SceneCollectionFile": mode},
              "BasicWindow": {"RecordWhenStreaming": "true", "KeepRecordingWhenStreamStops": "false"}}
    lines, section, seen = text.splitlines(), None, set()
    out = []
    for line in lines:
        if line.startswith("[") and line.endswith("]"):
            if section in values:  # add keys the section didn't have
                out += [f"{k}={v}" for k, v in values[section].items() if (section, k) not in seen]
            section = line[1:-1]
            out.append(line)
            continue
        key = line.split("=", 1)[0]
        if section in values and key in values[section]:
            out.append(f"{key}={values[section][key]}")
            seen.add((section, key))
        else:
            out.append(line)
    if section in values:
        out += [f"{k}={v}" for k, v in values[section].items() if (section, k) not in seen]
    for sec, kv in values.items():
        if f"[{sec}]" not in lines:
            out += ["", f"[{sec}]"] + [f"{k}={v}" for k, v in kv.items()]
    f.write_text("\n".join(out) + "\n", encoding="utf-8")


def desktop_entry(mode):
    APPS.mkdir(parents=True, exist_ok=True)
    (APPS / f"obs-{mode.lower()}.desktop").write_text(f"""[Desktop Entry]
Type=Application
Name=OBS · {mode}
Comment=OBS Studio in the {mode} mode (mini-studio)
Exec=obs --profile "{mode}" --collection "{mode}"
Icon=com.obsproject.Studio
Terminal=false
Categories=AudioVideo;Recorder;
StartupWMClass=obs
""", encoding="utf-8")


def obs_running():
    return subprocess.run(["pgrep", "-x", "obs"], capture_output=True).returncode == 0


def oldest_channel():
    """channel.json of the oldest channel in mini-studio, or {} (read only: never triggers the channels migration)."""
    from ..paths import WORK
    found = []
    for f in (WORK / "channels").glob("*/channel.json"):
        try:
            c = json.loads(f.read_text(encoding="utf-8"))
            found.append((c.get("created", 0), str(f), c))
        except (OSError, ValueError):
            pass
    return min(found)[2] if found else {}


def channel_color():
    return oldest_channel().get("color", "#c00fc9")


def channel_name():
    return oldest_channel().get("name", "CASA NOVA")


def main(argv=None):
    p = argparse.ArgumentParser(prog="studio.py obs", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--only", choices=MODES, help="write just this mode")
    p.add_argument("--keep-old", action="store_true", help='keep the old "Untitled" profile and scene collection')
    p.add_argument("--color", help="accent color of the live screens (default: your first channel's color)")
    args = p.parse_args(argv)
    if obs_running():
        sys.exit("close OBS first: it rewrites its settings when it quits and would undo these")
    if not Path(CAMERA).exists():
        print(f"warning: the DJI Pocket 3 isn't connected ({CAMERA}); the camera shows up once it is")

    backup = OBS / f"backup-{time.strftime('%Y-%m-%d_%H-%M-%S')}"
    if BASIC.is_dir():
        shutil.copytree(BASIC, backup / "basic")
        for name in ("user.ini", "global.ini"):
            if (OBS / name).is_file():
                shutil.copy2(OBS / name, backup / name)
        print("backup:", backup)

    make_assets(args.color or channel_color())
    for mode in [args.only] if args.only else MODES:
        d = BASIC / "profiles" / mode
        d.mkdir(parents=True, exist_ok=True)
        for name, text in profile_files(mode).items():
            (d / name).write_text(text, encoding="utf-8")
        (BASIC / "scenes").mkdir(parents=True, exist_ok=True)
        (BASIC / "scenes" / f"{mode}.json").write_text(json.dumps(collection_json(mode), indent=2), encoding="utf-8")
        desktop_entry(mode)
        print(f"{mode:9} profile + scene collection + app-menu shortcut 'OBS · {mode}'")

    if not args.keep_old and not args.only:
        old = [BASIC / "profiles" / "Untitled", BASIC / "scenes" / "Untitled.json", BASIC / "scenes" / "Untitled.json.bak"]
        for f in old:
            if f.is_dir():
                shutil.rmtree(f)
            elif f.is_file():
                f.unlink()
        print('removed the old "Untitled" profile and scenes (they are in the backup)')
    if not args.only:
        set_user_ini("Gameplay")
    print("open a mode from the app menu (OBS · Gameplay …) or: obs --profile Talk --collection Talk")
