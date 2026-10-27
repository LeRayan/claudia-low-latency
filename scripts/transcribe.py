#!/usr/bin/env python3
"""Word-level transcription of song takes with Whisper on Replicate, and log spend.

usage: transcribe.py audio/suno/take1.wav [audio/suno/take2.wav ...]
       transcribe.py --whisperx --prompt-file lyrics.txt v2/audio/stems/vocals.wav   (forced-aligned words, best timing)
Writes <take>.words.json (chunks with [start, end] timestamps) next to each file and prints the words with times.
"""
import base64, csv, datetime, json, os, pathlib, subprocess, sys, tempfile, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODEL = "vaibhavs10/incredibly-fast-whisper"
WX_VERSION = "655845d6190ef70573c669245f245892cd039df4b880a1e3a65852c09252f5cc"  # victor-upmeet/whisperx
EST_COST = 0.01


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
    with urllib.request.urlopen(r, timeout=120) as f:
        return json.load(f)


def whisperx(path, prompt):
    """WhisperX: Whisper large-v3 then wav2vec2 forced alignment. Returns the same chunk format as transcribe()."""
    with tempfile.TemporaryDirectory() as tmp:
        mp3 = pathlib.Path(tmp) / "a.mp3"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-ac", "1", "-b:a", "96k", str(mp3)], check=True)
        uri = "data:audio/mpeg;base64," + base64.b64encode(mp3.read_bytes()).decode()
    inp = {"audio_file": uri, "language": "en", "align_output": True, "batch_size": 16}
    if prompt:
        inp["initial_prompt"] = prompt
    p = req("POST", "https://api.replicate.com/v1/predictions", {"version": WX_VERSION, "input": inp})
    while p["status"] not in ("succeeded", "failed", "canceled"):
        time.sleep(3)
        p = req("GET", p["urls"]["get"])
    if p["status"] != "succeeded":
        sys.exit(f"{path}: {p['status']} {p.get('error')}")
    words = [w for seg in p["output"]["segments"] for w in seg.get("words", []) if "start" in w]
    return {"chunks": [{"timestamp": [w["start"], w["end"]], "text": w["word"]} for w in words]}


def transcribe(path, version):
    with tempfile.TemporaryDirectory() as tmp:
        mp3 = pathlib.Path(tmp) / "a.mp3"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-ac", "1", "-b:a", "96k", str(mp3)], check=True)
        uri = "data:audio/mpeg;base64," + base64.b64encode(mp3.read_bytes()).decode()
    p = req("POST", "https://api.replicate.com/v1/predictions",
            {"version": version, "input": {"audio": uri, "timestamp": "word", "language": "english", "task": "transcribe"}})
    while p["status"] not in ("succeeded", "failed", "canceled"):
        time.sleep(3)
        p = req("GET", p["urls"]["get"])
    if p["status"] != "succeeded":
        sys.exit(f"{path}: {p['status']} {p.get('error')}")
    return p["output"]


def main():
    load_env()
    args, wx, prompt = sys.argv[1:], False, None
    if "--whisperx" in args:
        args.remove("--whisperx")
        wx = True
    if "--prompt-file" in args:
        i = args.index("--prompt-file")
        prompt = pathlib.Path(args[i + 1]).read_text()
        del args[i:i + 2]
    sys.argv = [sys.argv[0], *args]
    version = None if wx else req("GET", f"https://api.replicate.com/v1/models/{MODEL}")["latest_version"]["id"]
    for f in args:
        path = pathlib.Path(f)
        out = whisperx(path, prompt) if wx else transcribe(path, version)
        path.with_suffix(".wx.words.json" if wx else ".words.json").write_text(json.dumps(out, indent=1))
        print(f"== {path}")
        print(" ".join(f"{c['timestamp'][0]:.1f}:{c['text'].strip()}" for c in out.get("chunks", [])))
    if not (ROOT / "spend.csv").exists():
        (ROOT / "spend.csv").write_text("date,model,what,est_cost\n")
    with (ROOT / "spend.csv").open("a", newline="") as fh:
        csv.writer(fh).writerow([datetime.date.today().isoformat(), MODEL, f"transcribe x{len(sys.argv) - 1}",
                                 f"{EST_COST * (len(sys.argv) - 1):.3f}"])


if __name__ == "__main__":
    main()
