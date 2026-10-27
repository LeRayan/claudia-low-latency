#!/usr/bin/env python3
"""Split the vocal out of a song with Demucs on Replicate (cjwbw/demucs, stem=vocals, ~10 s), and log spend.

usage: vocals.py song.mp3 vocals.wav
Lip-sync from the isolated vocal, never the full mix: the full mix gives mushy mouths.
"""
import base64, pathlib, subprocess, sys, tempfile, time, urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import pruna
import transcribe as tx

VERSION = "25a173108cff36ef9f80f854c162d01df9e6528be175794b81158fa03836d953"  # cjwbw/demucs
EST_COST = 0.01


def separate(src, dst):
    tx.load_env()
    with tempfile.TemporaryDirectory() as tmp:
        mp3 = pathlib.Path(tmp) / "a.mp3"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-b:a", "256k", str(mp3)], check=True)
        uri = "data:audio/mpeg;base64," + base64.b64encode(mp3.read_bytes()).decode()
    p = tx.req("POST", "https://api.replicate.com/v1/predictions",
               {"version": VERSION, "input": {"audio": uri, "stem": "vocals", "output_format": "wav"}})
    while p["status"] not in ("succeeded", "failed", "canceled"):
        time.sleep(2)
        p = tx.req("GET", p["urls"]["get"])
    if p["status"] != "succeeded":
        sys.exit(f"demucs: {p['status']} {p.get('error')}")
    url = p["output"]["vocals"]
    with tempfile.TemporaryDirectory() as tmp:
        raw = pathlib.Path(tmp) / "vocals.wav"
        urllib.request.urlretrieve(url, raw)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), str(dst)], check=True)
    pruna.MODEL = "cjwbw/demucs"
    pruna.log_spend(f"vocal stem of {pathlib.Path(src).name}", EST_COST)
    return dst


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    separate(sys.argv[1], sys.argv[2])
    print(sys.argv[2])
