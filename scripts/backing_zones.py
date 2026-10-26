#!/usr/bin/env python3
"""Find where the vocal stem is mostly backing vocals (wide stereo) rather than her centred lead.

usage: backing_zones.py audio/stems/vocals.wav [--out audio/stems/backing_zones.json] [--ratio 0.7]
A 0.1 s frame counts as backing when its side energy is above --ratio of its centre energy; runs of at least 0.3 s
become zones. The lead in this mix sits dead centre (ratio ~0.05 in the verses), the chants and stacks are wide.
"""
import argparse, array, json, math, subprocess

ap = argparse.ArgumentParser()
ap.add_argument("stem")
ap.add_argument("--out", default="audio/stems/backing_zones.json")
ap.add_argument("--ratio", type=float, default=0.7)
a = ap.parse_args()
SR, HOP = 8000, 800
x = array.array("h", subprocess.run(["ffmpeg", "-v", "error", "-i", a.stem, "-ar", str(SR), "-f", "s16le", "-"],
                                    capture_output=True, check=True).stdout)
L, R = x[0::2], x[1::2]
frames = []
for i in range(0, len(L) - HOP, HOP):
    m = math.sqrt(sum(((L[j] + R[j]) / 2) ** 2 for j in range(i, i + HOP)) / HOP)
    s = math.sqrt(sum(((L[j] - R[j]) / 2) ** 2 for j in range(i, i + HOP)) / HOP)
    frames.append(m > 50 and s / max(m, 1e-9) > a.ratio)
zones, start = [], None
for k, wide in enumerate(frames + [False]):
    t = k * HOP / SR
    if wide and start is None:
        start = t
    if not wide and start is not None:
        if t - start >= 0.3:
            zones.append([round(start, 2), round(t, 2)])
        start = None
json.dump(zones, open(a.out, "w"))
print(len(zones), "zones,", round(sum(b - a for a, b in zones), 1), "s:", zones)
