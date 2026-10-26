#!/usr/bin/env python3
"""Lyric graphics C+B (Rayan's pick): sung choruses, chants and the bridge show ONE word, huge, in the negative space
beside her (C); verses show one small tracked line at the bottom with a purple hairline growing as it is sung (B).
Long held notes and unreadable chops show nothing. No HUD.

usage: CLIP_PROJECT=v2star lyrics_cb.py <rough cut> <out.mp4>
Timing: Suno's word alignment (start/end per word) and the board's sections.
"""
import json, math, pathlib, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "edit"))
from project import P, path  # noqa: E402

SRC, DST = sys.argv[1], sys.argv[2]
VERSES_ONLY = "--verses-only" in sys.argv  # the hit words come from edit/fx_render.py; keep only B lines + end card
CARD_ONLY = "--card-only" in sys.argv  # all lyrics come from edit/lockups.py; only the end card here
info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                  "stream=width,height:format=duration", "-of", "json", SRC],
                                 capture_output=True, text=True, check=True).stdout)
W, H = info["streams"][0]["width"], info["streams"][0]["height"]
DUR = float(info["format"]["duration"])
FPS, K = 24, min(H / 768, W / 640)
PORTRAIT = H > W
PURPLE, WHITE = (155, 29, 190), (255, 255, 255)
HN = "/System/Library/Fonts/HelveticaNeue.ttc"
BIG = lambda s: ImageFont.truetype(HN, s, index=9)  # Condensed Black
SMALL = ImageFont.truetype(HN, int(24 * K), index=10)  # Medium

shots = json.load(open(path("board")))["shots"]
words = [(c["timestamp"][0], c["timestamp"][1], c["text"].strip()) for c in
         json.load(open(ROOT / "v2/audio/suno_aligned.words.json"))["chunks"]]
lines = [tuple(l) for l in P["lines"]]
VERSE = {"verse 1", "verse 2"}
HELD = 3.0  # a word held longer than this is a long note: the word fades after 1.5 s
FACE_X = P.get("face_x", {})


def shot_at(t):
    return next((s for s in shots if s["start"] <= t < s["end"]), shots[-1])


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


KEY = {"LATENCY", "ZERO", "WASTED", "CUT", "SHINE", "TOKEN", "MINE", "FUSE", "KERNEL", "PRUNE", "DISTILL", "SHIP",
       "FASTER", "QUANTIZE", "CACHE", "COMPILE", "LESS", "COMPUTE", "MORE", "ME"}
CARD = 145.4  # after "More me." and the smile settles: a quiet end title over the last shot


def end_card(d, t):
    if t < CARD:
        return
    a = ease((t - CARD) / 0.8)
    title, sub = "LOW LATENCY", "Claudia by anabology  ·  made with Pruna"
    f1, f2 = BIG(int(54 * K)), SMALL
    w1, w2 = d.textlength(title, font=f1), d.textlength(sub, font=f2)
    y = H * (0.80 if PORTRAIT else 0.83)
    d.text(((W - w1) / 2, y), title, font=f1, fill=WHITE + (int(235 * a),))
    d.text(((W - w2) / 2, y + 66 * K), sub, font=f2, fill=WHITE + (int(200 * a),))


