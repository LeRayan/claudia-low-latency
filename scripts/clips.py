#!/usr/bin/env python3
"""Cut each shot's audio window, write its H3 reference-mode prompt from the board, and render it with Pruna.

usage: clips.py [--only S01,S02] [--resolution 768p] [--seed 1001] [--tag v1] [--dry]
Outputs clips/board/<id>-<res>-<tag>.mp4 (+ .prompt.txt, .json). Spend is logged by scripts/pruna.py.
"""
import argparse, json, pathlib, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "edit"))
from project import P, path  # noqa: E402
BOARD = json.load(open(path("board")))

ID_TEXT = P["id_text"]
SPOKEN = set(P["spoken_sections"])


def delivery(section):
    if section in SPOKEN:
        return ("speaks the words in a close, dry, deadpan voice, every word crisp, a little amused, her lips, jaw and "
                "tongue in exact sync with every syllable of <Audio 1>")
    return ("sings in exact sync with <Audio 1>, her lips, jaw and tongue matching every syllable, the mouth opening wide "
            "on the held open vowels and closing between phrases")


sys.path.insert(0, str(ROOT / "edit"))
from lyrics import LINES  # (start, end, text, word start times)
ZONES = json.load(open(path("zones")))  # wide-stereo backing vocals (scripts/backing_zones.py)
in_zone = lambda t: any(a <= t < b for a, b in ZONES)
WORDS = [(w_t, w) for a, b, txt, ts in LINES for w_t, w in zip(ts, txt.split()) if not in_zone(w_t)]


