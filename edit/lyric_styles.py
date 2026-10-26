#!/usr/bin/env python3
"""Lyric/graphics directions for LOW LATENCY, drawn on stills so Rayan can pick before a full render.

usage: CLIP_PROJECT=v2 lyric_styles.py <rough cut without graphics> <out.jpg>
Each style draws one moment: (line text, index of the word being sung, which side her face is on). Less is more.
"""
import json, pathlib, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC, OUT = sys.argv[1], sys.argv[2]
SUP = "/System/Library/Fonts/Supplemental/"
PURPLE, LILAC, WHITE = (155, 29, 190), (200, 87, 239), (255, 255, 255)
F = lambda path, size, i=0: ImageFont.truetype(path, size, index=i)
HN = "/System/Library/Fonts/HelveticaNeue.ttc"

# moments: time, line, sung word index, face side ("left"/"right"/"center"), section title
MOMENTS = [(9.95, "Low latency, baby", 1, "left", "I — LOW LATENCY"),
           (39.3, "I pruned the lazy neurons that were only there for show", 3, "left", "II — PRUNE"),
           (104.9, "Quantize! Distill! Prune! Fuse! Cache! Compile!", 0, "left", "IV — COMPILE"),
           (142.9, "Less compute. More me.", 2, "center", "")]


def grab(t):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", SRC, "-frames:v", "1", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return Image.frombytes("RGB", (1344, 768), raw)


def shadowed(img, layer, blur=6, strength=0.6):
    a = layer.split()[3].filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * strength))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sh.putalpha(a)
    return Image.alpha_composite(Image.alpha_composite(img.convert("RGBA"), sh), layer).convert("RGB")


def couture(img, line, cur, side, title):
    """A. Couture serif: the line in big Didot on the side away from her face; the sung word in italic."""
    W, H = img.size
    L = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    reg, ita = F(SUP + "Didot.ttc", 58, 0), F(SUP + "Didot.ttc", 58, 1)
    words = line.split()
    x0 = W * 0.56 if side == "left" else W * 0.06
    if side == "center":
        x0 = W * 0.06
    maxw = W * 0.38
    rows, row = [], []
    for i, w in enumerate(words):
        trial = " ".join(words[j] for j in row + [i])
        if row and d.textlength(trial, font=reg) > maxw:
            rows.append(row)
            row = []
        row.append(i)
    rows.append(row)
    y = H * 0.5 - len(rows) * 34
    for r in rows:
        x = x0
        for i in r:
            f = ita if i == cur else reg
            d.text((x, y), words[i] + " ", font=f, fill=WHITE + ((255,) if i <= cur else (150,)))
            x += d.textlength(words[i] + " ", font=f)
        y += 68
    if title:
        d.text((x0, H * 0.5 - len(rows) * 34 - 40), title, font=F(SUP + "Didot.ttc", 18), fill=LILAC + (255,))
    grad = Image.new("L", img.size, 0)
    gd = ImageDraw.Draw(grad)
    for i in range(int(W * 0.5)):
        a = int(150 * (i / (W * 0.5)))
        xx = W - 1 - i if x0 > W * 0.3 else i
        gd.line((xx, 0, xx, H), fill=a if x0 > W * 0.3 else 150 - a)
    img = Image.composite(Image.new("RGB", img.size, (8, 4, 14)), img, grad)
    return shadowed(img, L)


def swiss(img, line, cur, side, title):
    """B. Swiss minimal: one small tracked line, bottom centre; a purple hairline grows under it as it's sung."""
    W, H = img.size
    L = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    f = F(HN, 26, 10)
    text = line.upper()
    track = 3
    w = sum(d.textlength(c, font=f) + track for c in text)
    x, y = (W - w) / 2, H * 0.86
    x_start = x
    for c in text:
        d.text((x, y), c, font=f, fill=WHITE + (255,))
        x += d.textlength(c, font=f) + track
    frac = (cur + 1) / len(line.split())
    d.line((x_start, y + 40, x_start + w * frac, y + 40), fill=PURPLE + (255,), width=3)
    return shadowed(img, L, blur=4, strength=0.5)


