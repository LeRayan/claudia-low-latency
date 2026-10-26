"""Which film the pipeline works on. CLIP_PROJECT=v2 (the default) loads projects/v2.json, LOW LATENCY. Every script
reads its board, song, stems, lyric lines and output folders from here."""
import json, os, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
NAME = os.environ.get("CLIP_PROJECT", "v2")
P = json.load(open(ROOT / "projects" / f"{NAME}.json"))


def path(key):
    return ROOT / P[key]
