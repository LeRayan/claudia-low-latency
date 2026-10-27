#!/usr/bin/env python3
"""Lyric lockups: every sung line as a typographic block BEHIND her, built word by word on the measured word clock.

usage: CLIP_PROJECT=v2 .venv-align/bin/python edit/lockups.py SRC.mp4 ALPHA.mp4 OUT.mp4 [--start 0] [--clones 21.9:23.8,...] [--sheet]
       any song: ... --clock words.json --spec lockups.json --soundtrack song.wav [--beatmap none]
- v2/lockups.json says how each line is set: CAPS rows (Helvetica Condensed Black) justified to one block width,
  ~italic rows (Baskerville SemiBold Italic) for filler words. Hooks are big and punch the picture on key words;
  verses are smaller and quiet. The chopped chant shows nothing.
- Each word appears 1 frame before its attack (v2/audio/word_clock.json, 16th-grid snap within 30 ms); a group holds
  until the next group starts (or 0.6 s past its last word, 1.6 s at most).
- Placement: "tuck an edge, never lose a glyph": over the union of her matte (and clones) for the group's whole time,
  no glyph is more than 15% hidden; the widest block that fits wins. If nothing fits, the block goes in front of her.
--sheet: also writes OUT.png, one frame per group with its last word in, for checking.
"""
import argparse, json, pathlib, re, subprocess
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
_HN, _BK = "/System/Library/Fonts/HelveticaNeue.ttc", "/System/Library/Fonts/Supplemental/Baskerville.ttc"
_FONTS = ROOT / "assets/fonts"  # open (OFL) stand-ins where the macOS fonts the film used don't exist


def CAPS(s):
    if pathlib.Path(_HN).exists():
        return ImageFont.truetype(_HN, max(6, int(s)), index=9)  # Helvetica Neue Condensed Black
    return ImageFont.truetype(str(_FONTS / "Anton-Regular.ttf"), max(6, int(s)))


def ITAL(s):
    if pathlib.Path(_BK).exists():
        return ImageFont.truetype(_BK, max(6, int(s)), index=5)  # Baskerville SemiBold Italic
    f = ImageFont.truetype(str(_FONTS / "LibreBaskerville-Italic.ttf"), max(6, int(s)))
    f.set_variation_by_name(b"SemiBold Italic")
    return f


KEY = {"LATENCY", "ZERO", "WASTED", "CUT", "WEIGHTS", "SHINE", "TOKEN", "MINE", "FUSE", "KERNEL", "PRUNE", "DISTILL",
       "SHIP", "QUANTIZE", "CACHE", "COMPILE", "LESS", "COMPUTE", "MORE", "ME"}
FPS = 24
norm = lambda w: re.sub(r"[^A-Z]", "", w.upper())

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("alpha"); ap.add_argument("out")
ap.add_argument("--start", type=float, default=0.0)
ap.add_argument("--clones", default="")
ap.add_argument("--sheet", action="store_true")
ap.add_argument("--clock", default=str(ROOT / "v2/audio/word_clock.json"), help='{"words": [{word, t, end}]}')
ap.add_argument("--spec", default=str(ROOT / "v2/lockups.json"))
ap.add_argument("--beatmap", default=str(ROOT / "v2/beatmap.json"), help="'none': no grid snap")
ap.add_argument("--soundtrack", default=str(ROOT / "v2/audio/LOW-LATENCY-PICK.wav"))
a = ap.parse_args()
info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                  "stream=width,height:format=duration", "-of", "json", a.src],
                                 capture_output=True, text=True).stdout)
W, H = info["streams"][0]["width"], info["streams"][0]["height"]
N = int(round(float(info["format"]["duration"]) * FPS))
S = 2  # placement at 1/2 scale


# ---------------------------------------------------------------- groups on the word clock
clock = json.load(open(a.clock))["words"]
bm = None if a.beatmap == "none" else json.load(open(a.beatmap))


def show_time(t):
    if not bm:
        return t - 1 / FPS
    six = bm["beat_s"] / 4
    g = bm["first_downbeat"] + round((t - bm["first_downbeat"]) / six) * six
    return (g if abs(g - t) <= 0.03 else t) - 1 / FPS


