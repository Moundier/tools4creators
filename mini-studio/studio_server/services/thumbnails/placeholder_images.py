"""Placeholder test images: a colorful background, a cartoon person cutout and a fake game logo."""
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ...paths import FONTS


def make_background(path):
    w, h = 1920, 1080
    img = Image.new("RGB", (w, h))
    px = img.load()
    # diagonal teal -> purple -> orange gradient
    rgb1 = (20, 160, 190)
    rgb2 = (110, 40, 170)
    rgb3 = (250, 120, 40)
    stops = [(0.0, rgb1), (0.5, rgb2), (1.0, rgb3)]
    for y in range(h):
        for x in range(w):
            t = (x / w * 0.7 + y / h * 0.3)
            for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
                if t0 <= t <= t1:
                    k = (t - t0) / (t1 - t0)
                    px[x, y] = tuple(int(a + (b - a) * k) for a, b in zip(c0, c1))
                    break
    # soft glowing circles for some "scene" texture
    rnd = random.Random(7)
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    for _ in range(18):
        r = rnd.randint(60, 260)
        cx, cy = rnd.randint(0, w), rnd.randint(0, h)
        col = rnd.choice([(255, 255, 255), (255, 220, 120), (120, 240, 255)])
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col + (rnd.randint(25, 70),))
    glow = glow.filter(ImageFilter.GaussianBlur(40))
    img = Image.alpha_composite(img.convert("RGBA"), glow)
    # a bright "subject" in the upper right for arrows/circles to point at
    subj = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(subj).regular_polygon((1450, 380, 170), 6, rotation=15,
                                         fill=(255, 210, 60, 255), outline=(255, 255, 255, 255), width=12)
    img = Image.alpha_composite(img, subj)
    img.convert("RGB").save(path, quality=92)


def make_person(path):
    w, h = 900, 1200
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    skin, shirt, hair = (232, 180, 140, 255), (40, 90, 200, 255), (60, 40, 30, 255)
    # shoulders / torso
    d.rounded_rectangle([70, 760, 830, 1400], radius=260, fill=shirt)
    # neck
    d.rectangle([370, 600, 530, 820], fill=(215, 160, 120, 255))
    # head + hair
    d.ellipse([240, 170, 660, 680], fill=skin)
    d.chord([230, 130, 670, 520], 180, 360, fill=hair)
    # face: surprised expression (works for thumbnails!)
    for ex in (360, 540):
        d.ellipse([ex - 32, 380, ex + 32, 444], fill=(255, 255, 255, 255))
        d.ellipse([ex - 15, 397, ex + 15, 427], fill=(30, 30, 30, 255))
    d.arc([320, 330, 400, 370], 200, 340, fill=hair, width=10)
    d.arc([500, 330, 580, 370], 200, 340, fill=hair, width=10)
    d.ellipse([410, 520, 490, 610], fill=(120, 30, 40, 255))
    # V-neck
    d.polygon([(370, 800), (530, 800), (450, 920)], fill=(215, 160, 120, 255))
    img.save(path)


def make_art(path):
    """Transparent 'game logo' title image, stands in for --art (e.g. a game or company logo)."""
    w, h = 900, 300
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(FONTS / "Anton-Regular.ttf"), 210)
    for off in range(16, 0, -2):  # thick dark-blue extrusion/outline
        d.text((w // 2 + off // 3, h // 2 + off // 3), "GAME", font=font, anchor="mm",
               fill=(10, 40, 130, 255), stroke_width=off, stroke_fill=(10, 40, 130, 255))
    d.text((w // 2, h // 2), "GAME", font=font, anchor="mm", fill=(255, 205, 0, 255))
    img.crop(img.getbbox()).save(path)



def make_art2(path):
    """Transparent round badge, stands in for --art2 (e.g. a console or platform logo)."""
    s = 600
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([10, 10, s - 10, s - 10], fill=(255, 255, 255, 255))
    d.ellipse([70, 70, s - 70, s - 70], fill=(30, 30, 30, 255))
    font = ImageFont.truetype(str(FONTS / "Anton-Regular.ttf"), 300)
    d.text((s // 2, s // 2), "2", font=font, anchor="mm", fill=(255, 255, 255, 255))
    img.save(path)
