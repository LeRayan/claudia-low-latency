#!/usr/bin/env python3
"""Draw the graphics layer (bit meter + lyric type) and composite it over a cut.

usage: graphics.py edit/rough-v1.mp4 edit/cut-v2.mp4
Frames are drawn with PIL at the cut's size and piped to ffmpeg as RGBA; nothing touches disk in between.
Timings: lyric lines below (from the bar map and Whisper), word highlight from Whisper word times where they match.
"""
import json, math, pathlib, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC, DST = sys.argv[1], sys.argv[2]
probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
                        "-of", "json", SRC], capture_output=True, text=True, check=True)
info = json.loads(probe.stdout)
W, H = info["streams"][0]["width"], info["streams"][0]["height"]
DUR = float(info["format"]["duration"])
FPS = 24
K = min(H / 768, W / 640)  # layout is designed at 768p landscape; portrait scales by width
PORTRAIT = H > W
PURPLE = (155, 29, 190)  # Pruna primary #9B1DBE
LILAC = (200, 87, 239)   # Pruna accent #C857EF
sys.path.insert(0, str(ROOT / "edit"))
from project import P, path  # noqa: E402
BAR = json.load(open(path("beatmap")))["bars"]

# bit meter steps: (time, bits, size); each lands on a bar line where the lyric squeezes her
STEPS = [(0.0, 32, "140 GB"), (BAR[10], 16, "70 GB"), (BAR[13], 8, "35 GB"), (BAR[21], 4, "17.5 GB")]
LOCK = BAR[58]  # "Same girl": the meter locks
NAMES = {32: "FP32", 16: "FP16", 8: "INT8", 4: "INT4"}

from lyrics import LINES  # (start, end, text, word start times)

F_LYR = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", int(38 * K), index=1)  # Bold
F_MONO = ImageFont.truetype("/System/Library/Fonts/SFNSMono.ttf", int(22 * K))
F_MONO_S = ImageFont.truetype("/System/Library/Fonts/SFNSMono.ttf", int(16 * K))
M = int(48 * K)


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def draw_meter(d, t):
    idx = max(i for i, s in enumerate(STEPS) if s[0] <= t)
    bits, size = STEPS[idx][1], STEPS[idx][2]
    since = t - STEPS[idx][0]
    prev_bits = STEPS[idx - 1][1] if idx else bits
    roll = idx and since < 0.214  # one eighth note at 140 BPM: cells drop out one by one
    lit = round(prev_bits - (prev_bits - bits) * ease(since / 0.214)) if roll else bits
    x, y = M, (int(H * 0.08) if PORTRAIT else M)
    flash = idx and since < 0.11
    label = f"{NAMES[bits]} · {size}"
    d.text((x, y), label, font=F_MONO, fill=(*LILAC, 255) if flash else (255, 255, 255, 235))
    cy, cw, gap = y + int(34 * K), int(8 * K), int(3 * K)
    for i in range(32):
        on = i < lit
        d.rectangle((x + i * (cw + gap), cy, x + i * (cw + gap) + cw, cy + int(10 * K)),
                    fill=(*PURPLE, 255) if on else (255, 255, 255, 50))
    locked = t >= LOCK
    check = "SAME GIRL ✓"
    pulse = locked and (t - LOCK) < 0.43
    cy2 = cy + int(22 * K)
    if locked:  # the lock: a Pruna-purple pill behind the check
        w = d.textlength(check, font=F_MONO_S)
        d.rounded_rectangle((x - int(6 * K), cy2 - int(3 * K), x + w + int(6 * K), cy2 + int(20 * K)), radius=int(6 * K),
                            fill=(*(LILAC if pulse else PURPLE), 255))
    d.text((x, cy2), check, font=F_MONO_S, fill=(255, 255, 255, 255 if locked else 170))


# LOW LATENCY's device: a latency readout that rolls down as she names each technique, and a row of chips
TECH = ["DISTILL", "PRUNE", "FUSE", "CACHE", "QUANTIZE", "SPECULATE", "COMPILE"]
# (time the chip lights, chip, latency after it) — on the word that names it
LAT_STEPS = [(32.2, "DISTILL", 620), (38.58, "PRUNE", 410), (45.09, "FUSE", 210), (83.71, "CACHE", 120),
             (86.63, "QUANTIZE", 64), (90.05, "SPECULATE", 31), (109.9, "COMPILE", 9)]  # Suno word alignment
TEASE = [(1.2, "PRUNE"), (3.05, "DISTILL"), (5.2, "FUSE")]  # the intro chant flashes chips before they are earned
BURST = [(104.68, "QUANTIZE"), (105.86, "DISTILL"), (106.57, "PRUNE"), (108.06, "FUSE"), (108.4, "CACHE"), (109.9, "COMPILE")]
LAT_LOCK = 141.32  # "Less compute. More me."


