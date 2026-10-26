#!/usr/bin/env python3
"""The word clock: one trusted start per sung word, from three independent sources, plus a spectrogram proof sheet.

usage: .venv-align/bin/python scripts/word_clock.py   (LOW LATENCY paths)
Sources: Suno's alignment (systematically ~110 ms late, measured), wav2vec2 forced alignment of the sheet (exact when
confident), and the vocal attack (full band + >3 kHz for consonants). Merge, per anabology's toolkit #5:
  1. forced conf >= 0.6 and within 0.25 s of Suno - bias -> forced t0
  2. else Suno - bias, then the earliest clear attack within ±60 ms of it (if any)
  3. flags: forced and the merged time disagree by > 0.3 s with forced conf >= 0.3, or no attack and conf < 0.3
Writes v2/audio/word_clock.json and v2/audio/word_clock_proof.png (one mel tile per key word, candidates drawn).
"""
import json, re, statistics, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

R = str(__import__("pathlib").Path(__file__).resolve().parent.parent) + "/"
SR = 16000
KEY = {"LATENCY", "ZERO", "WASTED", "CUT", "SHINE", "TOKEN", "MINE", "FUSE", "KERNEL", "PRUNE", "DISTILL", "SHIP",
       "FASTER", "QUANTIZE", "CACHE", "COMPILE", "LESS", "COMPUTE", "MORE", "ME"}
norm = lambda w: re.sub(r"[^A-Z]", "", w.upper())

fa = json.load(open(R + "v2/audio/forced.json"))
su = json.load(open(R + "v2/audio/suno_aligned.words.json"))["chunks"]
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", R + "v2/audio/stems/vocals.wav", "-ac", "1", "-ar", str(SR),
                      "-f", "f32le", "-"], capture_output=True, check=True).stdout
x = np.frombuffer(raw, np.float32)

# --- bias of Suno against confident forced words
bias = statistics.median([f["t0"] - s["timestamp"][0] for f, s in zip(fa, su) if f["conf"] >= 0.8 and f["t0"]])

# --- attack detector (5 ms frames): dB rise over 20 ms, full band and >3 kHz
def rise_db(sig):
    hop = 80
    n = len(sig) // hop
    e = np.sqrt((sig[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-6
    db = 20 * np.log10(e)
    r = np.zeros(n)
    for k in range(1, 5):
        r[4:] = np.maximum(r[4:], db[4:] - db[4 - k:n - k])
    return r

spec = np.fft.rfft(x[:len(x) // 2 * 2])
freqs = np.fft.rfftfreq(len(x[:len(x) // 2 * 2]), 1 / SR)
hp = np.fft.irfft(np.where(freqs > 3000, spec, 0)).astype(np.float32)
rise = np.maximum(rise_db(x), rise_db(hp))


def attack(t, win=0.06):
    lo, hi = max(4, int((t - win) / 0.005)), int((t + win) / 0.005)
    seg = rise[lo:hi]
    if len(seg) == 0 or seg.max() < 6:
        return None
    j = int(np.argmax(seg >= max(6, 0.7 * seg.max())))
    return (lo + j) * 0.005


words = []
for i, (f, s) in enumerate(zip(fa, su)):
    w = norm(f["word"])
    cand_suno = s["timestamp"][0] + bias
    # forced only when it agrees with Suno: confident forced hits on the NEIGHBOURING line happened ("mine" at 31.6)
    if f["conf"] >= 0.6 and f["t0"] is not None and abs(f["t0"] - cand_suno) <= 0.25:
        t, src = f["t0"], "forced"
    else:
        a = attack(cand_suno)
        t, src = (a, "suno-bias+attack") if a is not None else (cand_suno, "suno-bias")
    flag = ""
    if f["t0"] is not None and f["conf"] >= 0.3 and abs(f["t0"] - t) > 0.3:
        flag = "disagree"
    if src == "suno-bias" and f["conf"] < 0.3:
        flag = flag or "weak"
    words.append({"i": i, "word": f["word"], "key": w in KEY, "t": round(t, 3), "src": src, "conf": f["conf"],
                  "forced": f["t0"], "suno": round(s["timestamp"][0], 3), "end": round(s["timestamp"][1] + bias, 3),
                  "flag": flag})
# hand-measured onsets (spectrogram + attack list) where every source was wrong; each entry says why
import os
if os.path.exists(R + "v2/audio/word_overrides.json"):
    for o in json.load(open(R + "v2/audio/word_overrides.json")):
        words[o["i"]].update(t=o["t"], src="measured", flag="")
json.dump({"bias_s": round(bias, 3), "words": words}, open(R + "v2/audio/word_clock.json", "w"), indent=1)

# --- proof sheet: a mel-ish spectrogram tile per key word, 0.8 s around it
keys = [w for w in words if w["key"]]
TW, TH, COLS = 300, 150, 6
rows = (len(keys) + COLS - 1) // COLS
sheet = Image.new("RGB", (COLS * (TW + 6), rows * (TH + 26)), (255, 255, 255))
font = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", 13, index=1)
for n, w in enumerate(keys):
    c0 = w["t"] - 0.35
    seg = x[max(0, int(c0 * SR)):int((c0 + 0.8) * SR)]
    nfft, hop = 512, 64
    frames = [seg[k:k + nfft] * np.hanning(nfft) for k in range(0, max(1, len(seg) - nfft), hop)]
    S = np.abs(np.fft.rfft(np.array(frames), axis=1)).T[:200]  # 0-6.2 kHz
    S = 20 * np.log10(S + 1e-6)
    S = np.clip((S - (S.max() - 70)) / 70, 0, 1)
    img = Image.fromarray((255 - S[::-1] * 255).astype(np.uint8)).resize((TW, TH)).convert("RGB")
    d = ImageDraw.Draw(img)
    X = lambda t: (t - c0) / 0.8 * TW
    for t, col in ((w["suno"], (150, 150, 150)), (w["forced"], (0, 140, 255)), (w["t"], (200, 0, 160))):
        if t is not None and c0 <= t <= c0 + 0.8:
            d.line((X(t), 0, X(t), TH), fill=col, width=2)
    ox, oy = (n % COLS) * (TW + 6), (n // COLS) * (TH + 26)
    sheet.paste(img, (ox, oy + 22))
    ImageDraw.Draw(sheet).text((ox + 2, oy + 3), f"{w['word']} {w['t']:.2f}s {w['src']} c{w['conf']:.2f} {w['flag']}",
                               font=font, fill=(200, 0, 0) if w["flag"] else (0, 0, 0))
sheet.save(R + "v2/audio/word_clock_proof.png")
srcs = {}
for w in keys:
    srcs[w["src"]] = srcs.get(w["src"], 0) + 1
print(f"bias {bias*1000:.0f} ms | key words {len(keys)} by source {srcs} | flagged {[ (w['word'], w['t'], w['flag']) for w in keys if w['flag']]}")
