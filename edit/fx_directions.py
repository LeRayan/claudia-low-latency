#!/usr/bin/env python3
"""Trend graphics directions on real frames with her silhouette mask (BiRefNet cut-outs in v2/graphics/fx/).

usage: python3 edit/fx_directions.py  -> v2/graphics/fx-directions.jpg
"""
import math, pathlib
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "v2/graphics/fx"
HN = "/System/Library/Fonts/HelveticaNeue.ttc"
PURPLE, LILAC, WHITE = (155, 29, 190), (200, 87, 239), (255, 255, 255)
CONDB = lambda s: ImageFont.truetype(HN, s, index=9)
MOMENTS = [(9.9, "LATENCY"), (22.2, "TOKEN"), (39.3, "PRUNE"), (105.0, "QUANTIZE"), (118.6, "WASTED"), (142.95, "MORE ME")]


def load(t):
    frame = Image.open(D / f"frame-{t}.png").convert("RGB")
    cut = Image.open(D / f"cut-{t}.png").convert("RGBA")
    return frame, cut.split()[3].point(lambda v: 255 if v > 128 else 0).filter(ImageFilter.GaussianBlur(1))


def fit(text, maxw, maxh, start=900):
    s = start
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    while s > 40:
        bb = d.textbbox((0, 0), text, font=CONDB(s))
        if bb[2] - bb[0] <= maxw and bb[3] - bb[1] <= maxh:
            return CONDB(s), bb
        s -= 10
    return CONDB(s), d.textbbox((0, 0), text, font=CONDB(s))


def text_layer(size, text, color, maxw_frac=0.96, maxh_frac=0.62, y_frac=0.42):
    W, H = size
    f, bb = fit(text, W * maxw_frac, H * maxh_frac)
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).text(((W - (bb[2] - bb[0])) / 2 - bb[0], H * y_frac - (bb[3] - bb[1]) / 2 - bb[1]), text, font=f, fill=255)
    return m


def behind(frame, mask, word):
    """1. Text behind her: a giant word set into the scene, her head and body in front of it."""
    t = text_layer(frame.size, word, WHITE)
    over = Image.composite(Image.new("RGB", frame.size, (250, 246, 255)), frame, t)
    return Image.composite(frame, over, mask)


def sticker(frame, mask, word):
    """2. Cut-out sticker on the hit: background flattens to purple, she pops out with a thick white outline."""
    W, H = frame.size
    bg = Image.new("RGB", frame.size, PURPLE)
    t = text_layer(frame.size, word, WHITE, maxh_frac=0.5, y_frac=0.5)
    bg = Image.composite(Image.new("RGB", frame.size, (120, 20, 150)), bg, t.filter(ImageFilter.GaussianBlur(0)))
    big = mask.filter(ImageFilter.MaxFilter(25))
    out = Image.composite(Image.new("RGB", frame.size, WHITE), bg, big)
    shadow = ImageChops.offset(big, 10, 14).filter(ImageFilter.GaussianBlur(8)).point(lambda v: v // 3)
    out = Image.composite(Image.new("RGB", frame.size, (40, 0, 60)), out, ImageChops.subtract(shadow, big))
    return Image.composite(frame, out, mask)


def fisheye_text(size, word):
    W, H = size
    t = text_layer(size, word, WHITE, maxw_frac=1.25, maxh_frac=0.95, y_frac=0.5)
    # barrel warp: sample from a pinched grid
    src = t.load()
    out = Image.new("L", size, 0)
    dst = out.load()
    cx, cy = W / 2, H / 2
    for y in range(0, H, 2):
        for x in range(0, W, 2):
            nx, ny = (x - cx) / cx, (y - cy) / cy
            r = math.hypot(nx, ny)
            k = 1 + 0.45 * r * r
            sx, sy = int(cx + nx / k * cx), int(cy + ny / k * cy)
            v = src[sx, sy] if 0 <= sx < W and 0 <= sy < H else 0
            dst[x, y] = v
            if x + 1 < W: dst[x + 1, y] = v
            if y + 1 < H: dst[x, y + 1] = v
            if x + 1 < W and y + 1 < H: dst[x + 1, y + 1] = v
    return out


def fisheye(frame, mask, word):
    """3. Fisheye big bold: a huge warped word fills the frame behind her (the CapCut lyric-edit look)."""
    t = fisheye_text(frame.size, word)
    dark = Image.blend(frame, Image.new("RGB", frame.size, (10, 4, 18)), 0.45)
    over = Image.composite(Image.new("RGB", frame.size, LILAC), dark, t)
    return Image.composite(frame, over, mask)


def chrome(frame, mask, word):
    """4. Chrome 3D: a liquid-chrome extruded word behind her, glossy pop-album type."""
    W, H = frame.size
    t = text_layer(frame.size, word, WHITE, maxh_frac=0.55, y_frac=0.4)
    out = frame.copy()
    for i in range(14, 0, -1):  # extrusion
        out = Image.composite(Image.new("RGB", frame.size, (40 + i * 4, 10, 70 + i * 6)), out, ImageChops.offset(t, i, i))
    grad = Image.linear_gradient("L").resize(frame.size)
    bands = grad.point(lambda v: int(128 + 127 * math.sin(v / 255 * math.pi * 5)))
    chrome = Image.merge("RGB", (bands.point(lambda v: min(255, v + 40)), bands, bands.point(lambda v: min(255, v + 60))))
    out = Image.composite(chrome, out, t)
    edge = ImageChops.subtract(t.filter(ImageFilter.MaxFilter(3)), t)
    out = Image.composite(Image.new("RGB", frame.size, WHITE), out, edge)
    return Image.composite(frame, out, mask)


def trace(frame, mask, word):
    """5. Light trace: her silhouette drawn as a glowing purple-white outline, the word small and clean."""
    W, H = frame.size
    edge = ImageChops.subtract(mask.filter(ImageFilter.MaxFilter(9)), mask)
    glow = edge.filter(ImageFilter.GaussianBlur(10))
    out = Image.composite(Image.new("RGB", frame.size, LILAC), frame, glow.point(lambda v: min(255, v * 2)))
    out = Image.composite(Image.new("RGB", frame.size, WHITE), out, edge)
    d = ImageDraw.Draw(out)
    f = CONDB(64)
    w = d.textlength(word, font=f)
    d.text(((W - w) / 2, H * 0.84), word, font=f, fill=WHITE)
    return out


STYLES = [("1  text behind her", behind), ("2  cut-out sticker on the hit", sticker),
          ("3  fisheye big bold", fisheye), ("4  chrome 3D type", chrome), ("5  light trace", trace)]
TW, TH = 448, 256
label = ImageFont.truetype(HN, 26, index=1)
sheet = Image.new("RGB", ((TW + 8) * len(MOMENTS), (TH + 44) * len(STYLES)), (20, 16, 26))
frames = [(load(t), w) for t, w in MOMENTS]
for r, (name, fn) in enumerate(STYLES):
    ImageDraw.Draw(sheet).text((8, r * (TH + 44) + 8), name, font=label, fill=WHITE)
    for c, ((frame, mask), word) in enumerate(frames):
        sheet.paste(fn(frame, mask, word).resize((TW, TH)), (c * (TW + 8), r * (TH + 44) + 40))
out = ROOT / "v2/graphics/fx-directions.jpg"
sheet.save(out, quality=88)
print(out)
