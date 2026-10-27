#!/usr/bin/env python3
"""RUN FREE edit: six takes cut frame-exact on the song's frames, her matte per shot, lyric lockups behind her, credit.

usage: python examples/run-free/edit.py      (after render.py; about $0.55 of mattes)
Writes examples/run-free/edit/RUN-FREE.mp4, then check it: see the README, "Verify". Mattes are cached in edit/mattes/<shot>/ (BiRefNet, ~$0.0004 a frame).
"""
import pathlib, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))
from render import SHOTS, PREROLL
import quickstart  # credit()

FPS = 24
E = HERE / "edit"
E.mkdir(exist_ok=True)


def sh(*cmd, **kw):
    subprocess.run([str(c) for c in cmd], check=True, **kw)


parts, alphas = [], []
def lead_is_silent(take, lead=PREROLL):
    """The take keeps the window's audio, so its first `lead` seconds must be silent. If not, the lead-in went missing
    and trimming it would put her lips early (RUN FREE v1)."""
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(take), "-t", str(lead - 0.1), "-ac", "1", "-ar", "16000",
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.int16).astype(float)
    return 20 * np.log10(np.sqrt((x ** 2).mean()) / 32768 + 1e-9) < -50


for sid, t0, t1, plate, _ in SHOTS:
    assert lead_is_silent(HERE / "clips" / f"{sid}.mp4"), f"{sid}: no silent lead-in in the take; don't trim blind"
    n = round(t1 * FPS) - round(t0 * FPS)  # frame-exact on the song's own frames: nothing drifts
    part = E / f"{sid}.mp4"
    sh("ffmpeg", "-v", "error", "-y", "-ss", PREROLL, "-i", HERE / "clips" / f"{sid}.mp4", "-frames:v", n, "-an",
       "-vf", "fps=24,scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-crf", "15", "-pix_fmt", "yuv420p", part)
    frames, mattes = E / "frames" / sid, E / "mattes" / sid
    if not (E / f"{sid}.alpha.mp4").exists():
        frames.mkdir(parents=True, exist_ok=True); mattes.mkdir(parents=True, exist_ok=True)
        sh("ffmpeg", "-v", "error", "-y", "-i", part, "-q:v", "2", frames / "f%04d.jpg")
        sh(sys.executable, REPO / "scripts/birefnet_frames.py", frames, mattes, stdout=subprocess.DEVNULL)
        sh(sys.executable, REPO / "scripts/matte_build.py", mattes, E / f"{sid}.alpha.mp4", "--start", "0",
           stdout=subprocess.DEVNULL)
    parts.append(part); alphas.append(E / f"{sid}.alpha.mp4")

for name, files in (("cut", parts), ("alpha", alphas)):
    lst = E / f"{name}.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in files))
    sh("ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", E / f"{name}.mp4")

song = HERE / "audio/song.m4a"
sh(sys.executable, REPO / "edit/lockups.py", E / "cut.mp4", E / "alpha.mp4", E / "lyrics.mp4",
   "--clock", HERE / "audio/word_clock.json", "--spec", HERE / "lockups.json", "--soundtrack", song,
   "--beatmap", "none")
# new singers in Claudia's style, not Claudia: the credit says so
quickstart.credit(E / "lyrics.mp4", E / "RUN-FREE.mp4", text="Styled after Claudia by anabology  ·  made with Pruna")
print(E / "RUN-FREE.mp4")