def oneword(img, line, cur, side, title):
    """C. One word, huge: only the sung word, giant condensed caps in the negative space beside her."""
    W, H = img.size
    L = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    word = line.split()[cur].strip(",.!").upper()
    size = 260
    while True:
        f = F(HN, size, 9)
        bb = d.textbbox((0, 0), word, font=f)
        if bb[2] - bb[0] <= W * 0.42 or size < 60:
            break
        size -= 8
    x = W * 0.54 if side == "left" else W * 0.04
    if side == "center":
        x = (W - (bb[2] - bb[0])) / 2
    y = H * 0.5 - (bb[3] - bb[1]) / 2 - bb[1]
    if side == "center":  # never over her face: under it, at the bottom
        y = H * 0.80 - (bb[3] - bb[1]) / 2 - bb[1]
    d.text((x, y), word, font=f, fill=WHITE + (235,))
    return shadowed(img, L, blur=10, strength=0.5)


def poster(img, line, cur, side, title):
    """D. Vertical poster: the line set vertically up the far edge in condensed caps, a tiny title block opposite."""
    W, H = img.size
    L = Image.new("RGBA", (H, W), (0, 0, 0, 0))  # drawn rotated
    d = ImageDraw.Draw(L)
    f = F(SUP + "DIN Condensed Bold.ttf", 54)
    words = line.upper().split()
    x = 40
    for i, w in enumerate(words):
        d.text((x, 20), w + " ", font=f, fill=(WHITE if i <= cur else (255, 255, 255)) + ((255,) if i <= cur else (110,)))
        x += d.textlength(w + " ", font=f)
    L = L.rotate(90, expand=True)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    edge_x = W - 110 if side != "right" else 20
    layer.paste(L, (edge_x, 0), L)
    d2 = ImageDraw.Draw(layer)
    small = F(SUP + "DIN Condensed Bold.ttf", 22)
    bx = 40 if side != "left" else W * 0.62
    d2.text((bx, H - 70), "LOW LATENCY", font=small, fill=WHITE + (255,))
    d2.text((bx, H - 44), "CLAUDIA · PRUNA", font=small, fill=LILAC + (255,))
    return shadowed(img, layer, blur=5, strength=0.5)


def neon(img, line, cur, side, title):
    """E. Stage light: outline letters with a purple glow, like light rigged on the set, only the hook or key word."""
    W, H = img.size
    word = line.split()[cur].strip(",.!").upper()
    m = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(m)
    size = 150
    while True:
        f = F(SUP + "Futura.ttc", size, 2)
        bb = d.textbbox((0, 0), word, font=f, stroke_width=3)
        if bb[2] - bb[0] <= W * (0.8 if side == "center" else 0.4) or size < 50:
            break
        size -= 6
    x = W * 0.55 if side == "left" else W * 0.05
    if side == "center":
        x = (W - (bb[2] - bb[0])) / 2
    y = H * 0.12
    d.text((x, y), word, font=f, fill=0, stroke_width=3, stroke_fill=255)
    glow = m.filter(ImageFilter.GaussianBlur(14))
    out = Image.composite(Image.new("RGB", img.size, LILAC), img, glow.point(lambda v: int(v * 0.8)))
    return Image.composite(Image.new("RGB", img.size, (245, 225, 255)), out, m)


STYLES = [("A  couture serif", couture), ("B  swiss minimal", swiss), ("C  one word, huge", oneword),
          ("D  vertical poster", poster), ("E  stage-light outline", neon)]
frames = [grab(t) for t, *_ in MOMENTS]
TW, TH = 560, 320
label = F(HN, 26, 1)
sheet = Image.new("RGB", (TW * len(MOMENTS) + 10 * len(MOMENTS), (TH + 46) * len(STYLES)), (20, 16, 26))
for r, (name, fn) in enumerate(STYLES):
    ImageDraw.Draw(sheet).text((8, r * (TH + 46) + 8), name, font=label, fill=WHITE)
    for c, ((t, line, cur, side, title), fr) in enumerate(zip(MOMENTS, frames)):
        sheet.paste(fn(fr, line, cur, side, title).resize((TW, TH)), (c * (TW + 10), r * (TH + 46) + 40))
sheet.save(OUT, quality=88)
print(OUT)
