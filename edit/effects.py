#!/usr/bin/env python3
"""v11-B graphics: no HUD, no karaoke. The picture itself undergoes the optimisations she sings about, on her words
(Suno's word alignment), plus a mise en abyme of frames inside frames. Shouted words become giant letters that are
windows onto the video.

usage: CLIP_PROJECT=v2 effects.py <rough cut, no graphics> <out.mp4>
Each effect is an event (start, end, kind, params) with a fast attack and a decay; effects compose over the clean
frame. Frames stream through a small ring buffer: 7 behind (echo trails), 12 ahead (the "speculative" ghost).
"""
import collections, json, math, pathlib, subprocess, sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "edit"))
from project import P, path  # noqa: E402

SRC, DST = sys.argv[1], sys.argv[2]
info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                  "stream=width,height:format=duration", "-of", "json", SRC],
                                 capture_output=True, text=True, check=True).stdout)
W, H = info["streams"][0]["width"], info["streams"][0]["height"]
DUR = float(info["format"]["duration"])
FPS = 24
PURPLE = (155, 29, 190)
LILAC = (200, 87, 239)
BEAT = json.load(open(path("beatmap")))["beat_s"]
SHOTS = json.load(open(path("board")))["shots"]
FACE_X = P.get("face_x", {})
KNOCK = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", 400, index=9)  # Condensed Black
SMALL = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", max(14, int(H * 0.022)), index=10)


def face_center(t):
    s = next((s for s in SHOTS if s["start"] <= t < s["end"]), SHOTS[-1])
    return FACE_X.get(s["id"], 0.5) * W, 0.36 * H


# ---------------------------------------------------------------- the score: (start, end, kind, params)
E = []
add = lambda a, b, kind, **kw: E.append((a, b, kind, kw))
# intro chant: each word a window of letters onto her, with its own optimisation underneath
for a, b, word, kind in [(1.20, 3.0, "PRUNE IT", "prune"), (3.05, 5.15, "DISTILL IT", "droste"),
                         (5.20, 6.99, "FUSE IT", "fuse"), (7.04, 9.30, "SHIP IT", "punch")]:
    add(a, b, "knock", text=word)
    add(a, b, kind, amount=0.35, levels=3, d=60)
add(9.35, 11.0, "knock", text="LOW LATENCY", hold=True)
add(13.10, 14.4, "echo_snap")                           # "Zero wasted time": trails snap to clean
add(16.84, 17.9, "slice")                               # "Cut the weights"
add(21.98, 23.8, "tokens", n=4)                          # "Every token"
add(31.44, 37.77, "droste", levels=3)                    # the giant teacher, nested; gone by "in a day"
add(38.58, 41.81, "prune", amount=0.4)                   # "I pruned the lazy neurons"
add(41.86, 45.08, "prune_return", amount=0.4)           # "lighter on my feet": tiles come back on the beat
add(45.09, 46.08, "fuse", d=70)
add(46.20, 48.67, "fuse", d=70)
add(49.71, 50.6, "wire")                                 # "One kernel"
add(61.14, 62.2, "slice")
add(66.34, 68.0, "tokens", n=5)
add(68.54, 81.30, "beat_prune", amount=0.25)             # the chopped chant: tile masks flip on every beat
add(81.36, 82.98, "fuse", d=80)
add(83.71, 86.57, "echo")                                # "memory warm"
add(86.63, 89.34, "quant", bits=2, block=14)             # "Four bits a weight" ... sharp again on "precise"
add(90.05, 96.34, "ghost")                               # "I guess your next ten words"
add(96.38, 98.30, "fuse", d=70)
add(99.45, 100.6, "fuse", d=70)
add(101.17, 102.5, "wire")
for a, b, word, kind in [(104.68, 105.80, "QUANTIZE", "quant"), (105.86, 106.54, "DISTILL", "droste"),
                         (106.57, 107.97, "PRUNE", "prune"), (108.06, 108.38, "FUSE", "fuse"),
                         (108.40, 109.80, "CACHE", "echo"), (109.90, 114.35, "COMPILE", "wire")]:
    add(a, b, "knock", text=word)
    add(a, b, kind, amount=0.4, levels=3, d=60, bits=2, block=12)
add(121.76, 122.9, "slice")
add(126.74, 128.4, "tokens", n=6)
add(128.56, 141.0, "tunnel")                             # the held "mine": an infinite tunnel of frames
add(141.32, 142.70, "pixel_down")                        # "Less compute"
add(142.74, 143.30, "snap_clean")                        # "More me."
add(146.5, DUR, "credit")


