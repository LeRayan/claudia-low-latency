#!/usr/bin/env python3
"""Generate song takes with MiniMax Music 2.5 on Replicate from a song draft, and log spend.

usage: song_minimax.py audio/song-draft.md --out audio/minimax/half-the-size --takes 2
The draft's "Suno: Style field" becomes the prompt; its "Suno: Lyrics" become the lyrics, with section
cues reduced to MiniMax's plain tags ([Verse], [Chorus], ...).
"""
import argparse, csv, datetime, json, os, pathlib, re, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODEL = "minimax/music-2.5"
EST_COST = 0.15
TAGS = {"intro": "Intro", "verse": "Verse", "pre-chorus": "Pre Chorus", "pre chorus": "Pre Chorus",
        "chorus": "Chorus", "post-chorus": "Post Chorus", "bridge": "Bridge", "outro": "Outro",
        "hook": "Hook", "break": "Break"}


def load_env():
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))


def req(method, url, body=None):
    r = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body else None)
    r.add_header("Authorization", "Bearer " + os.environ["REPLICATE_API_TOKEN"])
    r.add_header("Content-Type", "application/json")
    r.add_header("User-Agent", "claudia-clips/1.0")
    try:
        with urllib.request.urlopen(r, timeout=120) as f:
            return json.load(f)
    except urllib.error.HTTPError as e:
        sys.exit(f"{e.code} {url}: {e.read()[:500]}")


def plain_tag(m):
    name = re.sub(r"\s*\d+$", "", m.group(1).split(" - ")[0].strip()).lower()
    return "[" + TAGS.get(name, name.title()) + "]"


def take(inp, dest):
    p = req("POST", f"https://api.replicate.com/v1/models/{MODEL}/predictions", {"input": inp})
    while p["status"] not in ("succeeded", "failed", "canceled"):
        time.sleep(5)
        p = req("GET", p["urls"]["get"])
    if p["status"] != "succeeded":
        return f"{dest}: {p['status']} {p.get('error')}"
    out = p["output"][0] if isinstance(p["output"], list) else p["output"]
    urllib.request.urlretrieve(out, dest)
    return str(dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("draft")
    ap.add_argument("--out", required=True)
    ap.add_argument("--takes", type=int, default=2)
    a = ap.parse_args()
    load_env()

    t = pathlib.Path(a.draft).read_text()
    style = re.search(r"## Suno: Style field\n\n```\n(.*?)\n```", t, re.S).group(1)
    lyrics = re.sub(r"\[([^\]]+)\]", plain_tag, re.search(r"## Suno: Lyrics\n\n```\n(.*?)\n```", t, re.S).group(1))
    inp = {"prompt": style, "lyrics": lyrics, "audio_format": "mp3"}
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    (out.parent / (out.name + ".input.json")).write_text(json.dumps(inp, indent=1))

    dests = [out.parent / f"{out.name}-take{i}.mp3" for i in range(1, a.takes + 1)]
    with ThreadPoolExecutor(a.takes) as ex:
        results = list(ex.map(lambda d: take(inp, d), dests))
    print("\n".join(results))

    done = sum(1 for d in dests if d.exists())
    if not (ROOT / "spend.csv").exists():
        (ROOT / "spend.csv").write_text("date,model,what,est_cost\n")
    with (ROOT / "spend.csv").open("a", newline="") as f:
        csv.writer(f).writerow([datetime.date.today().isoformat(), MODEL, f"song {out.name} x{done}",
                                f"{EST_COST * done:.3f}"])


if __name__ == "__main__":
    main()