groups, wi = [], 0
for g in json.load(open(a.spec))["groups"]:
    if g["k"] == "skip":
        wi += g["n"]
        continue
    rows = []
    for r in g["rows"]:
        ital = r.startswith("~")
        toks = r.lstrip("~").split()
        ws = []
        for tok in toks:
            c = clock[wi]
            assert norm(c["word"]) == norm(tok), (tok, c["word"], c["t"])
            first_caps = not ital and not any(not w["ital"] for w in rows) and not ws
            ws.append({"text": tok, "show": show_time(c["t"]), "end": c["end"],  # "punch": true = first CAPS word
                       "punch": g["k"] == "hook" and not ital and (norm(tok) in KEY or (g.get("punch") and first_caps))})
            wi += 1
        rows.append({"ital": ital, "words": ws})
    allw = [w for r in rows for w in r["words"]]
    groups.append({"k": g["k"], "rows": rows, "start": min(w["show"] for w in allw),
                   "last": max(w["show"] for w in allw), "end_sung": max(w["end"] for w in allw)})
assert wi == len(clock), (wi, len(clock))
for k, g in enumerate(groups):
    nxt = groups[k + 1]["start"] if k + 1 < len(groups) else g["last"] + 3
    g["stop"] = min(nxt - 0.02, g["last"] + 1.6, max(g["end_sung"] + 0.6, g["last"] + 0.7))  # long holds shrank the type
groups = [g for g in groups if g["stop"] > a.start and g["start"] < a.start + N / FPS]


# ---------------------------------------------------------------- layout
def layout(g, bw):
    """Words with font, size and baseline position inside a block bw wide; returns (words, block height)."""
    caps_sizes = []
    for r in g["rows"]:
        if not r["ital"]:
            txt = " ".join(w["text"] for w in r["words"])
            caps_sizes.append(100 * bw / CAPS(100).getlength(txt))
    ref = min(caps_sizes) if caps_sizes else 100 * bw / 400
    gap = 0.13 * ref * 0.72
    y, out, ci = 0.0, [], 0
    for r in g["rows"]:
        txt = " ".join(w["text"] for w in r["words"])
        if r["ital"]:
            size = ref * 0.78
            size = min(size, size * bw / ITAL(size).getlength(txt))
            f = ITAL(size)
            asc, desc = -f.getbbox("lkdf", anchor="ls")[1], f.getbbox("gpy", anchor="ls")[3]
            base = y + asc
            y = base + desc + gap * 0.5
        else:
            size = caps_sizes[ci]; ci += 1
            f = CAPS(size)
            base = y + -f.getbbox("H", anchor="ls")[1]
            y = base + gap
        x = 0.0
        for w in r["words"]:
            out.append({**w, "ital": r["ital"], "size": size, "x": x, "base": base})
            x += f.getlength(w["text"] + " ")
    return out, y - gap


_gm = {}


def glyph(ch, ital, size):
    """Ink mask of one glyph (at 1/S scale) and its offset from the pen position on the baseline."""
    k = (ch, ital, int(size))
    if k not in _gm:
        f = (ITAL if ital else CAPS)(size)
        bb = f.getbbox(ch, anchor="ls")
        im = Image.new("L", (max(1, bb[2] - bb[0]), max(1, bb[3] - bb[1])), 0)
        ImageDraw.Draw(im).text((-bb[0], -bb[1]), ch, font=f, fill=255, anchor="ls")
        _gm[k] = (np.asarray(im) > 127, bb[0], bb[1])
    return _gm[k]


