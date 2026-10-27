#!/usr/bin/env python3
"""Claudia sings it: one command from a voice clip to a finished, lip-synced shot with the film's lyric typography.

    python quickstart.py                                   # the demo: the LOW LATENCY chorus, about $0.60
    python quickstart.py --song my_suno_song.mp3 --start 42 --lyrics "the words"   # 20 s of any song, from 0:42
    python quickstart.py --audio my_voice.m4a              # Claudia sings YOUR recording (10-20 s works best)
    python quickstart.py --audio my_voice.m4a --lyrics "the words you sing"   # better word timing
    python quickstart.py --plate L03                       # any of the 20 film plates (v2/plates/), or your own image

What happens (each step is a script in this repo):
  0. --song: Demucs splits out the vocal                             (scripts/vocals.py, ~10 s, about $0.01)
  1. your audio -> mono, loudness-normalised, a 0.5 s lead-in       (the avatar model needs it; trimmed after)
  2. Pruna p-video-2-pro-avatar: the plate sings your audio           (scripts/avatar.py, $0.04 per second)
  3. word timing: WhisperX on Replicate                               (skipped for the demo: its words are measured)
  4. BiRefNet cuts her out of every frame                             (scripts/birefnet_frames.py, ~$0.0004 a frame)
  5. every line becomes a typographic lockup BEHIND her, word by word (edit/lockups.py)
Needs: .env with PRUNA_API_KEY and REPLICATE_API_TOKEN, ffmpeg, and `pip install -r requirements.txt`.
"""
import argparse, json, pathlib, re, shutil, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent
Q = ROOT / "assets/quickstart"
sys.path.insert(0, str(ROOT / "scripts"))

PROMPT = ("A cinematic 35mm music video shot. She sings this song with joy, like a real singer on stage: her head turns "
          "and tilts naturally with the phrases, she looks out over the crowd and back into the lens, relaxed natural "
          "blinks. Camera: eye level, a gentle drift toward her. Her lips, jaw and tongue match every syllable exactly. "
          "Her mood is joyful and euphoric: warm smiling eyes, wide open and bright, mouth wide open on the vowels. "
          "Never snarling, never sneering, never sultry: no half-closed eyes, no pout, no smirk. No bouncing: her "
          "shoulders and body stay steady; her energy comes from her face, eyes and hands. "
          "When the voice is silent her lips are closed. Her face, hair, purple streak, star clip, headset mic and "
          "outfit stay exactly as in the image; she stays the same 28-year-old woman.")
STOP = set("a an the and or but nor so to of in on at by for from with into onto up as if than that this these those "
           "it its it's i i'm im i've ive i'll ill you you're your yours we our us they them their he she his her "
           "is are was were be been am do does did just all my me's oh".split())
PREROLL = 0.5


def sh(*cmd, **kw):
    r = subprocess.run([str(c) for c in cmd], **kw)
    if r.returncode:
        sys.exit(f"failed: {' '.join(map(str, cmd))[:200]}")
    return r


def seconds(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                 str(path)], capture_output=True, text=True).stdout)


def transcribe(wav, lyrics):
    """WhisperX on Replicate (Whisper large-v3 + wav2vec2 alignment) -> {"words": [{word, t, end}]}."""
    import transcribe as tx
    tx.load_env()
    print("· word timing (WhisperX)…", flush=True)
    chunks = tx.whisperx(wav, lyrics)["chunks"]
    words = [{"word": c["text"].strip(), "t": round(c["timestamp"][0], 3), "end": round(c["timestamp"][1], 3)}
             for c in chunks if re.search(r"[A-Za-z0-9]", c["text"] or "")]
    return {"words": words}


