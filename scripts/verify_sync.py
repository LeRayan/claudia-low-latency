#!/usr/bin/env python3
"""Measure sync instead of trusting it: where the song sits in a take, whether her lips match the vocal, whether each
lyric lands on its word.

    verify_sync.py take  TAKE.mp4 --vocal STEM --at T0 --dur D        -> seconds to trim from the take's start
    verify_sync.py lips  VIDEO --clock CLOCK.json [--cuts a,b,c]     -> lip offset per shot (+ = lips late), PASS/FAIL
    verify_sync.py words CLOCK.json --vocal STEM [--fix OUT.json]       -> each word's time vs the vocal's attack

Rules of thumb (what we measured on LOW LATENCY and RUN FREE):
  * Never assume a lead-in survived. Match the syllable attacks of the take's own audio against the stem and trim to
    the match. Envelope and even raw-waveform correlation fooled us: at 122 BPM a beat is ~0.5 s, and loudnorm
    reshapes the waveform, so both peaked "one beat late" as often as on time. Attack timing doesn't.
  * Lips: on every word that starts with b/p/m/f/v the lips must close just before the sound. The median offset of
    those closures per shot must be within 150 ms (natural singing closes 40-120 ms early). Mouth opening comes from
    MediaPipe FaceLandmarker (inner lips / face height). Validated on RUN FREE: the cut with the lead-in bug measured
    -583 ms on the broken shots, the fixed cut -125..0 ms. Score all of a shot's lip words together over every shift;
    with fewer than 3 such words a shot is UNSURE and you look at the word strip (red frame = lips should be closed).
    Don't correlate mouth opening with loudness (singing closes the mouth on loud consonants: it read a correct take
    as 250 ms early), and don't pick the nearest closure per word (there is always one within a few frames).
  * Words: a lyric should appear 1 frame before its attack; |error| <= 80 ms passes.
Needs numpy and ffmpeg; `lips` also needs mediapipe (pip install mediapipe; the model downloads on first use).
"""
import argparse, json, os, pathlib, subprocess, sys, urllib.request
import numpy as np

SR = 16000
FPS = 24
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
MODEL = pathlib.Path(os.path.expanduser("~/.cache/claudia-clips/face_landmarker.task"))


def load(f, ss=None, t=None):
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", str(ss)] if ss is not None else []) + (["-t", str(t)] if t else []) + \
          ["-i", str(f), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32)


def _xcorr_peak(ref, x, max_s):
    """Seconds that `ref` sits late inside `x`, from raw-waveform cross-correlation, and the peak's strength (0-1)."""
    n = 1 << int(np.ceil(np.log2(len(ref) + len(x))))
    c = np.fft.irfft(np.fft.rfft(x, n) * np.conj(np.fft.rfft(ref, n)), n)
    m = int(max_s * SR)
    lags = np.concatenate([np.arange(m + 1), np.arange(-m, 0)])
    cand = np.concatenate([c[:m + 1], c[-m:]])
    i = int(np.argmax(cand))
    # normalise by the energy of the overlapping part of x
    L = lags[i]
    seg = x[max(0, L):max(0, L) + len(ref)]
    strength = float(cand[i] / (np.sqrt((ref[:len(seg)] ** 2).sum() * (seg ** 2).sum()) + 1e-9))
    return L / SR, strength


def onsets(x, min_quiet=0.15):
    """Times (s) where the voice starts again after at least `min_quiet` of quiet: phrase starts. Robust to gain
    changes (loudnorm, compression) and to beat-periodic music, unlike waveform or envelope correlation."""
    hop = SR // 100
    n = len(x) // hop
    e = 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)
    quiet = e < np.percentile(e, 70) - 12
    out, run = [], 0
    for i, q in enumerate(quiet):
        if q:
            run += 1
        else:
            if run >= min_quiet * 100:
                out.append(i / 100)
            run = 0
    return np.array(out)


