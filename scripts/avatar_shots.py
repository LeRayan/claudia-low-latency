#!/usr/bin/env python3
"""Render board shots with p-video-2-pro-avatar (Rayan's A/B: it lip-syncs sung close-ups best), in parallel.

usage: CLIP_PROJECT=v2 avatar_shots.py --only L01,L02 --tag v5 [--seed 7007]
Each shot: its plate as the portrait, its whole vocal-stem window as the audio, prompt upsampling on.
"""
import argparse, json, pathlib, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "edit"))
from project import P, path  # noqa: E402

STILL = ("No bouncing: her shoulders, body and jacket stay steady; her energy comes from her face, eyes and hands.")
CHOREO = ("Choreography: sharp, precise vogue-style arm and hand choreography on the beat: crisp geometric arm lines, "
          "hands framing her face, wrists snapping into poses, a shoulder isolation on each downbeat, one arm sweeping "
          "overhead and back. Her head and face stay steady and centred, facing the lens, calm and still, so all the dance "
          "is in her arms, hands and shoulders. Sharp and controlled, never bouncy.")
JOY = ("Her mood is joyful and euphoric: she loves singing this song, warm smiling eyes, open-hearted, mouth wide open on "
       "the vowels, radiant. Never snarling, never sneering, never menacing, no bared-teeth grimace.")
COLD = r"\b(commanding|fierce|fiercely|deadpan|menacing)\b"  # board words the avatar model turned into a snarl
PREROLL = 0.5  # s of audio before the shot so the model hears the lead-in (anabology: 0.3-0.7 s); trimmed in the edit
KEEP = P.get("keep_line", "Her face, hair, purple streak, star clip, headset mic and armour jacket stay exactly as in "
                          "the image; she stays the same 28-year-old woman.")


def run(s, a):
    pre = min(PREROLL, s["start"])
    win = path("windows_dir") / f"{s['id']}-vocal-pre{pre:.2f}-{s['start']:.3f}-{s['dur']:.3f}.wav"
    if not win.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(s["start"] - pre), "-t", str(s["dur"] + pre), "-i", str(path("vocals")),
                        "-af", "highpass=f=90,loudnorm=I=-16:TP=-1.5", "-ac", "1", "-ar", "48000", str(win)], check=True)
    verb = "says the words" if s["section"] in ("verse 1", "verse 2", "outro") else "sings"
    action = re.sub(COLD, "joyful", s["action"]) if a.joy else s["action"]
    prompt = (f"A cinematic 35mm music video shot. {action} Camera: {s['camera']} She {verb} with her lips, jaw "
              f"and tongue matching every syllable exactly, eyes on the lens. {JOY + ' ' if a.joy else ''}{CHOREO + ' ' if a.choreo else STILL + ' '}{KEEP}")
    out = path("clips_dir") / f"{s['id']}-768p-{a.tag}.mp4"
    p = subprocess.run([sys.executable, str(ROOT / "scripts/avatar.py"), "--image", str(ROOT / s["plate"]),
                        "--audio", str(win), "--prompt", prompt, "--out", str(out), "--seed", str(a.seed),
                        "--what", f"avatar clip {s['id']} {a.tag}"], capture_output=True, text=True)
    if p.returncode == 0:  # the edit trims this lead-in so the shot still starts on its cut
        meta = json.loads(out.with_suffix(".json").read_text()) | {"preroll": pre}
        out.with_suffix(".json").write_text(json.dumps(meta, indent=1))
    return s["id"], p.returncode, (p.stdout + p.stderr).strip().splitlines()[-2:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--seed", type=int, default=7007)
    ap.add_argument("--choreo", action="store_true", help="v11-A: body choreography, face steady")
    ap.add_argument("--joy", action="store_true", help="joyful, euphoric tone (Rayan: the fierce tone read as a snarl)")
    a = ap.parse_args()
    keep = set(a.only.split(","))
    shots = [s for s in json.load(open(path("board")))["shots"] if s["id"] in keep]
    with ThreadPoolExecutor(8) as ex:
        for sid, rc, tail in ex.map(lambda s: run(s, a), shots):
            print(sid, "ok" if rc == 0 else "FAILED", *tail)


if __name__ == "__main__":
    main()
