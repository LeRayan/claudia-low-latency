#!/usr/bin/env python3
"""Make a lip-synced take with Pruna p-video-2-pro-avatar (portrait + audio -> singing/talking video) and log spend.

usage: avatar.py --image plate.png --audio window.wav --prompt "..." --out clips/x.mp4 [--resolution 768p]
                 [--no-upsampling] [--seed N]
The audio sets the length (1 s to 3 min). Billed per output second: 480p $0.02, 768p $0.04, 1080p $0.06.
"""
import argparse, json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import pruna  # env loading, upload and the retrying HTTP call
pruna.MODEL = "p-video-2-pro-avatar"  # so the spend log names this model

RATE = {"480p": 0.02, "768p": 0.04, "1080p": 0.06, "2k": 0.08, "4k": 0.12}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--prompt", default="The woman is singing.")
    ap.add_argument("--out", required=True)
    ap.add_argument("--resolution", default="768p")
    ap.add_argument("--no-upsampling", action="store_true")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--what", default="avatar take")
    a = ap.parse_args()
    pruna.load_env()
    inp = {"image": pruna.upload(a.image), "audio": pruna.upload(a.audio), "prompt": a.prompt,
           "resolution": a.resolution, "prompt_upsampling": not a.no_upsampling}
    if a.seed is not None:
        inp["seed"] = a.seed
    p = pruna.call("POST", "/predictions", json.dumps({"input": inp}).encode(),
                   {"Content-Type": "application/json", "Model": "p-video-2-pro-avatar"})
    pid = p.get("id") or p.get("prediction_id")
    print("submitted", pid)
    while True:
        s = pruna.call("GET", f"/predictions/status/{pid}")
        if s.get("status") in ("succeeded", "completed", "success"):
            break
        if s.get("status") in ("failed", "error", "canceled"):
            sys.exit(f"failed: {json.dumps(s)[:500]}")
        time.sleep(8)
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(pruna.call("GET", s.get("generation_url") or s["output"]["generation_url"], raw=True))
    out.with_suffix(".json").write_text(json.dumps({k: v for k, v in inp.items() if k not in ("image", "audio")}
                                                   | {"image": a.image, "audio": a.audio, "id": pid}, indent=1))
    secs = pruna.audio_seconds(a.audio)
    pruna.log_spend(f"{a.what} ({secs:.1f}s {a.resolution})", RATE[a.resolution] * secs)
    print(out)


if __name__ == "__main__":
    main()
