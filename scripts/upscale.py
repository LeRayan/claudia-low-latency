#!/usr/bin/env python3
"""Upscale each frame-exact shot segment with Pruna p-video-upscale, in parallel, and log spend.

usage: upscale.py --src edit/segments/768p --dst edit/segments/4k --target 4k
Per request the model caps processed frames (4k: 300, 2k: 600, 1080p: 1,200), so shots go one by one, never the cut.
Billed per output second rounded up: 720p $0.01, 1080p $0.02, 2k $0.04, 4k $0.08 (up to 30 fps).
"""
import argparse, csv, datetime, json, math, pathlib, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import pruna  # reuse its env loading, upload and retrying HTTP call

RATE = {"720p": 0.01, "1080p": 0.02, "2k": 0.04, "4k": 0.08}


def upscale(src, dst, target):
    url = pruna.upload(str(src))
    p = pruna.call("POST", "/predictions", json.dumps({"input": {"video": url, "target": target}}).encode(),
                   {"Content-Type": "application/json", "Model": "p-video-upscale"})
    pid = p.get("id") or p.get("prediction_id")
    while True:
        s = pruna.call("GET", f"/predictions/status/{pid}")
        if s.get("status") in ("succeeded", "completed", "success"):
            break
        if s.get("status") in ("failed", "error", "canceled"):
            return src.stem, 0, f"FAILED {json.dumps(s)[:300]}"
        time.sleep(5)
    gen = s.get("generation_url") or s.get("output", {}).get("generation_url")
    dst.write_bytes(pruna.call("GET", gen, raw=True))
    secs = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(dst)],
                                capture_output=True, text=True).stdout)
    return src.stem, math.ceil(secs) * RATE[target], "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    ap.add_argument("--target", default="4k")
    a = ap.parse_args()
    pruna.load_env()
    dst = pathlib.Path(a.dst)
    dst.mkdir(parents=True, exist_ok=True)
    segs = sorted(pathlib.Path(a.src).glob("S*.mp4"))
    total = 0.0
    with ThreadPoolExecutor(8) as ex:
        for sid, cost, msg in ex.map(lambda f: upscale(f, dst / f.name, a.target), segs):
            print(sid, msg)
            total += cost
    with (ROOT / "spend.csv").open("a", newline="") as f:
        csv.writer(f).writerow([datetime.date.today().isoformat(), "p-video-upscale",
                                f"upscale {len(segs)} segments to {a.target}", f"{total:.3f}"])
    print(f"spend logged ${total:.2f}")


if __name__ == "__main__":
    main()