def place(g, union, lim=0.15):
    """Largest block whose every glyph stays >= (1 - lim) visible over `union` (bool, 1/S scale); None if none."""
    h, w = union.shape
    hook = g["k"] == "hook"
    bw = W * (0.86 if hook else 0.50)
    while bw >= W * (0.15 if hook else 0.17):  # a narrow block in a free strip beats covering her
        words, bh = layout(g, bw / S)
        bws, bhs = bw / S, bh
        if bhs <= h * 0.84:
            glyphs = []
            for wd in words:
                f = (ITAL if wd["ital"] else CAPS)(wd["size"])
                px = wd["x"]
                for ch in wd["text"]:
                    if ch.strip():
                        m, ox, oy = glyph(ch, wd["ital"], wd["size"])
                        glyphs.append((m, int(px + ox), int(wd["base"] + oy), m.sum()))
                    px += f.getlength(ch)
            mx, my = w * 0.03 + bws * 0.06, h * 0.05 + bhs * 0.06
            best = None
            for yi in range(9):
                for xi in range(17):
                    X = int(mx + xi / 16 * max(0, w - 2 * mx - bws))
                    Y = int(my + yi / 8 * max(0, h - 2 * my - bhs))
                    worst, tot = 0.0, 0
                    for m, gx, gy, area in glyphs:
                        x0, y0 = X + gx, Y + gy
                        if area == 0 or x0 < 0 or y0 < 0 or x0 + m.shape[1] > w or y0 + m.shape[0] > h:
                            worst = 1.0 if area else worst
                            break
                        hid = int((union[y0:y0 + m.shape[0], x0:x0 + m.shape[1]] & m).sum())
                        worst, tot = max(worst, hid / area), tot + hid
                        if worst > lim:
                            break
                    if worst <= lim:
                        sc = tot + (abs(X + bws / 2 - w / 2) * 0.01)  # prefer a real tuck, then the frame's edge
                        if not best or sc > best[0]:
                            best = (sc, X * S, Y * S)
            if best:
                return {"bw": bw, "x": best[1], "y": best[2], "front": False}
        bw *= 0.93
    return None


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


CLONE_LAYOUT = ((0.55, -0.33, 0.55), (0.55, 0.33, 0.55), (0.75, -0.19, 0.75), (0.75, 0.19, 0.75))
clones = [tuple(map(float, c.split(":"))) for c in a.clones.split(",") if c]


def with_clones(m):
    h, w = m.shape
    out = m.copy()
    im = Image.fromarray(m.astype(np.uint8) * 255)
    for s, dx, _ in CLONE_LAYOUT:
        c = np.asarray(im.resize((int(w * s), int(h * s)))) > 127
        x0 = int(w * (0.5 + dx) - c.shape[1] / 2)
        xa, xb = max(0, x0), min(w, x0 + c.shape[1])
        out[h - c.shape[0]:, xa:xb] |= c[:, xa - x0:xb - x0]
    return out


