#!/usr/bin/env python3
"""Audio windows for the avatar model, built so the lead-in can't silently go missing.

usage: windows.py STEM START END OUT.wav [--lead 0.5]
       from windows import make_window; make_window(stem, t0, t1, out, lead=0.5)

The avatar model wants a short lead-in before the first word, which the edit trims. RUN FREE v1 added that lead-in
with ffmpeg's `adelay` in the same command that seeked into the stem (-ss ... -i ... -af loudnorm,adelay=500). On
ffmpeg 9 that inserted the silence for some windows and not for others (a click test placed the same marker at
+1.0 s or +1.5 s depending on the start time). The edit trimmed 0.5 s from every take, so some shots had her lips
half a second early. Here the cut and the loudness pass happen in ffmpeg, and the lead-in is prepended in numpy,
then checked: the first `lead` seconds must be digital silence and the length must be exact.
"""
import argparse, pathlib, subprocess, wave
import numpy as np

SR = 44100


def make_window(stem, t0, t1, out, lead=0.5, normalise=True):
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    af = ["-af", "loudnorm=I=-16:TP=-1.5"] if normalise else []
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", str(stem),
                          "-ac", "1", "-ar", str(SR)] + af + ["-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    seg = np.frombuffer(raw, np.int16)
    want = int(round((t1 - t0) * SR))
    seg = np.pad(seg, (0, max(0, want - len(seg))))[:want]  # exact length, whatever the filter did at the edges
    x = np.concatenate([np.zeros(int(round(lead * SR)), np.int16), seg])
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(x.tobytes())
    check_window(out, t1 - t0, lead)
    return out


def check_window(path, dur, lead):
    with wave.open(str(path)) as w:
        sr, n = w.getframerate(), w.getnframes()
        x = np.frombuffer(w.readframes(n), np.int16)
    head = x[:int(round(lead * sr))]
    assert np.abs(head).max() == 0, f"{path}: the {lead} s lead-in is not silent"
    assert abs(n / sr - (dur + lead)) < 0.002, f"{path}: length {n / sr:.3f} s, expected {dur + lead:.3f} s"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stem"); ap.add_argument("start", type=float); ap.add_argument("end", type=float); ap.add_argument("out")
    ap.add_argument("--lead", type=float, default=0.5)
    a = ap.parse_args()
    print(make_window(a.stem, a.start, a.end, a.out, a.lead))
