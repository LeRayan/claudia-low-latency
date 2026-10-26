#!/usr/bin/env python3
"""Measure how far each clip's own soundtrack is shifted from the audio window it was given.

usage: CLIP_PROJECT=v2 sync_check.py [--tag v1]
Cross-correlates 10 ms loudness envelopes of the clip's audio and its input window over +-1.5 s.
A positive offset means the clip's audio (and so her lips) runs LATE versus the window.
"""
import argparse, array, glob, json, math, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "edit"))
from project import path  # noqa: E402


def env(f, dur=None):
    cmd = ["ffmpeg", "-v", "error", "-i", f] + (["-t", str(dur)] if dur else []) + ["-ac", "1", "-ar", "8000", "-f", "s16le", "-"]
    x = array.array("h", subprocess.run(cmd, capture_output=True).stdout)
    return [math.sqrt(sum(v * v for v in x[i:i + 80]) / 80) for i in range(0, len(x) - 80, 80)]


def corr(a, b, lag):
    pairs = [(a[i], b[i + lag]) for i in range(max(0, -lag), min(len(a), len(b) - lag))]
    if len(pairs) < 50:
        return -1
    ma = sum(p[0] for p in pairs) / len(pairs)
    mb = sum(p[1] for p in pairs) / len(pairs)
    num = sum((p - ma) * (q - mb) for p, q in pairs)
    den = math.sqrt(sum((p - ma) ** 2 for p, _ in pairs) * sum((q - mb) ** 2 for _, q in pairs)) or 1
    return num / den


ap = argparse.ArgumentParser()
ap.add_argument("--tag")
a = ap.parse_args()
board = json.load(open(path("board")))
for s in board["shots"]:
    takes = sorted(glob.glob(str(path("clips_dir") / f"{s['id']}-768p-{a.tag or 'v*'}.mp4")))
    wins = glob.glob(str(path("windows_dir") / f"{s['id']}-vocal-{s['start']:.3f}-{s['dur']:.3f}.wav"))  # this cut's window
    if not takes or not wins:
        continue
    w = env(wins[-1])
    c = env(takes[-1], s["dur"])
    best = max(range(-150, 151, 2), key=lambda L: corr(w, c, L))
    print(f"{s['id']} {pathlib.Path(takes[-1]).name:22s} offset {best * 10:+5d} ms  corr {corr(w, c, best):.2f}  (at 0: {corr(w, c, 0):.2f})")
