#!/usr/bin/env python3
"""Clean per-frame mattes: BiRefNet alpha per frame, temporally steadied inside each shot, soft edges kept.

usage: .venv-align/bin/python scripts/matte_build.py MATTE_DIR OUT_ALPHA.mp4 --start S --cuts 7.5,15.385,...
- soft alpha (never thresholded: a hard 128 cut made the jagged hair edges)
- temporal median of 3 frames within a shot (never across a cut), removing one-frame holes and flicker
- tiny holes filled (closing), stray specks removed (opening)
Prints the flicker metric: mean |alpha_t - alpha_t-1| on edge pixels, within shots.
"""
import argparse, glob, subprocess
import numpy as np
from PIL import Image, ImageFilter

ap = argparse.ArgumentParser()
ap.add_argument("matte_dir"); ap.add_argument("out")
ap.add_argument("--start", type=float, default=0.0)
ap.add_argument("--cuts", default="")
a = ap.parse_args()
FPS = 24
files = sorted(glob.glob(f"{a.matte_dir}/*.png"))
cuts = [round((float(c) - a.start) * FPS) for c in a.cuts.split(",") if c]


def load(f):
    im = Image.open(f)
    al = im.split()[3] if im.mode == "RGBA" else im.convert("L")
    al = al.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))   # close tiny holes
    al = al.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))   # drop stray specks
    return np.asarray(al, np.float32)


A = [load(f) for f in files]
shot = np.zeros(len(A), int)
for c in cuts:
    shot[c:] += 1
out = []
for i in range(len(A)):
    nb = [j for j in (i - 1, i, i + 1) if 0 <= j < len(A) and shot[j] == shot[i]]
    out.append(np.median(np.stack([A[j] for j in nb]), 0) if len(nb) == 3 else A[i])


def flicker(seq):
    d = []
    for i in range(1, len(seq)):
        if shot[i] != shot[i - 1]:
            continue
        edge = (seq[i] > 20) & (seq[i] < 235) | (np.abs(seq[i] - seq[i - 1]) > 0)
        d.append(np.abs(seq[i] - seq[i - 1])[edge].mean() if edge.any() else 0)
    return float(np.mean(d))


print(f"flicker raw {flicker(A):.2f}  steadied {flicker(out):.2f}")
h, w = out[0].shape
p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{w}x{h}", "-r",
                      str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "10", "-pix_fmt", "yuv420p", a.out],
                     stdin=subprocess.PIPE)
for m in out:
    p.stdin.write(np.clip(m, 0, 255).astype(np.uint8).tobytes())
p.stdin.close(); p.wait()
print(a.out)