def auto_spec(words):
    """Lines from pauses; filler words become small italic rows, the rest CAPS rows of at most ~10 letters."""
    groups, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        stop_here = re.search(r"[.!?,;:]$", w["word"].strip())  # a sentence or clause ends: so does the line
        natural = not nxt or stop_here or nxt["t"] - w["end"] > 0.35
        if natural or len(cur) >= 7 or nxt["t"] - cur[0]["t"] > 3.2:
            carry = []
            while not natural and len(cur) > 1 and cur[-1]["word"].strip(" ,.!?;:\"'").lower() in STOP:
                carry.insert(0, cur.pop())  # never end a line on a small word: it opens the next one
            groups.append(cur); cur = carry
    spec = []
    for g in groups:
        rows, run, ital = [], [], None
        for w in g:
            tok = w["word"].strip(" ,.!?;:\"'")  or w["word"].strip()
            is_stop = tok.lower() in STOP
            if run and (is_stop != ital or (not ital and len(" ".join(run + [tok])) > 10)):
                rows.append(("~" + " ".join(run).lower()) if ital else " ".join(run).upper()); run = []
            run.append(tok); ital = is_stop
        if run:
            rows.append(("~" + " ".join(run).lower()) if ital else " ".join(run).upper())
        if all(r.startswith("~") for r in rows):  # a line of only small words still needs a body
            rows = [r.lstrip("~").upper() for r in rows]
        spec.append({"k": "hook" if len(g) <= 4 else "verse", "punch": True, "rows": rows})
    return {"groups": spec}


