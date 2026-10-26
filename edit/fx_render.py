#!/usr/bin/env python3
"""Hit graphics: key words slammed BEHIND her on the exact hit (v2/audio/hits.json), readable by construction, with a
3-frame zoom punch + RGB split on the picture; a clone stack on chosen big moments.

usage: CLIP_PROJECT=v2 fx_render.py SRC.mp4 ALPHA.mp4 OUT.mp4 [--start 0] [--clones 21.9:23.8,...]
SRC is the picture without graphics, ALPHA her matte (same frames, white = her), --start the song time of frame 0.
Placement rule (anabology's "tuck an edge, never lose a glyph"): over the union of her matte for the word's whole
on-screen time, no glyph is more than 15% hidden; the biggest such word wins, with a small bonus for a real tuck.
"""
import argparse, json, pathlib, subprocess, sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageStat

ROOT = pathlib.Path(__file__).resolve().parent.parent
HN = "/System/Library/Fonts/HelveticaNeue.ttc"
F = lambda s: ImageFont.truetype(HN, max(8, int(s)), index=9)  # Condensed Black
WHITE, PURPLE = (255, 255, 255), (155, 29, 190)
ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("alpha"); ap.add_argument("out")
ap.add_argument("--start", type=float, default=0.0)
ap.add_argument("--clones", default="")
a = ap.parse_args()
FPS = 24
info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                  "stream=width,height:format=duration", "-of", "json", a.src],
                                 capture_output=True, text=True).stdout)
W, H = info["streams"][0]["width"], info["streams"][0]["height"]
N = int(round(float(info["format"]["duration"]) * FPS))
S = 4  # placement works at 1/4 scale


def frames(path, mode, size):
    pix = {"RGB": "rgb24", "L": "gray"}[mode]
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={size[0]}:{size[1]}", "-f", "rawvideo",
                          "-pix_fmt", pix, "-"], stdout=subprocess.PIPE)
    n = size[0] * size[1] * (3 if mode == "RGB" else 1)
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            return
        yield Image.frombytes(mode, size, b)