def attack_times(x, pct=85, gap=0.1):
    """Syllable attacks (s): peaks of spectral flux (full band + >3 kHz), at least `gap` apart."""
    hop, win = SR // 100, 512
    n = (len(x) - win) // hop
    if n < 10:
        return np.array([])
    fr = np.lib.stride_tricks.sliding_window_view(x, win)[::hop][:n] * np.hanning(win)
    S = np.abs(np.fft.rfft(fr))
    full = np.log(S.sum(1) + 1e-6)
    hi = np.log(S[:, int(3000 / (SR / win)):].sum(1) + 1e-6)
    on = np.maximum(0, np.diff(full, prepend=full[0])) + np.maximum(0, np.diff(hi, prepend=hi[0]))
    thr = np.percentile(on, pct)
    peaks, last = [], -1e9
    for i in np.argsort(-on):
        if on[i] < thr:
            break
        if all(abs(i - j) >= gap * 100 for j in peaks):
            peaks.append(i)
    return np.sort(np.array(peaks)) / 100


def take_offset(take, vocal, at, dur, search=(-1.0, 1.5), tol=0.03):
    """Seconds into the take where stem time `at` sits. Matches syllable attacks of stem[at:at+dur] against the take's
    own audio over every shift; returns (trim, hit share at best, hit share at runner-up 100+ ms away)."""
    a = attack_times(load(vocal, at, dur))
    b = attack_times(load(take))
    if len(a) < 3 or len(b) < 3:
        return 0.0, 0.0, 0.0
    score = {}
    for k in range(int(search[0] * 100), int(search[1] * 100) + 1):
        sft = k / 100
        score[sft] = float(np.mean([np.min(np.abs(b - (x + sft))) <= tol for x in a]))
    best = max(score, key=lambda s_: (score[s_], -abs(s_)))
    second = max(v for s_, v in score.items() if abs(s_ - best) >= 0.1)
    return best, score[best], second


# ----------------------------------------------------------------------------------------------------------- lips
def mouth_track(video, start=0.0, dur=None):
    """Mouth opening per frame (inner-lip gap / face height), NaN where no face."""
    import mediapipe as mp
    from mediapipe.tasks.python import vision, BaseOptions
    if not MODEL.exists():
        MODEL.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(MODEL_URL, MODEL)
    opts = vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=str(MODEL)),
                                        running_mode=vision.RunningMode.VIDEO, num_faces=1)
    w, h = map(int, subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                    "stream=width,height", "-of", "csv=p=0", str(video)],
                                   capture_output=True, text=True).stdout.strip().split(","))
    sw, sh = 640, int(640 * h / w) // 2 * 2
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start), "-i", str(video)] + (["-t", str(dur)] if dur else []) + \
          ["-vf", f"fps={FPS},scale={sw}:{sh}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, sh, sw, 3)
    out = []
    with vision.FaceLandmarker.create_from_options(opts) as lm:
        for i, f in enumerate(frames):
            r = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(f)),
                                    int(i * 1000 / FPS))
            if not r.face_landmarks:
                out.append(np.nan); continue
            p = r.face_landmarks[0]
            gap = abs(p[14].y - p[13].y)            # inner lips
            face = abs(p[152].y - p[10].y) + 1e-6   # chin to forehead
            out.append(gap / face)
    return np.array(out)


def mouth_center(frame, w, h):
    """Pixel position of her mouth in one frame (falls back to the frame centre)."""
    import mediapipe as mp
    from mediapipe.tasks.python import vision, BaseOptions
    opts = vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=str(MODEL)), num_faces=1)
    with vision.FaceLandmarker.create_from_options(opts) as lm:
        r = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(frame)))
    if not r.face_landmarks:
        return w / 2, h / 2
    p = r.face_landmarks[0]
    return (p[13].x + p[14].x) / 2 * w, (p[13].y + p[14].y) / 2 * h


