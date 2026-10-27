#!/usr/bin/env python3
"""BiRefNet matte for every frame in a folder, in parallel on Replicate; resumable; logs spend.
usage: python3 scripts/birefnet_frames.py FRAMES_DIR MATTES_DIR"""
import base64, csv, datetime, glob, json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for l in open(os.path.join(ROOT, ".env")):
    if "=" in l: k, v = l.strip().split("=", 1); os.environ.setdefault(k, v.strip('"'))
H = {"Authorization": "Bearer " + os.environ["REPLICATE_API_TOKEN"], "Content-Type": "application/json",
     "User-Agent": "claudia-clips/1.0", "Prefer": "wait=60"}
V = "f74986db0355b58403ed20963af156525e2891ea3c2d499bfbfb2a28cd87c5d7"
def call(m, u, b=None):
    for k in range(5):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u, method=m, headers=H,
                             data=json.dumps(b).encode() if b else None), timeout=120))
        except Exception as e:
            err = e; time.sleep(3 * (k + 1))
    raise err
def run(f):
    out = os.path.join(sys.argv[2], os.path.basename(f).replace(".jpg", ".png"))
    if os.path.exists(out): return 0
    uri = "data:image/jpeg;base64," + base64.b64encode(open(f, "rb").read()).decode()
    p = call("POST", "https://api.replicate.com/v1/predictions", {"version": V, "input": {"image": uri}})
    while p["status"] not in ("succeeded", "failed", "canceled"):
        time.sleep(1.5); p = call("GET", p["urls"]["get"])
    if p["status"] != "succeeded": return 0
    o = p["output"]; o = o[0] if isinstance(o, list) else o
    urllib.request.urlretrieve(o, out)
    return (p.get("metrics") or {}).get("predict_time", 0)
fs = sorted(glob.glob(os.path.join(sys.argv[1], "*.jpg")))
with ThreadPoolExecutor(16) as ex: pt = list(ex.map(run, fs))
missing = [f for f in fs if not os.path.exists(os.path.join(sys.argv[2], os.path.basename(f).replace(".jpg", ".png")))]
print(len(fs), "frames,", len(missing), "missing, gpu s", round(sum(pt)))
if not os.path.exists(os.path.join(ROOT, "spend.csv")):
    open(os.path.join(ROOT, "spend.csv"), "w").write("date,model,what,est_cost\n")
csv.writer(open(os.path.join(ROOT, "spend.csv"), "a", newline="")).writerow(
    [datetime.date.today().isoformat(), "men1scus/birefnet", f"per-frame mattes {len(fs)-len(missing)} frames", f"{sum(pt)*0.000725:.3f}"])
