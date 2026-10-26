#!/usr/bin/env python3
"""Assemble the board's clips into one cut on the song, frame-exact.

usage: assemble.py --tag v5                       # 768p: cut each shot's latest take into edit/segments/768p, then join
       assemble.py --tag v5 --segments edit/segments/4k --res 4k   # join already-cut (e.g. upscaled) segments

Every cut sits on an absolute frame of the song: shot k covers frames round(start*24) .. round(end*24). Cutting each
shot to its own rounded-up length instead drifted the picture 0.03 s per cut (0.5 s late by the end).
The full song is laid underneath, so the cut never drifts from the music.
"""
import argparse, json, pathlib, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from project import P, path  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
FPS = 24
# above 768p use the Mac's hardware encoder: software x264 at 4K maxes every core for minutes
ENC = {False: ["-c:v", "libx264", "-crf", "16", "-preset", "medium"],
       True: ["-c:v", "h264_videotoolbox", "-b:v", "60M", "-profile:v", "high"]}
SIZES = {"768p": "1344:768", "1080p": "1920:1080", "2k": "2560:1440", "4k": "3840:2160"}
ap = argparse.ArgumentParser()
ap.add_argument("--res", default="768p")
ap.add_argument("--tag", default="v1", help="name of the output cut")
ap.add_argument("--segments", help="directory of already-cut segments <id>.mp4 to join instead of cutting clips")
ap.add_argument("--out")
a = ap.parse_args()
board = json.load(open(path("board")))
song = ROOT / board["song"]
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(song)],
                           capture_output=True, text=True).stdout)
size = SIZES[a.res]
shots = board["shots"]
bounds = [round(s["start"] * FPS) for s in shots] + [round(dur * FPS)]

seg_dir = pathlib.Path(a.segments) if a.segments else path("edit_dir") / "segments/768p"
if not a.segments:
    seg_dir.mkdir(parents=True, exist_ok=True)
    for k, s in enumerate(shots):
        n = bounds[k + 1] - bounds[k]
        pick = P.get("takes", {}).get(s["id"])  # a chosen take, else the latest
        take = path("clips_dir") / f"{s['id']}-768p-{pick}.mp4" if pick else sorted(path("clips_dir").glob(f"{s['id']}-768p-v*.mp4"))[-1]
        meta = take.with_suffix(".json")
        pre = json.loads(meta.read_text()).get("preroll", 0) if meta.exists() else 0  # avatar takes carry a lead-in
        # tpad holds the last frame if a take is a frame short of its slot
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(take), "-an", "-vf",
                        f"trim=start_frame={round(pre * FPS)},setpts=PTS-STARTPTS,fps={FPS},scale={SIZES['768p']}:force_original_aspect_ratio=increase,crop={SIZES['768p']},"
                        f"setsar=1,tpad=stop_mode=clone:stop=24,trim=end_frame={n},setpts=PTS-STARTPTS",
                        "-c:v", "libx264", "-crf", "12", "-preset", "medium", "-pix_fmt", "yuv420p",
                        str(seg_dir / f"{s['id']}.mp4")], check=True)
        print(s["id"], take.name, n, "frames")

inputs, filters = [], []
for k, s in enumerate(shots):
    n = bounds[k + 1] - bounds[k]
    inputs += ["-i", str(seg_dir / f"{s['id']}.mp4")]
    filters.append(f"[{k}:v]fps={FPS},scale={size}:force_original_aspect_ratio=increase:flags=lanczos,crop={size},"
                   f"setsar=1,tpad=stop_mode=clone:stop=24,"
                   f"trim=end_frame={n},setpts=PTS-STARTPTS[v{k}]")
filters.append("".join(f"[v{k}]" for k in range(len(shots))) + f"concat=n={len(shots)}:v=1:a=0[v]")
out = pathlib.Path(a.out or path("edit_dir") / f"rough-{a.tag}.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-i", str(song), "-filter_complex", ";".join(filters),
                "-map", "[v]", "-map", f"{len(shots)}:a", *ENC[a.res != "768p"], "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "320k", "-shortest", str(out)], check=True)
print(out)
