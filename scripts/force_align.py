#!/usr/bin/env python3
"""Forced alignment of the KNOWN lyric on the isolated vocal (anabology's toolkit #5), with a confidence per word.

usage: .venv-align/bin/python scripts/force_align.py VOCAL.wav LYRICS.txt OUT.json [--chunks words.json]
wav2vec2 CTC (facebook/wav2vec2-large-960h-lv60-self) gives letter probabilities every 20 ms; a Viterbi pass walks the
sheet's letters through them. Long songs are aligned line by line inside windows taken from a rough timing
(--chunks, e.g. Suno's alignment), padded 1.5 s each side, so one bad line can't drag the rest.
Output: [{word, line, t0, t1, conf}] ; conf = mean letter probability over the word's frames.
"""
import json, re, sys
import numpy as np, soundfile as sf, torch
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

MODEL = "facebook/wav2vec2-large-960h-lv60-self"
SR = 16000


def load(path):
    import subprocess
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def viterbi(logp, tokens, blank):
    """CTC forced alignment: best path of `tokens` through frame log-probs; returns the frame of each token."""
    T, S = logp.shape[0], len(tokens)
    L = 2 * S + 1
    ext = [blank if i % 2 == 0 else tokens[i // 2] for i in range(L)]
    NEG = -1e9
    dp = np.full((T, L), NEG, np.float32)
    bp = np.zeros((T, L), np.int8)
    dp[0, 0] = logp[0, ext[0]]
    if L > 1:
        dp[0, 1] = logp[0, ext[1]]
    for t in range(1, T):
        prev = dp[t - 1]
        stay = prev
        step = np.concatenate([[NEG], prev[:-1]])
        skip = np.concatenate([[NEG, NEG], prev[:-2]])
        allow = np.array([i % 2 == 1 and i >= 2 and ext[i] != ext[i - 2] for i in range(L)])
        skip = np.where(allow, skip, NEG)
        cand = np.stack([stay, step, skip])
        bp[t] = cand.argmax(0)
        dp[t] = cand.max(0) + logp[t, ext]
    i = L - 1 if dp[-1, L - 1] >= dp[-1, L - 2] else L - 2
    path = []
    for t in range(T - 1, -1, -1):
        path.append((t, i))
        i -= bp[t, i]
    path.reverse()
    return [(t, i // 2) for t, i in path if i % 2 == 1]  # (frame, token index) for non-blank states


def main():
    vocal, lyr, out = sys.argv[1], sys.argv[2], sys.argv[3]
    chunks = None
    if "--chunks" in sys.argv:
        chunks = json.load(open(sys.argv[sys.argv.index("--chunks") + 1]))["chunks"]
    proc = Wav2Vec2Processor.from_pretrained(MODEL)
    model = Wav2Vec2ForCTC.from_pretrained(MODEL).eval()
    vocab = proc.tokenizer.get_vocab()
    blank = vocab["<pad>"]
    audio = load(vocal)
    lines = [l.strip() for l in open(lyr).read().splitlines() if l.strip()]
    # rough windows per line from the chunks (word order matches the sheet)
    flat = [(c["timestamp"][0], c["timestamp"][1], c["text"]) for c in chunks] if chunks else None
    res, wi = [], 0
    norm = lambda w: re.sub(r"[^A-Z']", "", w.upper())
    for li, line in enumerate(lines):
        words = [w for w in line.split() if norm(w)]
        if flat:
            seg = flat[wi:wi + len(words)]
            wi += len(words)
            a, b = max(0, seg[0][0] - 1.5), seg[-1][1] + 1.5
        else:
            a, b = 0, len(audio) / SR
        x = audio[int(a * SR):int(b * SR)]
        with torch.no_grad():
            iv = proc(x, sampling_rate=SR, return_tensors="pt").input_values
            logp = torch.log_softmax(model(iv).logits[0], -1).numpy()
        hop = (len(x) / SR) / logp.shape[0]
        text = "|".join(norm(w) for w in words)
        toks = [vocab.get(c, vocab.get("|")) for c in text]
        path = viterbi(logp, toks, blank)
        # map token -> frames, then letters -> words
        tf = {}
        for t, k in path:
            tf.setdefault(k, []).append(t)
        k = 0
        for w in words:
            n = len(norm(w))
            idx = list(range(k, k + n))
            fr = [t for j in idx for t in tf.get(j, [])]
            if fr:
                probs = [float(np.exp(logp[t, toks[j]])) for j in idx for t in tf.get(j, [])]
                res.append({"word": w, "line": li, "t0": round(a + min(fr) * hop, 3), "t1": round(a + (max(fr) + 1) * hop, 3),
                            "conf": round(float(np.mean(probs)), 3)})
            else:
                res.append({"word": w, "line": li, "t0": None, "t1": None, "conf": 0.0})
            k += n + 1  # skip the word separator
        print(f"line {li:2d} [{a:6.1f}-{b:6.1f}] " + " ".join(f"{r['word']}@{r['t0']}({r['conf']:.2f})"
                                                         for r in res[-len(words):]), flush=True)
    json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
