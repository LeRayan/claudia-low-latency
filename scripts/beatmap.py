#!/usr/bin/env python3
"""Estimate tempo and bar grid of a song from its onsets (pure stdlib).

usage: beatmap.py song.wav --bpm-range 135 145 --anchor 34.85 [--out edit/beatmap.json]
--anchor is a time known to be a downbeat (e.g. a beat drop); the grid is phase-locked near it.
"""
import argparse, array, json, math, subprocess

ap = argparse.ArgumentParser()
ap.add_argument("song")
ap.add_argument("--bpm-range", nargs=2, type=float, default=[60, 180])
ap.add_argument("--anchor", type=float, required=True)
ap.add_argument("--out", default="edit/beatmap.json")
a = ap.parse_args()

SR, HOP = 8000, 80  # 10 ms frames
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.song, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                     capture_output=True, check=True).stdout
x = array.array("h", raw)
env = [math.sqrt(sum(v * v for v in x[i:i + HOP]) / HOP) + 1e-9 for i in range(0, len(x) - HOP, HOP)]
log = [math.log(e) for e in env]
onset = [max(0.0, log[i] - log[i - 1]) for i in range(1, len(log))]
onset.insert(0, 0.0)
dur = len(onset) / 100


def strength(bpm, phase):
    period = 60 / bpm
    t, s, n = phase, 0.0, 0
    while t < dur:
        k = int(round(t * 100))
        s += max(onset[max(0, k - 2):k + 3])
        n += 1
        t += period
    return s / n


best = (0, 0, 0)
bpm = a.bpm_range[0]
while bpm <= a.bpm_range[1]:
    period = 60 / bpm
    for i in range(40):
        ph = (a.anchor % period) + (i - 20) * 0.005
        s = strength(bpm, ph % period)
        if s > best[0]:
            best = (s, bpm, ph % period)
    bpm = round(bpm + 0.05, 2)

_, bpm, phase = best
beat = 60 / bpm
# bar 1 downbeat: the beat on the grid closest to the anchor, stepped back by whole bars to just after 0
k = round((a.anchor - phase) / beat)
down = phase + k * beat
while down - 4 * beat >= -0.05:
    down -= 4 * beat
bars = []
t = down
while t < dur:
    bars.append(round(t, 3))
    t += 4 * beat
json.dump({"song": a.song, "bpm": bpm, "beat_s": round(beat, 5), "bar_s": round(4 * beat, 5),
           "first_downbeat": round(down, 3), "bars": bars, "duration": dur}, open(a.out, "w"), indent=1)
print(f"bpm {bpm}  beat {beat:.4f}s  bar {4*beat:.4f}s  first downbeat {down:.3f}s  bars {len(bars)}")