def draw_latency(d, t):
    x, y = M, (int(H * 0.08) if PORTRAIT else M)
    done = [s for s in LAT_STEPS if s[0] <= t]
    prev = done[-2][2] if len(done) > 1 else 1240
    cur = done[-1][2] if done else 1240
    since = t - done[-1][0] if done else 99
    shown = round(prev - (prev - cur) * ease(since / 0.43)) if since < 0.43 else cur  # rolls over one beat
    flash = since < 0.15
    d.text((x, y), f"LATENCY {shown:,} ms", font=F_MONO, fill=(*LILAC, 255) if flash else (255, 255, 255, 235))
    lit = {s[1] for s in done}
    hot = {c for t0, c in TEASE + BURST if 0 <= t - t0 < 0.45}
    cx, cy = x, y + int(32 * K)
    for chip in TECH:
        w = d.textlength(chip, font=F_MONO_S) + int(12 * K)
        if PORTRAIT and cx + w > W - M:  # wrap the chip row on a narrow frame
            cx, cy = x, cy + int(26 * K)
        on, burn = chip in lit, chip in hot
        d.rounded_rectangle((cx, cy, cx + w, cy + int(20 * K)), radius=int(5 * K),
                            fill=(*(LILAC if burn else PURPLE), 255) if (on or burn) else (255, 255, 255, 30),
                            outline=None if (on or burn) else (255, 255, 255, 90), width=max(1, int(K)))
        d.text((cx + int(6 * K), cy + int(2 * K)), chip, font=F_MONO_S, fill=(255, 255, 255, 255 if (on or burn) else 150))
        cx += w + int(6 * K)
    if t >= LAT_LOCK:
        msg = "LESS COMPUTE ✓  MORE ME"
        w = d.textlength(msg, font=F_MONO_S)
        ly = cy + int(30 * K)
        d.rounded_rectangle((x - int(6 * K), ly - int(3 * K), x + w + int(6 * K), ly + int(20 * K)), radius=int(6 * K),
                            fill=(*(LILAC if t - LAT_LOCK < 0.43 else PURPLE), 255))
        d.text((x, ly), msg, font=F_MONO_S, fill=(255, 255, 255, 255))


def draw_lyric(d, t):
    for a, b, txt, ts in LINES:
        if not (a <= t < b):
            continue
        fade_in, fade_out = ease((t - a) / 0.12), ease((b - t) / 0.15)
        alpha = min(fade_in, fade_out)
        toks = txt.split()
        x, y = M, (int(H * 0.70) if PORTRAIT else H - M - int(44 * K))  # portrait: above the app's bottom UI
        maxw = W - 2 * M
        # wrap onto two lines if needed
        rows, row = [], []
        for i, tk in enumerate(toks):
            trial = " ".join(toks[j] for j in row + [i])
            if row and d.textlength(trial, font=F_LYR) > maxw * (0.92 if PORTRAIT else 0.62):
                rows.append(row)
                row = []
            row.append(i)
        rows.append(row)
        y -= (len(rows) - 1) * int(48 * K)
        cur = max([i for i, s in enumerate(ts) if s <= t] or [0])
        for r in rows:
            cx = x
            for i in r:
                tk = toks[i] + " "
                if i == cur:  # the word being sung: white on a Pruna-purple pill
                    w = d.textlength(toks[i], font=F_LYR)
                    pad = int(7 * K)
                    d.rounded_rectangle((cx - pad, y - int(2 * K), cx + w + pad, y + int(46 * K)), radius=int(10 * K),
                                        fill=(*PURPLE, int(235 * alpha)))
                    col = (255, 255, 255, int(255 * alpha))
                elif i < cur:
                    col = (255, 255, 255, int(255 * alpha))
                else:
                    col = (255, 255, 255, int(175 * alpha))
                d.text((cx, y), tk, font=F_LYR, fill=col)
                cx += d.textlength(tk, font=F_LYR)
            y += int(48 * K)


def frame(t):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    (draw_latency if P.get("hud") == "latency" else draw_meter)(d, t)
    draw_lyric(d, t)
    # the shadow is computed at 768p and scaled up, so 4K frames cost about the same as 768p ones
    small = im.split()[3].resize((round(W / K), round(H / K)), Image.BILINEAR)
    shadow = small.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(6)).point(lambda v: min(255, int(v * 0.95)))
    shadow = shadow.resize((W, H), Image.BILINEAR)
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    base.putalpha(shadow)
    return Image.alpha_composite(base, im)


n = int(math.ceil(DUR * FPS))
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-i", SRC, "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto[v]",
                       "-map", "[v]", "-map", "0:a", *(["-c:v", "h264_videotoolbox", "-b:v", "60M", "-profile:v", "high"] if H > 1080
                                                       else ["-c:v", "libx264", "-crf", "17", "-preset", "medium"]),
                       "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", DST], stdin=subprocess.PIPE)
for k in range(n):
    ff.stdin.write(frame(k / FPS).tobytes())
ff.stdin.close()
ff.wait()
print(DST, ff.returncode)
