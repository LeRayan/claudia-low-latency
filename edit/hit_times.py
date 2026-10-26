#!/usr/bin/env python3
"""Exact on-screen times for the key words: Suno's word start, snapped to the real attack in her vocal stem,
then to the song's 16th-note grid when within 40 ms, shown one frame early (reads as on time to the eye).

usage: CLIP_PROJECT=v2 hit_times.py  -> v2/audio/hits.json  [{word, show, hide, suno, onset, snapped, source}]
Why: Suno's alignment sits up to ±150-200 ms off the sung attack; on a slammed word that is 2-5 visible frames.
"""
import array, json, math, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "edit"))
from project import path  # noqa: E402

KEY = {"LATENCY", "ZERO", "WASTED", "CUT", "SHINE", "TOKEN", "MINE", "FUSE", "KERNEL", "PRUNE", "DISTILL", "SHIP",
       "FASTER", "QUANTIZE", "CACHE", "COMPILE", "LESS", "COMPUTE", "MORE", "ME"}
SR, HOP = 16000, 80                     # 5 ms frames
WIN = 0.12                              # search ±120 ms around Suno's start (key words are >= ~0.3 s apart)
MIN_DB = 6.0                            # an attack must rise at least 6 dB in 20 ms to be trusted
GRID_SNAP = 0.040
LEAD = 1 / 24                           # one frame early

def band_rise(af):
    """dB rise over 20 ms, in 5 ms frames, of the vocal through an ffmpeg filter."""
    x = array.array("h", subprocess.run(["ffmpeg", "-v", "error", "-i", str(path("vocals")), "-af", af, "-ac", "1",
                                         "-ar", str(SR), "-f", "s16le", "-"], capture_output=True, check=True).stdout)
    lg = [20 * math.log10(math.sqrt(sum(v * v for v in x[i:i + HOP]) / HOP) + 1) for i in range(0, len(x) - HOP, HOP)]
    r = [0.0] * len(lg)
    for i in range(4, len(lg)):
        r[i] = lg[i] - min(lg[i - 4:i])
    return r


# full band catches vowels; above 3 kHz catches the consonant you hear first (sh, f, s, k bursts)
full, high = band_rise("anull"), band_rise("highpass=f=3000")
rise = [max(a, b) for a, b in zip(full, high)]
bm = json.load(open(path("beatmap")))
sixteenth = bm["beat_s"] / 4
grid0 = bm["first_downbeat"]

words = json.load(open(ROOT / "v2/audio/suno_aligned.words.json"))["chunks"]
hits = []
for c in words:
    w = c["text"].strip(",.!? ").upper()
    if w not in KEY:
        continue
    s, e = c["timestamp"]
    lo, hi = int((s - WIN) / 0.005), int((s + WIN) / 0.005)
    span = range(max(4, lo), min(len(rise), hi))
    peak = max(rise[i] for i in span)
    # the EARLIEST clear attack in the window: the first consonant, not the louder vowel after it
    j = next((i for i in span if rise[i] >= max(MIN_DB, 0.7 * peak)), None)
    onset = j * 0.005 if j is not None else None
    t = onset if onset is not None else s
    g = grid0 + round((t - grid0) / sixteenth) * sixteenth
    snapped = abs(g - t) <= GRID_SNAP
    t = g if snapped else t
    hits.append({"word": w, "suno": round(s, 3), "onset": None if onset is None else round(onset, 3),
                 "snapped": snapped, "source": "onset" if onset is not None else "suno",
                 "show": round(t - LEAD, 3), "end": round(e, 3)})
for k, h in enumerate(hits):  # hold to the next key word or 0.35 s past the sung word, at least 0.5 s, at most 2 s
    nxt = hits[k + 1]["show"] if k + 1 < len(hits) else h["end"] + 1
    h["hide"] = round(min(nxt - 0.02, max(h["show"] + 0.5, min(h["end"] + 0.35, h["show"] + 2.0))), 3)
out = ROOT / "v2/audio/hits.json"
out.write_text(json.dumps(hits, indent=1))
n_on = sum(h["source"] == "onset" for h in hits)
n_sn = sum(h["snapped"] for h in hits)
print(f"{len(hits)} hits: {n_on} on a measured attack, {len(hits) - n_on} on Suno's time; {n_sn} snapped to the 16th grid")