def timeline(s, seg=2.0):
    """Per-segment lines of what the vocal holds, from Whisper word times relative to the window (their WHITEPILL
    method: the exact words, each tied to when it sounds)."""
    ws = [(t - s["start"], w) for t, w in WORDS if s["start"] - 0.05 <= t < s["end"] - 0.05]
    out, cur, t0 = [], [], None
    for t, w in ws:
        if t0 is None:
            t0 = int(t // seg * seg)
        if t >= t0 + seg and cur:
            out.append((t0, cur))
            cur, t0 = [], int(t // seg * seg)
        cur.append(w)
    if cur:
        out.append((t0, cur))
    verb = "says" if s["section"] in SPOKEN else "sings"
    return " ".join(f"From {a:.0f} s to {a + seg:.0f} s, in <Audio 1> she {verb} \"{' '.join(w)}\"; her lips form each of "
                    f"those words exactly when it sounds in <Audio 1>." for a, w in out)


CHOREO = ("Choreography: sharp, precise vogue-style arm and hand choreography on the beat: crisp geometric arm lines, "
          "hands framing her face, wrists snapping into poses, a shoulder isolation on each downbeat, one arm sweeping "
          "overhead and back. Her head and face stay steady and centred, facing the lens, calm and still, so all the dance "
          "is in her arms, hands and shoulders. Sharp and controlled, never bouncy.")
SILENT = ("This is an instrumental stretch: she does not sing or speak at all, her lips stay closed the whole shot, "
          "and <Audio 1> is silence.")


CHOREO_ON = False
SAME = P.get("same_line", "Her face is the same 28-year-old adult woman from <Picture 1> throughout: the same angular jaw, cheekbones, freckles and eyes, never younger.")


def prompt_for(s, vocal=False):
    heard = [w for tw, w in WORDS if s["start"] - 0.05 <= tw < s["end"] - 0.05]  # what she actually sings in this window
    lyric = " ".join(heard) if heard else re.sub(r"\s*/\s*\(Cut…\)", "", s["lyric"]).replace(" / ", ", ")
    lyric = lyric.rstrip(".") + "."
    is_night = "night" in s["set"]
    look_src = "<Picture 2>"
    return f"""subject_definitions:
<Subject 1> is Claudia, the woman whose identity comes from <Picture 1>, a ten-panel photographic sheet of her face from every angle with expressions, and whose outfit, pose and surroundings in this shot come from <Picture 2>. She is {ID_TEXT}. She wears {BOARD['look']}. <Picture 1> is only a reference for who she is; its grid, grey backdrop and black t-shirt never appear.
<Subject 2> is the setting of <Picture 2>: {s['set']}, exactly as shown there, with its light.
<Picture 2> is the composition anchor of [Shot 1]: the shot is framed like it.
{"<Audio 1> is Claudia's own voice alone (the vocal only, no music), <Subject 1> (S1), and the complete soundtrack of this video. Her mouth follows <Audio 1> exactly." if vocal else f"<Audio 1> is the song window for this shot, a bright Jersey club pop track at {BOARD['bpm']:.0f} BPM whose lead vocal is <Subject 1> (S1). It is the video's complete soundtrack."}

summary:
[reference generation + audio reuse] One continuous {s['framing']} shot of <Subject 1> in <Subject 2>, {'speaking' if s['section'] in SPOKEN else 'singing'} the words of <Audio 1> with precise lip sync. <Picture 1> fixes her identity, <Picture 2> fixes the framing, her outfit and the place, and <Audio 1> is copied as the complete soundtrack.

retention_analysis:
<Subject 1> (appears in [Shot 1]): fully_preserved - her face structure, freckles, adult age, black blunt bob with heavy bangs, the single purple streak on her right side, the single star clip on her left side, the headset mic and her outfit are retained exactly.
<Subject 2> (appears in [Shot 1]): fully_preserved - the place and its light are retained as in <Picture 2>.
<Picture 2> ([Shot 1] composition): fully_preserved - framing, her position and scale in the frame are retained.
<Audio 1>: fully_copy - <Audio 1> is reused 1:1 as the target video's complete final audio track.

detailed_description:
The target video is a cinematic 35mm music-video shot: real skin texture with visible pores and light freckles, {'deep night light' if is_night else 'cool blue-black light'}, shallow depth of field, fine silver film grain, natural true-to-life exposure, her purple streak and clay-orange star clip the only color accents on her, no text or graphics anywhere.
[Shot 1] The shot opens exactly as {look_src}: {s['action']} Camera: {s['camera']} The whole shot is one continuous take with no cuts. {f"Through the shot <Subject 1> (S1) {delivery(s['section'])}: <d>[English] {lyric}</d> "} Only her own lead vocal moves her mouth: she never mouths backing vocals, chants, harmonies or ad-libs, and whenever <Audio 1> is silent her lips are closed. Between phrases she closes her lips; {CHOREO if CHOREO_ON else 'her shoulders and body stay steady with no bouncing; her head, eyes and hands move with deliberate, controlled intent, and she never turns away from the camera for long.'} The purple streak stays on her right side of the bangs, the star clip above her left ear, the headset mic on her left cheek, in every frame. {SAME}

overall_soundscape:
The soundtrack is <Audio 1> copied in full; no added ambience or sound effects.

non_diegetic_music:
{"N/A" if vocal else "<Audio 1> is copied in full as the score under her vocal."}
"""


def run(s, a):
    out = path("clips_dir")
    out.mkdir(parents=True, exist_ok=True)
    path("windows_dir").mkdir(parents=True, exist_ok=True)
    if a.vocal:  # her vocal alone, mono, cleaned and normalised; the song is laid back over in the edit
        win = path("windows_dir") / f"{s['id']}-vocal-{s['start']:.3f}-{s['dur']:.3f}.wav"
        # keep only her own lines: mute everything outside each lyric line's words (backing chants, ad-libs, bleed)
        # her whole voice; only the measured wide-stereo backing chants are muted. Never mute by the lyric sheet: a
        # wrong line window there cut real singing out of what the model heard (LOW LATENCY v1: lips shut mid-line).
        backing = [(a - s["start"], b - s["start"]) for a, b in ZONES if b > s["start"] and a < s["end"]]
        mute = "anull"  # any muting cost lip sync more than the chants it removed (HALF THE SIZE A/B, LOW LATENCY v1)
        src, af = path("vocals"), ["-af", f"highpass=f=90,{mute},loudnorm=I=-16:TP=-1.5", "-ac", "1"]
    else:
        win = path("windows_dir") / f"{s['id']}-{s['start']:.3f}-{s['dur']:.3f}.wav"
        src, af = ROOT / BOARD["song"], ["-ac", "2"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(s["start"]), "-t", str(s["dur"]), "-i", str(src), *af,
                    "-ar", "48000", str(win)], check=True)
    pf = out / f"{s['id']}{'.vocal' if a.vocal else ''}.h3.txt"
    pf.write_text(prompt_for(s, a.vocal))
    if a.dry:
        return s["id"], 0, ["dry"]
    dur = max(5, min(15, round(s["dur"])))
    if 4 <= s["dur"] < 5:  # audio within 1 s of the request sets the length, and under 5 s Pruna fails: ask for 6
        dur = 6
    cmd = [sys.executable, str(ROOT / "scripts/pruna.py"), "--prompt-file", str(pf),
           "--out", str(out / f"{s['id']}-{a.resolution}-{a.tag}.mp4"),
           "--image", str(path("sheet")), "--image", str(ROOT / s["plate"]),
           "--audio", str(win), "--keep-audio", "--duration", str(dur), "--resolution", a.resolution,
           "--upsampler", "off", "--aspect", "16:9", "--seed", str(a.seed), "--what", f"clip {s['id']} {a.tag}"]
    if a.first_frame:  # start exactly on the plate (forces Pruna's turbo upsampler)
        cmd += ["--first-frame", str(ROOT / s["plate"])]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return s["id"], p.returncode, (p.stdout + p.stderr).strip().splitlines()[-2:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--resolution", default="768p")
    ap.add_argument("--seed", type=int, default=1001)
    ap.add_argument("--tag", default="v1")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--first-frame", action="store_true", help="also pass each shot's plate as its first frame")
    ap.add_argument("--choreo", action="store_true", help="v11-A: body choreography, face steady")
    ap.add_argument("--vocal", action="store_true", help="lip-sync from the isolated vocal stem (audio/stems/vocals.wav)")
    a = ap.parse_args()
    global CHOREO_ON
    CHOREO_ON = a.choreo
    shots = BOARD["shots"]
    if a.only:
        keep = set(a.only.split(","))
        shots = [s for s in shots if s["id"] in keep]
    with ThreadPoolExecutor(8) as ex:
        for sid, rc, tail in ex.map(lambda s: run(s, a), shots):
            print(sid, "ok" if rc == 0 else "FAILED", *tail)


if __name__ == "__main__":
    main()