def env(t, a, b, attack=0.06, release=0.18):
    if t < a or t > b + release:
        return 0.0
    if t < a + attack:
        return (t - a) / attack
    if t > b:
        return 1 - (t - b) / release
    return 1.0


# ---------------------------------------------------------------- primitives
def tint(img, color, k):
    return Image.blend(img, Image.new("RGB", img.size, color), k)


def droste(img, levels, z=0.0, scale=0.56, border=True):
    """Paste the frame inside itself, centred, `levels` deep; z in [0,1) slides the nest outward (a tunnel)."""
    out = img.copy()
    d = ImageDraw.Draw(out)
    for k in range(levels, 0, -1):
        s = scale ** (k - z)
        if s >= 0.98:
            continue
        w, h = max(8, int(W * s)), max(5, int(H * s))
        x, y = (W - w) // 2, (H - h) // 2
        out.paste(img.resize((w, h), Image.BILINEAR), (x, y))
        if border:
            d.rectangle((x - 2, y - 2, x + w + 1, y + h + 1), outline=PURPLE, width=max(2, int(4 * s)))
    return out


def tile_mask(seed, amount, t):
    """A grid of tiles switched off (deterministic per seed), never over her face."""
    cols, rows = 24, 14
    tw, th = W / cols, H / rows
    fx, fy = face_center(t)
    m = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(m)
    for r in range(rows):
        for c in range(cols):
            h = math.sin((r * 97 + c * 31 + seed * 13) * 12.9898) * 43758.5453
            if h - math.floor(h) < amount:
                cx, cy = (c + 0.5) * tw, (r + 0.5) * th
                if ((cx - fx) / (0.20 * W)) ** 2 + ((cy - fy) / (0.36 * H)) ** 2 < 1:
                    continue
                d.rectangle((c * tw + 1, r * th + 1, (c + 1) * tw - 1, (r + 1) * th - 1), fill=0)
    return m


def pruned(img, seed, amount, t):
    dark = Image.new("RGB", img.size, (8, 4, 14))
    return Image.composite(img, dark, tile_mask(seed, amount, t))


def fused(img, d):
    a = ImageChops.offset(img, int(d), 0)
    b = ImageChops.offset(img, -int(d), 0)
    return Image.blend(tint(a, LILAC, 0.25), tint(b, (255, 255, 255), 0.15), 0.5)


