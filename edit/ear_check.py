#!/usr/bin/env python3
"""The ear check (anabology's toolkit #5): the few hit words no aligner could confirm, as short previews to judge by ear.

usage: python3 edit/ear_check.py CUT.mp4 OUT.mp4 [--n 5]
Picks the n flagged hit words with the lowest confidence; for each, 6 s of the cut around the word with a card:
"k/n · WORD at 1:54.7 · ok, early or late?" and a marker bar that fills exactly when the word is shown.
"""
import json, pathlib, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
ROOT = pathlib.Path(__file__).resolve().parent.parent
cut, out = sys.argv[1], sys.argv[2]
n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 5
hits = json.load(open(ROOT / "v2/audio/hits.json"))
pick = sorted([h for h in hits if h["flag"]], key=lambda h: h["conf"])[:n]
pick.sort(key=lambda h: h["t"])
tmp = ROOT / "v2/fx/ear"; tmp.mkdir(parents=True, exist_ok=True)
f = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", 30, index=1)
parts = []
for k, h in enumerate(pick, 1):
    a = max(0, h["t"] - 3.0)
    card = Image.new("RGBA", (1344, 768), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    m, s = divmod(h["t"], 60)
    txt = f"{k}/{len(pick)}  ·  {h['word']} at {int(m)}:{s:04.1f}  ·  ok, early or late?"
    d.rectangle((0, 0, 1344, 56), fill=(0, 0, 0, 200)); d.text((20, 12), txt, font=f, fill=(255, 255, 255, 255))
    cp = tmp / f"card{k}.png"; card.save(cp)
    seg = tmp / f"seg{k}.mp4"
    x0 = (h["show"] - a)  # the bar turns purple exactly while the word is on screen
    x1 = (h["hide"] - a)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(a), "-t", "6", "-i", cut, "-i", str(cp), "-filter_complex",
                    f"[0:v][1:v]overlay=0:0[v0];[v0]drawbox=x=0:y=ih-14:w=iw:h=14:color=white@0.25:t=fill,"
                    f"drawbox=x=0:y=ih-14:w=iw:h=14:color=0x9B1DBE:t=fill:enable='between(t,{x0:.3f},{x1:.3f})'[v]",
                    "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-crf", "20", "-c:a", "aac", "-b:a", "192k",
                    str(seg)], check=True)
    parts.append(seg)
lst = tmp / "list.txt"; lst.write_text("".join(f"file '{p}'\n" for p in parts))
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", out], check=True)
print(out, [(h["word"], h["t"], h["conf"]) for h in pick])
