---
name: claudia-music-video
description: Make a lip-synced AI music video with an open character (Claudia by anabology, or your own) using Suno for the song, GPT Image for stills and Pruna's p-video models for video, with the edit, word timing and lyric typography done in code. Use when someone wants to make a music video, a music-video shot, or lyrics on a video with this repo.
---

# Make a lip-synced AI music video

The method that made LOW LATENCY: 20 lip-synced shots for $6.69 of video generation. Everything here was learned the
hard way; LESSONS.md has the full list. Work autonomously between checkpoints, and stop at each checkpoint to show
the human what you made.

## Start here
If they just want to see it work, run `python quickstart.py` (the demo, about $0.60) or
`python quickstart.py --audio <their clip>`. It renders one lip-synced shot with the lyric lockups. The full film
method follows.

## Ground rules
- **Keys** live in `.env` (`REPLICATE_API_TOKEN`, `PRUNA_API_KEY`). Load them in scripts; never print them.
- **Budget.** Agree a budget with the human first. Every script that calls an API appends to `spend.csv` (date,
  model, what, est_cost). Check in when the total passes each threshold you agreed.
- **You can't hear.** Say so. Verify anything about sound with measurements and pictures (spectrograms, waveform
  plots, mouth-crop strips), never by assumption.
- **The character.** Claudia's canon is at claudia.gallery; credit "Claudia is an open character by anabology
  (claudia.gallery)". Prompt her age as a number ("28-year-old"), never "young". She acts; she never shrinks.

## 1. Song (checkpoint: the human picks the take)
- Write the style and lyrics like `v2/song.md`. Choruses: one syllable per note, a chantable hook. Pass an exclude
  list of styles.
- The human generates it in Suno (their account), then gives you the WAV and Suno's word alignment.
- Split her vocal: Demucs on Replicate (`cjwbw/demucs`, stem=vocals). Build the beat map (`scripts/beatmap.py`).

## 2. Character sheet (checkpoint: the human approves it)
- Write a portrait from text only first, then a 10-panel identity sheet using that portrait as the only face
  reference (`scripts/sunburst.py`; see `v2/identity-sheet.prompt.txt`).
- Name two concrete imperfections and say "unretouched, no beauty retouching, 85mm, window light". Never write
  "realistic".
- That sheet becomes Image 1 for every later shot.

## 3. Storyboard (checkpoint: the human reads the board)
- Write a board generator like `v2/make_board.py`. Each shot gets its lyric, a world that illustrates that line, a
  plate prompt, a camera move and a model (avatar or reference).
- **Cuts never fall inside a word**, held notes included. A long held note gets one take.
- **Faces big:** when her face is visible it fills at least a quarter of the frame height. Wide shots only with her
  face turned away.
- **Movement:** still or light by default. A few different moves, each motivated by the world, never one signature
  move repeated through the film.

## 4. Plates (checkpoint: the human picks a plate per shot)
- `scripts/plates.py`, GPT Image 2.5 Sunburst, 16:9. Image 1 = identity sheet, Image 2 = outfit. Give every image a
  role and say what "same" means: face structure, hair, which side the streak is on, which side the clip is on,
  freckles, age.
- End plate prompts with "No text, no letters, no logos". See `v2/plates/*.prompt.txt`.

## 5. Video (checkpoint: a rough cut with no graphics)
- **Sung close-ups → `p-video-2-pro-avatar`** (`scripts/avatar_shots.py`): plate as portrait, the vocal window as
  audio, prompt upsampling ON, 0.5 s audio lead-in trimmed in the edit. Ask for a joyful, euphoric tone ("fierce"
  becomes a snarl). See `v2/prompts/L02.prompt.txt`.
- **Action worlds → `p-video-2-pro-reference`** (`scripts/clips.py`): the H3 six-section prompt (subject_definitions,
  summary, retention_analysis, detailed_description, overall_soundscape, non_diegetic_music), sung words in
  `<d>[English] ...</d>`, keep_audio on. See `v2/prompts/L06.prompt.txt`.
- **Always feed her isolated vocal**, mono and normalised. Never the full mix (mushy mouths), and never a window
  muted by guessed lyric times (her lips shut while she sings).
- **Silent tails:** gate the window to true silence after the last word, or the lips keep moving on beat bleed.
- **Iterate at 768p.** Pass a seed every time. Audio windows under 6 s can crash the reference model. Retry
  transient failures once with a new seed.
- **Assemble frame-exact** on the song's frames (`edit/assemble.py`). Pin the chosen take for each shot in
  `projects/<name>.json`.

## 6. Word clock (checkpoint: the proof sheet)
- `scripts/force_align.py` (wav2vec2 on the vocal stem), then `scripts/word_clock.py`. That merges Suno's alignment
  (about 110 ms late), forced alignment (only within 0.25 s of Suno) and the vocal's attacks.
- Render word-marked spectrograms of the WHOLE song and read every row. Check the clock only ever moves forward. Put
  measured fixes in `word_overrides.json`, each with a reason.
- Show each word 1 frame before its attack. Where vocals are chopped and unreadable, show nothing.

## 7. Lyrics and graphics (checkpoint: a frame sheet, then the film)
- Mattes: `scripts/birefnet_frames.py`, then `scripts/matte_build.py` (3-frame median inside each shot, soft
  alpha). Judge mattes on a magenta ground.
- Lockups: `edit/lockups.py` with a spec like `v2/lockups.json`. Each line is a block behind her, CAPS rows justified
  to one width plus small italic rows, built word by word. Highlight theme phrases, never lone ambiguous words.
  Placement rule: no letter more than 15% hidden by her, and never over her face.
- Check with `--sheet` (one frame per lyric block) before sending a full render.
- End card: "Claudia by anabology · made with Pruna" (`edit/lyrics_cb.py --card-only`).

## Before you send anything
Look at frames yourself first: the hit frames, clone moments, the end card and the frame count. Give the human
options plus your pick, with exact costs.