def quant(img, bits, block):
    small = img.resize((max(1, W // block), max(1, H // block)), Image.NEAREST).resize((W, H), Image.NEAREST)
    return ImageOps.posterize(small, bits)


def wire(img):
    e = img.convert("L").filter(ImageFilter.FIND_EDGES).point(lambda v: 255 if v > 40 else 0)
    e = e.filter(ImageFilter.MaxFilter(3))
    bg = Image.new("RGB", img.size, (6, 2, 12))
    return Image.composite(Image.new("RGB", img.size, LILAC), bg, e)


def sliced(img, k):
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon([(0, 0), (W * 0.62, 0), (W * 0.38, H), (0, H)], fill=255)
    dx = int(36 * k)
    a = ImageChops.offset(img, -dx, -dx // 3)
    b = ImageChops.offset(img, dx, dx // 3)
    out = Image.composite(a, b, mask)
    if k > 0.05:
        ImageDraw.Draw(out).line([(W * 0.62, 0), (W * 0.38, H)], fill=LILAC, width=3)
    return out


def tokens(img, n):
    out = Image.new("RGB", (W, H), (8, 4, 14))
    gw, gh = W / n, H / n
    small = img.resize((int(gw) - 4, int(gh) - 4), Image.BILINEAR)
    for r in range(n):
        for c in range(n):
            out.paste(small, (int(c * gw) + 2, int(r * gh) + 2))
    return out


def knock(img, text, k):
    """Giant letters as windows onto the video; black around them."""
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    size = 400
    while True:
        f = KNOCK.font_variant(size=size)
        box = d.textbbox((0, 0), text, font=f)
        if box[2] - box[0] <= W * 0.92 and box[3] - box[1] <= H * 0.62:
            break
        size -= 10
    x = (W - (box[2] - box[0])) / 2 - box[0]
    y = (H - (box[3] - box[1])) / 2 - box[1]
    d.text((x, y), text, font=f, fill=255)
    dark = Image.new("RGB", (W, H), (6, 2, 12))
    win = Image.composite(img, dark, m)
    edge = m.filter(ImageFilter.MaxFilter(5))  # a thin lilac outline keeps every word legible, even "COMPILE"
    edge = ImageChops.subtract(edge, m)
    win = Image.composite(Image.new("RGB", (W, H), LILAC), win, edge)
    return Image.blend(img, win, k)


# ---------------------------------------------------------------- one frame
def frame(t, cur, past, future):
    img = cur
    knocks = []
    for a, b, kind, kw in E:
        k = env(t, a, b)
        if k <= 0:
            continue
        p = min(1.0, max(0.0, (t - a) / max(0.01, b - a)))  # progress through the event
        if kind == "knock":
            knocks.append((kw["text"], 1.0 if kw.get("hold") or t <= b else k))
        elif kind == "prune":
            img = Image.blend(img, pruned(img, int(a * 10), kw["amount"], t), k)
        elif kind == "prune_return":
            beats = int((t - a) / BEAT)
            amt = kw["amount"] * max(0.0, 1 - beats / 7)
            img = pruned(img, int(a * 10), amt, t)
        elif kind == "beat_prune":
            beat = int((t - a) / BEAT)
            img = Image.blend(img, pruned(img, beat, kw["amount"], t), k)
        elif kind == "droste":
            img = Image.blend(img, droste(img, kw.get("levels", 3)), k)
        elif kind == "fuse":
            img = Image.blend(img, fused(img, kw["d"] * (1 - p) ** 2), k)
        elif kind == "punch":
            z = 1 + 0.12 * (1 - p)
            w, h = int(W * z), int(H * z)
            img = Image.blend(img, img.resize((w, h), Image.BILINEAR).crop(((w - W) // 2, (h - H) // 2, (w - W) // 2 + W, (h - H) // 2 + H)), k)
        elif kind == "slice":
            img = sliced(img, k * (1 - p) ** 0.5)
        elif kind == "tokens":
            img = Image.blend(img, tokens(img, kw["n"]), k * (1 if p < 0.7 else (1 - p) / 0.3))
        elif kind in ("echo", "echo_snap"):
            amt = k * (1 - p if kind == "echo_snap" else 1)
            if len(past) >= 6:
                trail = Image.blend(past[-3], past[-6], 0.5)
                img = Image.blend(img, tint(trail, PURPLE, 0.15), 0.45 * amt)
        elif kind == "quant":
            img = Image.blend(img, quant(img, kw["bits"], kw["block"]), k)
        elif kind == "ghost":
            if future:
                img = Image.blend(img, tint(future[-1], LILAC, 0.2), 0.32 * k)
        elif kind == "wire":
            img = Image.blend(img, wire(img), k * (1 - 0.5 * p))
        elif kind == "tunnel":
            depth = 1 + 5 * p                                   # deeper as the note holds
            z = (t - a) * 0.35 % 1.0                            # the nest slides outward forever
            img = Image.blend(img, droste(img, int(depth) + 1, z=z), min(1.0, 0.35 + 0.65 * p) * k)
        elif kind == "pixel_down":
            block = int(2 + 46 * p)
            img = quant(img, 8, block)
        elif kind == "snap_clean":
            pass
        elif kind == "credit":
            img = img.copy()
            d = ImageDraw.Draw(img)
            txt = "LOW LATENCY   ·   Claudia by anabology   ·   made with Pruna"
            w = d.textlength(txt, font=SMALL)
            d.text(((W - w) / 2, H * 0.92), txt, font=SMALL, fill=(255, 255, 255, int(255 * k)))
    for text, k in knocks:
        img = knock(img, text, k)
    return img


# ---------------------------------------------------------------- stream
n = int(round(DUR * FPS))
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                        "-r", str(FPS), "-i", "-", "-i", SRC, "-map", "0:v", "-map", "1:a", "-c:v", "libx264",
                        "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", DST],
                       stdin=subprocess.PIPE)
size = W * H * 3


def read():
    b = dec.stdout.read(size)
    return Image.frombytes("RGB", (W, H), b) if len(b) == size else None


AHEAD = 12
ahead = collections.deque()
past = collections.deque(maxlen=7)
while len(ahead) <= AHEAD:
    f = read()
    if f is None:
        break
    ahead.append(f)
i = 0
while ahead:
    cur = ahead.popleft()
    nxt = read()
    if nxt is not None:
        ahead.append(nxt)
    enc.stdin.write(frame(i / FPS, cur, list(past), list(ahead)).tobytes())
    past.append(cur)
    i += 1
enc.stdin.close()
enc.wait()
print(DST, i, "frames")
