---
name: verify-sync
description: Verify, and fix, the sync of a lip-synced music video made with this repo before anyone sees it - lead-ins that went missing, lips early or late per shot, lyrics that land before or after the word. Use after every render or edit of a sung shot or a film, before sending a clip to the human, and whenever someone says the lip sync or the subtitle/lyric timing is off.
---

# Verify sync

You can't hear, and neither can most of the people who will run this repo. Don't trust a sync you haven't
measured, and don't trust a measurement you haven't validated. Everything here runs on `scripts/verify_sync.py` and
`scripts/windows.py`; LESSONS.md, "Sync, verified" has the story behind each rule.

## 1. Audio windows (before paying for renders)
- Build every window with `scripts/windows.py` (`make_window(stem, t0, t1, out, lead=0.5)`). It cuts and normalises
  in ffmpeg, prepends the lead-in in code and asserts it: first 0.5 s digitally silent, exact length.
- Never add a lead-in with `adelay` in the same ffmpeg command that seeks (`-ss`): on ffmpeg 9 it silently skipped
  the silence for some windows and not others.

## 2. Takes (before trimming)
- The take keeps the window's audio, so its first 0.4 s must be silent. If not, stop: the lead-in went missing and
  trimming 0.5 s would put her lips half a second early. (`lead_is_silent` in `examples/run-free/edit.py`.)
- Trim exactly the lead-in, cut frame-exact on the song's frames.

## 3. Lyrics (the word clock)
```
python scripts/verify_sync.py words CLOCK.json --vocal VOCAL_STEM            # report
python scripts/verify_sync.py words CLOCK.json --vocal VOCAL_STEM --fix OUT  # snap words to their own attack
```
- Pass: no word more than 80 ms from its attack. Suno's alignment and speech recognition both run late on singing
  (RUN FREE: 27 of 69 words 100-150 ms late). `--fix` snaps each word to its attack, in order, each attack once, only
  within [-160, +80] ms. Check the biggest moves on a spectrogram before you trust them.
- Words with "no clear attack" (held notes, slurs) keep their time: look at them.

## 4. Lips (after the cut)
```
python scripts/verify_sync.py lips VIDEO --clock CLOCK.json --cuts 0,11.05,...,END --strips OUT_DIR
```
- It scores, per shot, how closed the mouth is at every word that starts with b/p/m/f/v, over every possible shift.
  PASS: within 150 ms (lips naturally close 40-120 ms before the sound). FAIL: re-render that shot.
- UNSURE (fewer than 3 lip words, or a weak margin): open the strip in OUT_DIR. Each row is one lip word; the red
  frame is where the lips should be closed. Closed at or one frame before the red frame = in sync.
- Validated on RUN FREE: the cut with the lead-in bug read -583 ms on its broken shots; the fixed cut read -125..0.
- Don't use mouth-opening vs loudness correlation (it read a correct take as 250 ms early: singing closes the mouth on
  loud consonants) or nearest-closure per word (there's always one within a few frames).

## 5. Report
Tell the human what you measured, per shot, with the strips you looked at. "Verified" means: windows checked, takes'
lead-ins silent, 0 words off by more than 80 ms, every shot PASS or UNSURE-and-looked-at. If you couldn't check
something, say so.
