# RUN FREE

A 57-second song about opening up this repo, made to test the whole method on something new: a new Suno song, sung
line by line by six new singers, with the lyrics set behind them.

The six singers are new characters in Claudia's style, made with the `character-variants` skill
([CHARACTERS.md](../../CHARACTERS.md)). They share her look (the bob, the streak, the star clip, the headset mic); the
faces are their own. They are not Claudia, who is anabology's character and has one face. The video's credit reads
"Styled after Claudia by anabology · made with Pruna".

## Run it

From the repo root, after the setup in the main README:

```
python examples/run-free/render.py   # six p-video-2-pro-avatar takes, one per line, about $2.40
python examples/run-free/edit.py     # cut, mattes, lyrics, credit: about $0.55, writes examples/run-free/edit/RUN-FREE.mp4
```

## What's here

| | |
|---|---|
| `song.md` | the Suno style prompt, exclusions and lyrics (Suno v6, take 8b17b58f, 57.6 s) |
| `audio/song.m4a`, `audio/vocals.m4a` | the song and her isolated vocal (Demucs, `scripts/vocals.py`) |
| `audio/suno_aligned.json` | Suno's own word alignment |
| `audio/word_clock.json` | one start per sung word: forced alignment where it's confident and agrees with Suno, Suno elsewhere |
| `lockups.json` | how each line is set: theme phrases big (FORK / CLONE / RUN / OWN, FIFTY CENTS a DREAM, RUN FREE) |
| `plates/` | the six singers on stage, one still each |
| `prompts/` | the exact avatar prompt, plate, seed and audio window for each shot |
| `render.py`, `edit.py` | the whole pipeline, about 100 lines |

## How it was made, and what we learned

- **Picking a take without ears.** Claude can't hear, so it measured both Suno takes as they played (energy per band,
  every 40 ms) and read the chosen one's isolated vocal as a word-marked spectrogram. That showed the shouted chant
  was really there (four bursts with silence between them) and that the ending was a held note, not the section tag
  sung aloud, which Suno's alignment had suggested.
- **Cuts in the gaps.** Each shot runs from a gap between words to the next gap, read off that spectrogram.
- **Whole vocal windows.** Every shot gets its stem window untouched, plus a 0.5 s lead-in the edit trims. Our first
  render put the lead-in inside the window and lost the last half-second of every line: put `-t` on the input.
- **Joy, not attitude.** The prompts ask for warm, bright, open eyes and a joyful delivery, and say no pout, no smirk,
  never sultry. Without that the avatar model drifts toward a glossy, sultry default.
- **Check your plates.** One of our folders held earlier edits that had kept the original face. Look at the six plates
  side by side before paying for renders.
