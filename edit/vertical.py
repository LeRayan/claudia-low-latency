#!/usr/bin/env python3
"""A 9:16 version of a cut: each shot's 768p segment is cropped to a 9:16 window centred on her face, scaled to
1080x1920, joined frame-exact on the song, then the graphics are drawn in portrait layout.

usage: vertical.py --tag v5     -> edit/rough-<tag>-vertical.mp4 and edit/cut-<tag>-vertical.mp4
"""
import argparse, json, pathlib, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from project import P, path  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
FPS = 24
# where her face sits across each shot, as a fraction of the frame width (read off the v5 contact sheet)
FACE_X = P.get("face_x") or {"S01": 0.55, "S02": 0.62, "S03": 0.30, "S04": 0.48, "S05": 0.50, "S06": 0.48, "S07": 0.30, "S08": 0.46,
          "S09": 0.50, "S10": 0.50, "S11": 0.50, "S12": 0.62, "S13": 0.46, "S14": 0.66, "S15": 0.50, "S16": 0.47}
ap = argparse.ArgumentParser()
ap.add_argument("--tag", default="v5")
ap.add_argument("--overlay", help="graphics script in edit/, default graphics.py")
a = ap.parse_args()
board = json.load(open(path("board")))
song = ROOT / board["song"]
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(song)],
                           capture_output=True, text=True).stdout)
shots = board["shots"]
bounds = [round(s["start"] * FPS) for s in shots] + [round(dur * FPS)]
cw = 432  # 9:16 of 768 tall
inputs, filters = [], []
for k, s in enumerate(shots):
    n = bounds[k + 1] - bounds[k]
    x = int(min(1344 - cw, max(0, FACE_X[s["id"]] * 1344 - cw / 2)))
    inputs += ["-i", str(path("edit_dir") / f"segments/768p/{s['id']}.mp4")]
    filters.append(f"[{k}:v]crop={cw}:768:{x}:0,scale=1080:1920:flags=lanczos,setsar=1,fps={FPS},"
                   f"tpad=stop_mode=clone:stop=24,trim=end_frame={n},setpts=PTS-STARTPTS[v{k}]")
filters.append("".join(f"[v{k}]" for k in range(len(shots))) + f"concat=n={len(shots)}:v=1:a=0[v]")
rough = path("edit_dir") / f"rough-{a.tag}-vertical.mp4"
subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-i", str(song), "-filter_complex", ";".join(filters),
                "-map", "[v]", "-map", f"{len(shots)}:a", "-c:v", "h264_videotoolbox", "-b:v", "20M", "-profile:v", "high",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "320k", "-shortest", str(rough)], check=True)
subprocess.run(["python3", str(ROOT / ("edit/" + (a.overlay or "graphics.py"))), str(rough), str(path("edit_dir") / f"cut-{a.tag}-vertical.mp4")], check=True)
print(path("edit_dir") / f"cut-{a.tag}-vertical.mp4")