def word_strip(video, words, out, before=0.25, after=0.17):
    """For each b/p/m/f/v word, a row of mouth crops from `before` to `after` around it; the frame where the lips should
    be closed has a red border. This is what you look at when the numbers can't decide."""
    from PIL import Image, ImageDraw
    w, h = map(int, subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                    "stream=width,height", "-of", "csv=p=0", str(video)],
                                   capture_output=True, text=True).stdout.strip().split(","))
    rows = []
    for wd in words:
        t = wd["t"] - 0.04
        n = int((before + after) * FPS)
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, t - before):.3f}", "-i", str(video), "-frames:v",
                              str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        fr = np.frombuffer(raw, np.uint8)[:n * w * h * 3].reshape(-1, h, w, 3)
        if not len(fr):
            continue
        cx, cy = mouth_center(fr[len(fr) // 2], w, h)
        box = (int(cx - w * .12), int(cy - h * .2), int(cx + w * .12), int(cy + h * .1))
        row = Image.new("RGB", (120 * len(fr), 150 + 18), "white")
        d = ImageDraw.Draw(row)
        d.text((4, 2), f"{wd['word']} @ {wd['t']:.2f}s", fill="black")
        for k, f_ in enumerate(fr):
            tile = Image.fromarray(f_).crop(box).resize((120, 150))
            row.paste(tile, (120 * k, 18))
            if k == int(before * FPS):
                d.rectangle([120 * k, 18, 120 * k + 119, 167], outline="red", width=3)
        rows.append(row)
    if rows:
        sheet = Image.new("RGB", (max(r.width for r in rows), sum(r.height for r in rows)), "white")
        y = 0
        for r in rows:
            sheet.paste(r, (0, y)); y += r.height
        sheet.save(out)


def cmd_lips(a):
    total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                  str(a.video)], capture_output=True, text=True).stdout)
    cuts = [float(c) for c in a.cuts.split(",")] if a.cuts else [0.0, total]
    words = json.load(open(a.clock))["words"]
    fails = 0
    print(f"{'shot':>4} {'from':>7} {'to':>7}  lips(ms)  margin  verdict")
    for k, (t0, t1) in enumerate(zip(cuts, cuts[1:])):
        sft, margin, used = closure_lag(a.video, words, t0, t1, a.offset)
        if sft is None:
            verdict = "UNSURE (no b/p/m/f/v word in this shot)"
        elif len(used) < 3 or margin < a.min_margin:
            verdict = f"UNSURE ({len(used)} lip words, margin {margin:.2f}: look at the strip)"
        elif abs(sft * 1000) <= a.tol:
            verdict = "PASS"
        else:
            verdict = "FAIL"; fails += 1
        if verdict != "PASS" and a.strips:
            pathlib.Path(a.strips).mkdir(parents=True, exist_ok=True)
            lw = [w for w in words if w["word"].strip(" ,.!?\"'").lower()[:1] in LIP_START and t0 + 0.3 <= w["t"] < t1 - 0.2]
            if lw:
                word_strip(a.video, lw, pathlib.Path(a.strips) / f"shot{k + 1:02d}.jpg")
            verdict += f"  strip: {a.strips}/shot{k + 1:02d}.jpg"
        ms = f"{sft * 1000:+6.0f}" if sft is not None else "     -"
        print(f"{k + 1:>4} {t0:7.2f} {t1:7.2f}  {ms}  {margin:6.2f}  {verdict}   ({' '.join(used)})")
    sys.exit(1 if fails else 0)

# ------------------------------------------------------------------------------------------------- lips: closures
LIP_START = ("b", "p", "m", "f", "v")


def closure_lag(video, clock_words, t0, t1, offset=0.0, search=(-0.75, 0.5)):
    """Lip sync from phonetics: on words that start with b/p/m/f/v the lips close just before the sound releases.
    Tries every shift of the whole shot and scores how closed the mouth is at all those words together; the true
    offset is where they are all closed at once. Returns (shift s, + = lips late; margin over the best shift that is
    >= 0.25 s away, in the mouth's own spread; the words used). Per-word picks don't work: singing closes the mouth
    every few frames, so a nearest closure always exists, even for a take that is half a second off."""
    mouth = mouth_track(video, t0, t1 - t0)
    ok = ~np.isnan(mouth)
    if ok.sum() < FPS:
        return None, 0.0, []
    z = (mouth - np.nanmean(mouth)) / (np.nanstd(mouth) + 1e-9)
    z = np.where(ok, z, 0.0)
    used = [w for w in clock_words
            if (w["word"].strip(" ,.!?\"'").lower()[:1] in LIP_START) and t0 + 0.3 <= w["t"] < t1 - 0.2]
    if not used:
        return None, 0.0, []
    score = {}
    for k in range(int(search[0] * FPS), int(search[1] * FPS) + 1):
        vals = []
        for w in used:
            i = int(round((w["t"] - 0.04 - t0 + offset) * FPS)) + k
            if 1 <= i < len(z) - 1:
                vals.append(z[i - 1:i + 2].min())      # closed at the closure, give or take a frame
        if vals:
            score[k / FPS] = float(np.mean(vals))
    best = min(score, key=score.get)
    far = [v for s_, v in score.items() if abs(s_ - best) >= 0.25]
    margin = (min(far) - score[best]) if far else 0.0
    return best, margin, [w["word"].strip(" ,.!?\"'").lower() for w in used]

