#!/usr/bin/env python3
"""Generate stills with GPT Image 2.5 Sunburst on Replicate and log spend.

usage: sunburst.py --prompt-file P.txt --out sheets/v1/name [--ref img ...] [--quality xhigh]
                   [--n 2] [--ar 16:9] [--what "identity sheet"]
Refs are local files (sent as data URIs) or URLs, in order: Image 1, Image 2, ...
"""
import argparse, base64, csv, datetime, json, mimetypes, os, pathlib, sys, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODEL = "openai/gpt-image-2.5-sunburst"
PRICE = {"low": 0.012, "medium": 0.047, "high": 0.128, "xhigh": 0.25, "max": 0.50, "auto": 0.25}


def load_env():
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))


def req(method, url, body=None):
    r = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body else None)
    r.add_header("Authorization", "Bearer " + os.environ["REPLICATE_API_TOKEN"])
    r.add_header("Content-Type", "application/json")
    if method == "POST":
        r.add_header("Prefer", "wait=60")
    with urllib.request.urlopen(r, timeout=180) as f:
        return json.load(f)


def as_uri(ref):
    if ref.startswith("http"):
        return ref
    mime = mimetypes.guess_type(ref)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(pathlib.Path(ref).read_bytes()).decode()


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
    ap.add_argument("--out", required=True, help="output path prefix, e.g. sheets/v1/sheet-xhigh")
    ap.add_argument("--ref", action="append", default=[])
    ap.add_argument("--quality", default="xhigh")
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--ar", default="16:9")
    ap.add_argument("--what", default="still")
    a = ap.parse_args()
    load_env()

    prompt = pathlib.Path(a.prompt_file).read_text().strip()
    inp = {"prompt": prompt, "quality": a.quality, "number_of_images": a.n, "aspect_ratio": a.ar,
           "output_format": "png", "moderation": "low"}
    if a.ref:
        inp["input_images"] = [as_uri(r) for r in a.ref]

    p = req("POST", f"https://api.replicate.com/v1/models/{MODEL}/predictions", {"input": inp})
    while p["status"] not in ("succeeded", "failed", "canceled"):
        time.sleep(3)
        p = req("GET", p["urls"]["get"])
    if p["status"] != "succeeded":
        sys.exit(f"{p['status']}: {p.get('error')}")

    outs = p["output"] if isinstance(p["output"], list) else [p["output"]]
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    (out.parent / (out.name + ".prompt.txt")).write_text(
        prompt + "\n\n" + json.dumps({k: v for k, v in inp.items() if k not in ("prompt", "input_images")} | {"refs": a.ref}))
    for i, url in enumerate(outs, 1):
        dest = out.parent / f"{out.name}-{i}.png"
        urllib.request.urlretrieve(url, dest)
        print(dest)
    log_spend(f"{a.what} x{len(outs)} {a.quality} {a.ar}", PRICE.get(a.quality, 0.5) * len(outs))


if __name__ == "__main__":
    main()
