"""The lyric sheet with timings: line windows (bar map + listening) and per-word start times.

Word times come from Whisper on both the mix and the isolated vocal (each drops different words); a lyric word takes
the time of the next matching transcript word inside its line window, and unmatched words are spread by length.
"""
import json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from project import P, path  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


LINE_WINDOWS = [tuple(x) for x in P["lines"]]  # (start, end, text), per film in projects/<name>.json
words = sorted([c for f in P["words"] for c in json.load(open(ROOT / f))["chunks"]], key=lambda c: c["timestamp"][0])
norm = lambda w: re.sub(r"[^a-z']", "", w.lower())


def word_times(start, end, text):
    """Start time of each word in a line: Whisper's time when the next unmatched Whisper word in the window agrees,
    otherwise spread evenly by length between its neighbours."""
    toks = text.split()
    pool = [(c["timestamp"][0], norm(c["text"])) for c in words if start - 0.3 <= c["timestamp"][0] < end]
    times, j = [None] * len(toks), 0
    for i, tk in enumerate(toks):
        for k in range(j, len(pool)):
            if pool[k][1] == norm(tk):
                times[i], j = pool[k][0], k + 1
                break
    times[0] = times[0] if times[0] is not None else start
    known = [i for i, t in enumerate(times) if t is not None] + [len(toks)]
    edge = lambda i: times[i] if i < len(toks) else end - 0.25
    for a, b in zip(known, known[1:]):
        span, total = edge(b) - times[a], sum(len(t) for t in toks[a:b])
        acc = 0
        for i in range(a + 1, b):
            acc += len(toks[i - 1])
            times[i] = times[a] + span * acc / total
    return [max(start, min(t, end - 0.1)) for t in times]


LINES = [(a, b, txt, word_times(a, b, txt)) for a, b, txt in LINE_WINDOWS]
