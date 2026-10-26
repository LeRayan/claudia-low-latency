#!/usr/bin/env python3
"""Generate plate candidates for every shot on the board that has a plate prompt, in parallel.

usage: plates.py [--only S03,S04] [--n 2] [--quality xhigh] [--board storyboard/board.json]
Writes plates/board/<id>.prompt.txt and plates/board/<id>-<k>.png via scripts/sunburst.py (which logs spend).
"""
import argparse, json, pathlib, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent


def run(shot, n, quality, out_dir="plates/board"):
    out = ROOT / out_dir
    out.mkdir(parents=True, exist_ok=True)
    pf = out / f"{shot['id']}.prompt.txt"
    pf.write_text(shot["plate_prompt"])
    cmd = [sys.executable, str(ROOT / "scripts/sunburst.py"), "--prompt-file", str(pf), "--out", str(out / shot["id"]),
           "--quality", quality, "--n", str(n), "--ar", "16:9", "--what", f"plate {shot['id']}"]
    for r in shot["refs"]:
        cmd += ["--ref", str(ROOT / r)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return shot["id"], p.returncode, (p.stdout + p.stderr).strip().splitlines()[-1:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--n", type=int, default=2)
    ap.add_argument("--quality", default="xhigh")
    ap.add_argument("--board", default=str(ROOT / "storyboard/board.json"))
    ap.add_argument("--out-dir", default="plates/board")
    a = ap.parse_args()
    shots = [s for s in json.load(open(a.board))["shots"] if s["plate_prompt"]]
    if a.only:
        keep = set(a.only.split(","))
        shots = [s for s in shots if s["id"] in keep]
    with ThreadPoolExecutor(8) as ex:
        for sid, rc, tail in ex.map(lambda s: run(s, a.n, a.quality, a.out_dir), shots):
            print(sid, "ok" if rc == 0 else f"FAILED {tail}")


if __name__ == "__main__":
    main()