def credit(video, out, text="Claudia by anabology  ·  made with Pruna"):
    """A small credit, bottom right, on every clip people share."""
    from PIL import Image, ImageDraw, ImageFont
    w, h = map(int, subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                    "stream=width,height", "-of", "csv=p=0", str(video)],
                                   capture_output=True, text=True).stdout.strip().split(","))
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    hn = pathlib.Path("/System/Library/Fonts/HelveticaNeue.ttc")
    f = ImageFont.truetype(str(hn), int(h * 0.024), index=1) if hn.exists() else \
        ImageFont.truetype(str(ROOT / "assets/fonts/Anton-Regular.ttf"), int(h * 0.024))
    tw = d.textlength(text, font=f)
    d.text((w - tw - h * 0.03 + 1, h * 0.95 + 1), text, font=f, fill=(0, 0, 0, 140))
    d.text((w - tw - h * 0.03, h * 0.95), text, font=f, fill=(255, 255, 255, 200))
    png = pathlib.Path(out).with_suffix(".credit.png"); im.save(png)
    sh("ffmpeg", "-v", "error", "-y", "-i", video, "-i", png, "-filter_complex", "[0:v][1:v]overlay=0:0",
       "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "copy", out)
    png.unlink()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--song", help="a full song (a Suno track works): she sings its vocal, the song plays under her")
    ap.add_argument("--start", type=float, default=0.0, help="where in --song to start, in seconds")
    ap.add_argument("--audio", help="a voice clip to sing (any format); default: the LOW LATENCY chorus")
    ap.add_argument("--soundtrack", help="what the final clip plays (default: your audio, or the full mix for the demo)")
    ap.add_argument("--lyrics", help="the words sung (helps the timing; with --song, no lyrics are drawn without it)")
    ap.add_argument("--plate", default=str(Q / "plate.jpg"), help="an image of her, or a film plate id like L03")
    ap.add_argument("--max", type=float, default=20.0, help="longest clip in seconds (cost is $0.04/s)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--prompt", default=PROMPT)
    ap.add_argument("--out")
    a = ap.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} is missing: install ffmpeg first")
    env = (ROOT / ".env").read_text() if (ROOT / ".env").exists() else ""
    for k in ("PRUNA_API_KEY", "REPLICATE_API_TOKEN"):
        if not re.search(rf"^{k}=\S", env, re.M):
            sys.exit(f"{k} is missing: copy .env.example to .env and fill it in")
    if a.song and a.audio:
        sys.exit("pass --song or --audio, not both")
    demo = a.audio is None and a.song is None
    plate = ROOT / "v2/plates" / f"{a.plate}.jpg" if re.fullmatch(r"L\d\d", a.plate) else pathlib.Path(a.plate)
    if not plate.exists():
        sys.exit(f"no such plate: {plate}")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    work = ROOT / "out" / f"work-{stamp}"; work.mkdir(parents=True)
    out = pathlib.Path(a.out) if a.out else ROOT / "out" / f"claudia-{stamp}.mp4"
    t0 = time.time()

    # 1. audio: mono, loudness-normalised, capped, plus the lead-in the avatar model wants
    src = Q / "vocal.wav" if demo else pathlib.Path(a.song or a.audio)
    if a.song:  # lip-sync from her vocal alone (the full mix gives mushy mouths); the song itself plays under her
        window = work / "song.wav"
        sh("ffmpeg", "-v", "error", "-y", "-ss", a.start, "-i", src, "-t", a.max, "-ar", "44100", window)
        print("· splitting out the vocal (Demucs)…", flush=True)
        import vocals
        src = vocals.separate(window, work / "song-vocal.wav")
        a.soundtrack = a.soundtrack or str(window)
    voice, lead = work / "voice.wav", work / "voice-lead.wav"
    sh("ffmpeg", "-v", "error", "-y", "-i", src, "-t", a.max, "-ac", "1", "-ar", "44100",
       "-af", "loudnorm=I=-16:TP=-1.5", voice)
    dur = seconds(voice)
    sh("ffmpeg", "-v", "error", "-y", "-i", voice, "-af", f"adelay={int(PREROLL * 1000)}", lead)
    track = work / "soundtrack.wav"
    st = Q / "mix.m4a" if demo and not a.soundtrack else pathlib.Path(a.soundtrack or src)
    sh("ffmpeg", "-v", "error", "-y", "-i", st, "-t", dur, "-ar", "44100", track)
    print(f"· {dur:.1f} s of audio → about ${dur * 0.04 + dur * 24 * 0.0004 + (0 if demo else 0.01) + (0.01 if a.song else 0):.2f}", flush=True)

    # 2. the plate sings it (Pruna p-video-2-pro-avatar)
    print("· rendering her (Pruna p-video-2-pro-avatar, ~1-3 min)…", flush=True)
    take = work / "take.mp4"
    sh(sys.executable, ROOT / "scripts/avatar.py", "--image", plate, "--audio", lead, "--prompt", a.prompt,
       "--out", take, "--seed", a.seed, "--what", "quickstart avatar", stdout=subprocess.DEVNULL)
    clip = work / "clip.mp4"  # drop the lead-in, 24 fps, the soundtrack under it
    sh("ffmpeg", "-v", "error", "-y", "-ss", PREROLL, "-i", take, "-i", track, "-t", dur, "-map", "0:v", "-map", "1:a",
       "-vf", "fps=24,scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "256k", clip)

    # 3. word timing
    words = work / "words.json"
    if demo:
        shutil.copy(Q / "words.json", words)
    elif a.song and not a.lyrics:  # speech recognition on a sung mix guesses words: lyrics only when you give them
        words.write_text(json.dumps({"words": []}))
    else:
        words.write_text(json.dumps(transcribe(voice, a.lyrics), indent=1))
    clock = json.loads(words.read_text())["words"]
    print(f"· {len(clock)} words: {' '.join(w['word'] for w in clock)[:120]}", flush=True)

    # 4. her matte, every frame
    print("· cutting her out of every frame (BiRefNet)…", flush=True)
    frames, mattes = work / "frames", work / "mattes"; frames.mkdir(); mattes.mkdir()
    sh("ffmpeg", "-v", "error", "-y", "-i", clip, "-q:v", "2", frames / "f%04d.jpg")
    sh(sys.executable, ROOT / "scripts/birefnet_frames.py", frames, mattes, stdout=subprocess.DEVNULL)
    alpha = work / "alpha.mp4"
    sh(sys.executable, ROOT / "scripts/matte_build.py", mattes, alpha, "--start", "0", stdout=subprocess.DEVNULL)

    # 5. the lyrics, behind her
    if clock:
        print("· setting the lyrics…", flush=True)
        spec = work / "lockups.json"
        spec.write_text(json.dumps(json.loads((Q / "lockups.json").read_text()) if demo else auto_spec(clock), indent=1))
        lyr = work / "lyrics.mp4"
        sh(sys.executable, ROOT / "edit/lockups.py", clip, alpha, lyr, "--clock", words, "--spec", spec,
           "--soundtrack", track, "--beatmap", "none", stdout=subprocess.DEVNULL)
    else:
        lyr = clip
    out.parent.mkdir(parents=True, exist_ok=True)
    credit(lyr, out)
    print(f"\n✓ {out}  ({time.time() - t0:.0f} s)\nCredit when you share: Claudia by @anabology, made with Pruna p-video")


if __name__ == "__main__":
    main()