# ----------------------------------------------------------------------------------------------------------- words
def attacks(vocal):
    """Onset strength of the vocal at 10 ms: rise of full-band + >3 kHz energy (consonants)."""
    x = load(vocal)
    hop, win = SR // 100, 512
    n = (len(x) - win) // hop
    fr = np.lib.stride_tricks.sliding_window_view(x, win)[::hop][:n] * np.hanning(win)
    S = np.abs(np.fft.rfft(fr))
    full = np.log(S.sum(1) + 1e-6)
    hi = np.log(S[:, int(3000 / (SR / win)):].sum(1) + 1e-6)
    on = np.maximum(0, np.diff(full, prepend=full[0])) + np.maximum(0, np.diff(hi, prepend=hi[0]))
    return on


def cmd_words(a):
    """Report each word against the vocal's attacks; with --fix, snap words to their own attack and write a new clock.
    Snapping keeps the words in order, uses each attack once, and only moves a word when a clear attack sits within
    [-160, +80] ms of it (clocks from Suno run late, so look mostly earlier)."""
    data = json.load(open(a.clock))
    words = data["words"]
    on = attacks(a.vocal)
    strong = np.percentile(on, 90)
    bad, prev_t, used, moved = 0, -1.0, set(), 0
    print(f"{'word':>12} {'clock':>7} {'attack':>7} {'err ms':>7}")
    for w in words:
        lo, hi = int((w["t"] - 0.16) * 100), int((w["t"] + 0.08) * 100)
        cand = [i for i in range(max(0, lo), min(len(on), hi)) if on[i] >= strong and i not in used and i / 100 > prev_t
                and on[i] == on[max(0, i - 3):i + 4].max()]
        if not cand:
            print(f"{w['word'][:12]:>12} {w['t']:7.2f}       -       -   (no clear attack: check by eye)")
            prev_t = w["t"]
            continue
        i = min(cand, key=lambda j: abs(j / 100 - w["t"]))
        t_att = i / 100
        err = (w["t"] - t_att) * 1000
        flag = "" if abs(err) <= a.tol else "  <-- off"
        bad += bool(flag)
        print(f"{w['word'][:12]:>12} {w['t']:7.2f} {t_att:7.2f} {err:+7.0f}{flag}")
        if a.fix and abs(err) > 20:
            w["t"] = round(t_att, 3); w["src"] = "attack"; moved += 1
        used.add(i)
        prev_t = w["t"]
    print(f"\n{bad} of {len(words)} words more than {a.tol:.0f} ms from an attack")
    if a.fix:
        for x, y in zip(words, words[1:]):
            assert y["t"] > x["t"], ("clock must be strictly increasing", x, y)
        json.dump(data, open(a.fix, "w"), indent=1)
        print(f"moved {moved} words to their attack -> {a.fix}")
    sys.exit(1 if bad and not a.fix else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    t = sp.add_parser("take"); t.add_argument("take"); t.add_argument("--vocal", required=True)
    t.add_argument("--at", type=float, required=True); t.add_argument("--dur", type=float, required=True)
    l = sp.add_parser("lips"); l.add_argument("video"); l.add_argument("--clock", required=True)
    l.add_argument("--cuts", help="shot boundaries in seconds, comma separated"); l.add_argument("--offset", type=float, default=0.0,
                   help="where the video's t=0 sits in the vocal (s)"); l.add_argument("--tol", type=float, default=150)
    l.add_argument("--min-margin", type=float, default=0.3, help="below this the shot is UNSURE")
    l.add_argument("--strips", help="folder for mouth-crop strips of shots that don't pass")
    w = sp.add_parser("words"); w.add_argument("clock"); w.add_argument("--vocal", required=True)
    w.add_argument("--tol", type=float, default=80)
    w.add_argument("--fix", help="write a corrected clock here (words snapped to their own attack)")
    a = ap.parse_args()
    if a.cmd == "take":
        s, best, second = take_offset(a.take, a.vocal, a.at, a.dur)
        sure = best >= 0.5 and best - second >= 0.15
        print(f"trim {s:.2f} s  ({best:.0%} of attacks match; next best {second:.0%}){'' if sure else '  CHECK BY EYE'}")
    elif a.cmd == "lips":
        cmd_lips(a)
    else:
        cmd_words(a)


if __name__ == "__main__":
    main()
