#!/usr/bin/env python3
"""RUN FREE: six Claudias, one per line, each shot one p-video-2-pro-avatar take from her isolated vocal.

usage: render.py            # renders every shot missing from clips/, in parallel
Cuts sit in the gaps between words (read off the word-marked spectrogram). Each shot gets the whole stem window,
never muted, plus a 0.5 s lead-in that the edit trims.
"""
import pathlib, subprocess, sys
from concurrent.futures import ThreadPoolExecutor


HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
PLATES = HERE / "plates"
PREROLL = 0.5
sys.path.insert(0, str(REPO / "scripts"))
from windows import make_window  # noqa: E402

BASE = ("A cinematic 35mm music video shot on a concert stage. Her lips, jaw and tongue match every syllable exactly. "
        "Warm, bright, wide-open eyes; never sultry: no half-closed eyes, no pout, no smirk, never snarling. "
        "No bouncing: her shoulders and body stay steady; her energy comes from her face, eyes and hands. "
        "Camera: eye level, a gentle drift toward her. When the voice is silent her lips are closed. Her face, any glasses, hair, "
        "purple streak, star clip, headset mic and outfit stay exactly as in the image; she stays the same woman.")
CHANT = "She shouts a chant, one punchy word at a time, grinning with joy between the shouts. "
VERSE = "She half-speaks the lines like a confident, amused singer letting the crowd in on a secret, a joyful smile between lines. "
CHORUS = "She sings a huge joyful, euphoric belt, mouth wide open on the vowels, and holds the last note wide open. "

SHOTS = [  # id, start, end (song seconds), plate, mood
    ("R1", 0.00, 11.05, "N1", CHANT),
    ("R2", 11.05, 18.95, "N2", VERSE),
    ("R3", 18.95, 27.05, "C02b", VERSE),
    ("R4", 27.05, 34.20, "N3", VERSE),
    ("R5", 34.20, 42.80, "C09b", VERSE),
    ("R6", 42.80, 57.60, "C09c", CHORUS),
]


def sh(*cmd):
    subprocess.run([str(c) for c in cmd], check=True)


def render(shot, seed):
    sid, t0, t1, plate, mood = shot
    out = HERE / "clips" / f"{sid}.mp4"
    if out.exists():
        return f"{sid} exists"
    win = HERE / "audio/windows" / f"{sid}.wav"
    make_window(HERE / "audio/vocals.m4a", t0, t1, win, lead=PREROLL)  # lead-in prepended in code and checked
    out.parent.mkdir(exist_ok=True)
    sh(sys.executable, REPO / "scripts/avatar.py", "--image", PLATES / f"{plate}.jpg", "--audio", win,
       "--prompt", mood + BASE, "--out", out, "--seed", seed, "--what", f"RUN FREE {sid} ({plate})")
    (HERE / "clips" / f"{sid}.prompt.txt").write_text(mood + BASE + f"\n\nplate: {plate}  seed: {seed}  window: {t0}-{t1}\n")
    return f"{sid} done"


if __name__ == "__main__":
    with ThreadPoolExecutor(6) as ex:
        for r in ex.map(lambda p: render(*p), [(s, 11 + i) for i, s in enumerate(SHOTS)]):
            print(r, flush=True)
