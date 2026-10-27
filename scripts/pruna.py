#!/usr/bin/env python3
"""Make a clip with Pruna p-video-2-pro-reference and log spend.

usage: pruna.py --prompt-file P.txt --out clips/test/take1.mp4 --image sheet.png --image plate.png
                [--audio window.wav --keep-audio] [--duration 5] [--resolution 768p]
                [--upsampler off] [--aspect 16:9] [--seed N] [--first-frame plate.png] [--what "..."]
Images are numbered in order: the first --image is <Picture 1>. Local files are uploaded; URLs pass through.
"""
import argparse, csv, datetime, json, mimetypes, os, pathlib, subprocess, sys, time, urllib.error, urllib.request, uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://api.pruna.ai/v1"
MODEL = "p-video-2-pro-reference"
RATE = {"speed": {"480p": .02, "768p": .035, "1080p": .055, "2k": .075, "4k": .115},
        "cost": {"480p": .015, "768p": .025, "1080p": .045, "2k": .065, "4k": .105}}
IMG_RATE = {"speed": .01, "cost": .005}
AUDIO_RATE = {"speed": .0025, "cost": .0015}


def load_env():
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))


def call(method, path, body=None, headers=None, raw=False):
    url = path if path.startswith("http") else BASE + path
    r = urllib.request.Request(url, method=method, data=body)
    r.add_header("apikey", os.environ["PRUNA_API_KEY"])
    for k, v in (headers or {}).items():
        r.add_header(k, v)
    for attempt in range(5):  # transient gateway errors happen; back off and retry
        try:
            with urllib.request.urlopen(r, timeout=300) as f:
                return f.read() if raw else json.load(f)
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == 4:
                raise
        except urllib.error.URLError:
            if attempt == 4:
                raise
        time.sleep(5 * (attempt + 1))


def upload(path):
    if path.startswith("http"):
        return path
    p = pathlib.Path(path)
    boundary = uuid.uuid4().hex
    mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"content\"; filename=\"{p.name}\"\r\n"
            f"Content-Type: {mime}\r\n\r\n").encode() + p.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    res = call("POST", "/files", body, {"Content-Type": f"multipart/form-data; boundary={boundary}"})
    return res["urls"]["get"]


def audio_seconds(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout
    return float(out or 0)


def log_spend(what, cost):
    path = ROOT / "spend.csv"
    if not path.exists():
        path.write_text("date,model,what,est_cost\n")  # a fresh clone has no log yet
    with path.open("a", newline="") as f:
        csv.writer(f).writerow([datetime.date.today().isoformat(), MODEL, what, f"{cost:.3f}"])
    total = sum(float(r["est_cost"]) for r in csv.DictReader(path.open()))
    print(f"spend logged ${cost:.3f}; running total ${total:.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--image", action="append", default=[])
    ap.add_argument("--audio", action="append", default=[])
    ap.add_argument("--keep-audio", action="store_true")
    ap.add_argument("--first-frame")
    ap.add_argument("--duration", type=int, default=5)
    ap.add_argument("--resolution", default="768p")
    ap.add_argument("--mode", default="speed")
    ap.add_argument("--upsampler", default="off")
    ap.add_argument("--aspect", default="16:9")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--what", default="clip")
    a = ap.parse_args()
    load_env()

    prompt = pathlib.Path(a.prompt_file).read_text().strip()
    inp = {"prompt": prompt, "duration": a.duration, "resolution": a.resolution, "mode": a.mode,
           "prompt_upsampler": a.upsampler, "aspect_ratio": a.aspect}
    if a.image:
        inp["image"] = [upload(i) for i in a.image]
    if a.audio:
        inp["audio"] = [upload(x) for x in a.audio]
    if a.keep_audio:
        inp["keep_audio"] = True
    if a.first_frame:
        inp["first_frame_image"] = upload(a.first_frame)
    if a.seed is not None:
        inp["seed"] = a.seed

    p = call("POST", "/predictions", json.dumps({"input": inp}).encode(),
             {"Content-Type": "application/json", "Model": MODEL})
    pid = p.get("id") or p.get("prediction_id")
    print("submitted", pid)
    while True:
        s = call("GET", f"/predictions/status/{pid}")
        status = s.get("status")
        if status in ("succeeded", "completed", "success"):
            break
        if status in ("failed", "error", "canceled"):
            sys.exit(f"{status}: {json.dumps(s)[:800]}")
        time.sleep(10)

    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    gen = s.get("generation_url") or s.get("output", {}).get("generation_url")
    out.write_bytes(call("GET", gen, raw=True))
    meta = {k: v for k, v in inp.items() if k != "prompt"} | {"local_images": a.image, "local_audio": a.audio,
                                                             "first_frame": a.first_frame, "id": pid}
    out.with_suffix(".json").write_text(json.dumps(meta, indent=1))
    out.with_suffix(".prompt.txt").write_text(prompt)
    print(out)

    secs = min(a.duration, 14) if a.duration == 15 else a.duration
    n_img = len(a.image) + (1 if a.first_frame else 0)
    aud = sum(min(audio_seconds(x), a.duration + .5) for x in a.audio if not x.startswith("http"))
    cost = secs * RATE[a.mode][a.resolution] + n_img * IMG_RATE[a.mode] + aud * AUDIO_RATE[a.mode]
    log_spend(f"{a.what} {a.duration}s {a.resolution}", cost)


if __name__ == "__main__":
    main()