def big_word(d, t):
    """C: the current sung word, giant, away from her face."""
    w = next(((a, b, txt) for a, b, txt in words if a <= t < max(b, a + 0.35)), None)
    if not w:
        return
    a, b, txt = w
    if not any(l[0] <= a < l[1] for l in lines):  # unreadable stretch: nothing
        return
    txt = txt.strip(",.!?").upper()
    if txt not in KEY:  # less is more: only the words that carry the song
        return
    if a < shot_at(t)["start"] - 0.02:  # a word never crosses a cut
        return
    life = t - a
    alpha = ease(life / 0.08)
    if b - a > HELD:
        alpha *= max(0.0, 1 - (life - 1.5) / 0.6) if life > 1.5 else 1
    if alpha <= 0:
        return
    side = FACE_X.get(shot_at(t)["id"], 0.5)
    maxw = W * (0.84 if PORTRAIT else (0.34 if abs(side - 0.5) > 0.08 else 0.80))
    size = int(260 * K)
    while True:
        f = BIG(size)
        bb = d.textbbox((0, 0), txt, font=f)
        if bb[2] - bb[0] <= maxw or size < 40:
            break
        size -= 6
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    if PORTRAIT or abs(side - 0.5) <= 0.08:  # face centred: under it
        x, y = (W - tw) / 2, H * (0.74 if PORTRAIT else 0.78) - th / 2
    elif side < 0.5:
        x, y = W * 0.96 - tw, H * 0.5 - th / 2
    else:
        x, y = W * 0.04, H * 0.5 - th / 2
    pop = 1 + 0.06 * (1 - ease(life / 0.12))  # a tiny settle on the attack
    if pop > 1.001:
        f = BIG(int(size * pop))
        bb2 = d.textbbox((0, 0), txt, font=f)
        x -= ((bb2[2] - bb2[0]) - tw) / 2
        y -= ((bb2[3] - bb2[1]) - th) / 2
    d.text((x - bb[0], y - bb[1]), txt, font=f, fill=WHITE + (int(240 * alpha),))


def small_line(d, t):
    """B: one tracked line at the bottom, hairline grows with the sung words."""
    ln = next((l for l in lines if l[0] <= t < l[1]), None)
    if not ln:
        return
    a, b, text = ln
    alpha = min(ease((t - a) / 0.15), ease((b - t) / 0.2))
    lw = [w for w in words if a - 0.05 <= w[0] < b]
    done = sum(1 for w in lw if w[0] <= t)
    frac = done / max(1, len(lw))
    s = text.upper()
    track = 3 * K
    total = sum(d.textlength(c, font=SMALL) + track for c in s)
    if total > W * 0.9:  # wrap long lines at a space near the middle
        cut = s.rfind(" ", 0, len(s) // 2 + 6)
        rows = [s[:cut], s[cut + 1:]]
    else:
        rows = [s]
    y = H * (0.80 if PORTRAIT else 0.88) - (len(rows) - 1) * 34 * K
    widths = [sum(d.textlength(c, font=SMALL) + track for c in r) for r in rows]
    for r, rw in zip(rows, widths):
        x = (W - rw) / 2
        for c in r:
            d.text((x, y), c, font=SMALL, fill=WHITE + (int(255 * alpha),))
            x += d.textlength(c, font=SMALL) + track
        y += 34 * K
    full = max(widths)
    x0 = (W - full) / 2
    d.line((x0, y + 6 * K, x0 + full * frac, y + 6 * K), fill=PURPLE + (int(255 * alpha),), width=max(2, int(3 * K)))


def frame(t):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if t >= CARD:
        end_card(d, t)
    elif CARD_ONLY:
        pass
    elif shot_at(t)["section"] in VERSE:
        small_line(d, t)
    elif not VERSES_ONLY:
        big_word(d, t)
    a = im.split()[3]
    if a.getbbox() is None:
        return im
    small = a.resize((max(1, W // 2), max(1, H // 2)), Image.BILINEAR).filter(ImageFilter.GaussianBlur(6))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh.putalpha(small.resize((W, H), Image.BILINEAR).point(lambda v: int(v * 0.55)))
    return Image.alpha_composite(sh, im)


n = int(math.ceil(DUR * FPS))
enc = ["-c:v", "h264_videotoolbox", "-b:v", "60M"] if H > 1080 else ["-c:v", "libx264", "-crf", "17", "-preset", "medium"]
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-i", SRC, "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto[v]",
                       "-map", "[v]", "-map", "0:a", *enc, "-pix_fmt", "yuv420p", "-c:a", "copy", "-frames:v", str(round(DUR * FPS)), DST],
                      stdin=subprocess.PIPE)
for k in range(n):
    ff.stdin.write(frame(k / FPS).tobytes())
ff.stdin.close()
ff.wait()
print(DST, ff.returncode)