small = [np.asarray(m) > 128 for m in frames(a.alpha, "L", (W // S, H // S))]
for g in groups:
    i0, i1 = max(0, int((g["start"] - a.start) * FPS)), min(len(small), int((g["stop"] - a.start) * FPS) + 1)
    cl = any(c0 < g["stop"] and g["start"] < c1 for c0, c1 in clones)
    u = np.zeros_like(small[0])
    for m in small[i0:i1]:
        u |= with_clones(m) if cl else m
    g["place"] = place(g, u) or place(g, u, 0.30)  # a deeper tuck before ever covering her
    if not g["place"]:  # nothing fits behind her: in front of her, where it covers the least of her
        bw = W * (0.34 if g["k"] == "hook" else 0.30)
        bh = layout(g, bw)[1]
        uu = np.asarray(Image.fromarray(u.astype(np.uint8)).resize((W, H)))
        cands = [(uu[int(y):int(y + bh), int(x):int(x + bw)].sum(), x, y)
                 for x in (W * 0.04, W * 0.96 - bw) for y in (H * 0.08, H * 0.92 - bh)]
        _, x, y = min(cands)
        g["place"] = {"bw": bw, "x": x, "y": y, "front": True}
    g["words"], _ = layout(g, g["place"]["bw"])
    txt = " / ".join(" ".join(w["text"] for w in r["words"]) for r in g["rows"])
    print(f"{g['start']:7.2f}-{g['stop']:6.2f} {g['k']:5} bw {g['place']['bw'] / W:.2f}"
          f"{' FRONT' if g['place']['front'] else ''}  {txt}", flush=True)


# ---------------------------------------------------------------- render
def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def zoom(img, z):
    if z <= 1.001:
        return img
    w, h = int(W * z), int(H * z)
    return img.resize((w, h), Image.BILINEAR).crop(((w - W) // 2, (h - H) // 2, (w - W) // 2 + W, (h - H) // 2 + H))


def text_layer(g, t):
    """The group's words sung so far, as an L mask; returns (mask, strongest punch now)."""
    L = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(L)
    fade = min(1.0, (g["stop"] - t) / (3 / FPS))
    punch = 0.0
    for wd in g["words"]:
        age = t - wd["show"]
        if age < 0:
            continue
        hook = g["k"] == "hook" and not wd["ital"]
        n = 3 if hook else 2
        p = 1 - ease(age / (n / FPS))
        sc = 1 + (0.12 if hook else 0.06) * p
        al = fade * (1.0 if hook else min(1.0, 0.35 + age / (n / FPS)))
        f0 = (ITAL if wd["ital"] else CAPS)(wd["size"])
        f = (ITAL if wd["ital"] else CAPS)(wd["size"] * sc)
        capH = -f0.getbbox("H", anchor="ls")[1]
        cx = g["place"]["x"] + wd["x"] + f0.getlength(wd["text"]) / 2
        cy = g["place"]["y"] + wd["base"] - capH / 2
        d.text((cx - f.getlength(wd["text"]) / 2, cy + capH * sc / 2), wd["text"], font=f,
               fill=int(255 * al), anchor="ls")
        if wd["punch"]:
            punch = max(punch, p)
    return L, punch


def frame(i, img, matte):
    t = a.start + i / FPS
    fg = matte
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
                out.paste(Image.new("RGB", c.size, (6, 2, 12)), (pos[0] + 8, pos[1] + 6), sh)
                dim = Image.blend(c.convert("RGB"), Image.new("RGB", c.size, (14, 6, 24)), 1 - br)
                ak = al.point(lambda v, k=k: int(v * k))
                out.paste(dim, pos, ak)
                layer = Image.new("L", img.size, 0); layer.paste(ak, pos)
                fg = ImageChops.lighter(fg, layer)
            out.paste(cut, (0, 0), cut)
            img = out
    for g in groups:
        if not (g["start"] <= t < g["stop"]):
            continue
        L, punch = text_layer(g, t)
        if punch > 0:
            img = zoom(img, 1 + 0.05 * punch)
            fg = zoom(fg, 1 + 0.05 * punch)
            if punch > 0.05:
                r, gg, b = img.split(); o = int(8 * punch)
                img = Image.merge("RGB", (ImageChops.offset(r, o, 0), gg, ImageChops.offset(b, -o, 0)))
        sh = L.filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * 0.45))
        over = Image.composite(Image.new("RGB", img.size, (8, 2, 16)), img, sh)   # soft shadow for bright stages
        over = Image.composite(Image.new("RGB", img.size, (255, 255, 255)), over, L)
        img = over if g["place"]["front"] else Image.composite(img, over, fg)   # she stays in front of the words
    return img


enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                        "-r", str(FPS), "-i", "-", "-ss", str(a.start), "-t", str(N / FPS),
                        "-i", a.soundtrack, "-map", "0:v", "-map", "1:a",
                        "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "256k", "-frames:v", str(N), a.out], stdin=subprocess.PIPE)
want = {int((g["last"] + 0.2 - a.start) * FPS): g for g in groups}
shots = []
for i, (img, matte) in enumerate(zip(frames(a.src, "RGB", (W, H)), frames(a.alpha, "L", (W, H)))):
    fr = frame(i, img, matte)
    enc.stdin.write(fr.tobytes())  # soft alpha: thresholding made the jagged edges
    if a.sheet and i in want:
        shots.append(fr.resize((W // 3, H // 3)))
enc.stdin.close(); enc.wait()
if shots:
    cols = 5
    sheet = Image.new("RGB", (cols * (W // 3), -(-len(shots) // cols) * (H // 3)))
    for k, s in enumerate(shots):
        sheet.paste(s, ((k % cols) * (W // 3), (k // cols) * (H // 3)))
    sheet.save(str(pathlib.Path(a.out).with_suffix(".png")))
print(a.out)