small = [m.point(lambda v: 255 if v > 128 else 0) for m in frames(a.alpha, "L", (W // S, H // S))]  # placement only
hits = [h for h in json.load(open(ROOT / "v2/audio/hits.json"))
        if a.start <= h["show"] < a.start + N / FPS]
clones = [tuple(map(float, c.split(":"))) for c in a.clones.split(",") if c]


def place(word, union):
    w, h = union.size
    d0 = ImageDraw.Draw(Image.new("L", (1, 1)))
    best = None
    for size in range(int(H * 0.68 / S), int(H * 0.10 / S), -3):
        f = F(size)
        bb = d0.textbbox((0, 0), word, font=f)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        if tw * 1.18 > w * 0.91:  # must still fit at the peak of the slam
            continue
        for yf in (0.14, 0.28, 0.42, 0.56, 0.70):
            for xi in range(21):
                mx, my = w * 0.045 + tw * 0.09, h * 0.06 + th * 0.09  # margins incl. the 18% slam growth
                x, y = mx + xi / 20 * (w - 2 * mx - tw) - bb[0], my + yf * (h - 2 * my - th) - bb[1]
                worst, tot, cx = 0.0, 0.0, x
                for ch in word:
                    g = Image.new("L", (w, h), 0)
                    ImageDraw.Draw(g).text((cx, y), ch, font=f, fill=255)
                    cx += d0.textlength(ch, font=f)
                    area = ImageStat.Stat(g).sum[0]
                    if area == 0:
                        continue
                    hid = ImageStat.Stat(ImageChops.multiply(g, union)).sum[0]
                    worst, tot = max(worst, hid / area), tot + hid
                    if worst > 0.15:
                        break
                if worst <= 0.15:
                    score = size + (4 if tot > 0 else 0)
                    if not best or score > best[0]:
                        best = (score, size * S, x * S, y * S)
        if best and best[1] == size * S:
            break
    return best


CLONE_LAYOUT = ((0.55, -0.33, 0.55), (0.55, 0.33, 0.55), (0.75, -0.19, 0.75), (0.75, 0.19, 0.75))


def with_clones(m):
    """Her matte plus where the clone stack puts copies of it (fully spread), for placement."""
    w, h = m.size
    out = m
    for s, dx, _ in CLONE_LAYOUT:
        c = m.resize((int(w * s), int(h * s)))
        layer = Image.new("L", m.size, 0)
        layer.paste(c, (int(w * (0.5 + dx) - c.width / 2), h - c.height))
        out = ImageChops.lighter(out, layer)
    return out


for h in hits:
    i0, i1 = int((h["show"] - a.start) * FPS), int((h["hide"] - a.start) * FPS)
    cl = any(c0 < h["hide"] and h["show"] < c1 for c0, c1 in clones)
    u = small[max(0, i0)]
    for m in small[max(0, i0):min(len(small), i1 + 1)]:
        u = ImageChops.lighter(u, with_clones(m) if cl else m)
    h["place"] = place(h["word"], u)
    print(h["word"], h["show"], "size", h["place"][1] if h["place"] else None, flush=True)


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def zoom(img, z):
    if z <= 1.001:
        return img
    w, h = int(W * z), int(H * z)
    return img.resize((w, h), Image.BILINEAR).crop(((w - W) // 2, (h - H) // 2, (w - W) // 2 + W, (h - H) // 2 + H))


def frame(i, img, matte):
    t = a.start + i / FPS
    fg = matte  # everything that stands in front of the words: her, and her clones when they are on
    for c0, c1 in clones:  # clone stack: copies of her in depth on a dark stage
        if c0 <= t < c1:
            cut = img.copy(); cut.putalpha(matte)
            out = Image.blend(img, Image.new("RGB", img.size, (14, 6, 24)), 0.75)
            k = ease((t - c0) / 0.25)
            for s, dx, br in CLONE_LAYOUT:
                c = cut.resize((int(W * s), int(H * s)), Image.LANCZOS)
                al = c.split()[3].filter(ImageFilter.GaussianBlur(1.2))
                pos = (int(W * (0.5 + dx * k) - c.width / 2), H - c.height)
                sh = al.filter(ImageFilter.GaussianBlur(10)).point(lambda v, k=k: int(v * 0.6 * k))
                out.paste(Image.new("RGB", c.size, (6, 2, 12)), (pos[0] + 8, pos[1] + 6), sh)   # separation shadow
                dim = Image.blend(c.convert("RGB"), Image.new("RGB", c.size, (14, 6, 24)), 1 - br)
                ak = al.point(lambda v, k=k: int(v * k))
                out.paste(dim, pos, ak)
                layer = Image.new("L", img.size, 0); layer.paste(ak, pos)
                fg = ImageChops.lighter(fg, layer)
            out.paste(cut, (0, 0), cut)
            img = out
    for h in hits:
        if not h["place"] or not (h["show"] <= t < h["hide"]):
            continue
        life, left = t - h["show"], h["hide"] - t
        punch = 1 - ease(life / (3 / FPS))           # 3-frame impact
        img = zoom(img, 1 + 0.06 * punch)
        m = zoom(fg, 1 + 0.06 * punch)
        if punch > 0.05:                              # RGB split, gone by frame 4
            r, g, b = img.split(); o = int(9 * punch)
            img = Image.merge("RGB", (ImageChops.offset(r, o, 0), g, ImageChops.offset(b, -o, 0)))
        _, size, x, y = h["place"]
        sc = 1 + 0.18 * punch                         # the word slams in from 118%
        tl = Image.new("L", img.size, 0)
        f = F(size * sc)
        bb = ImageDraw.Draw(tl).textbbox((0, 0), h["word"], font=F(size))
        cx, cy = x + bb[0] + (bb[2] - bb[0]) / 2, y + bb[1] + (bb[3] - bb[1]) / 2
        bb2 = ImageDraw.Draw(tl).textbbox((0, 0), h["word"], font=f)
        ImageDraw.Draw(tl).text((cx - (bb2[2] - bb2[0]) / 2 - bb2[0], cy - (bb2[3] - bb2[1]) / 2 - bb2[1]),
                                h["word"], font=f, fill=255)
        alpha = min(1.0, left / (3 / FPS))
        tl = tl.point(lambda v: int(v * alpha))
        over = Image.composite(Image.new("RGB", img.size, WHITE), img, tl)
        img = Image.composite(img, over, m)            # she stays in front of the word
    return img


enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                        "-r", str(FPS), "-i", "-", "-ss", str(a.start), "-t", str(N / FPS),
                        "-i", str(ROOT / "v2/audio/LOW-LATENCY-PICK.wav"), "-map", "0:v", "-map", "1:a",
                        "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "256k", "-shortest", a.out], stdin=subprocess.PIPE)
for i, (img, matte) in enumerate(zip(frames(a.src, "RGB", (W, H)), frames(a.alpha, "L", (W, H)))):
    enc.stdin.write(frame(i, img, matte).tobytes())  # soft alpha: thresholding made the jagged edges
enc.stdin.close(); enc.wait()
print(a.out)
