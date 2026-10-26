# Prompt playbook

The prompt patterns behind LOW LATENCY, with the reasons they look the way they do. The exact prompt of every take
in the final cut is in `v2/prompts/`, and every plate prompt is in `v2/plates/`.

## 1. Identity sheet (GPT Image 2.5 Sunburst)
Full prompt: `v2/identity-sheet.prompt.txt`.
- **Portrait first, sheet second.** Make one portrait from text only, then a 10-panel sheet (two rows of five, every
  head angle plus five expressions) with that portrait as the only face reference. With two face references, six
  "variants" came out identical.
- **Spell out the canon.** One streak, and which side it's on; one clip, and which side. "Never two."
- **Write realism as physical detail:** "real photograph, visible skin pores, fine 35mm silver grain". Never the
  word "realistic".
- **Age as a number:** "28-year-old adult woman". Never "young".
- **Mouth:** "relaxed and natural, never pouting. Lips are not enlarged."

## 2. Plates (one still per shot)
Example: `v2/plates/L06.prompt.txt`. The order matters:
1. **Framing and action:** "Medium close-up, eye level. She stands on the left third beside…, looking into the lens
   with an amused face."
2. **Face size, stated explicitly:** "her face is large, at least a quarter of the frame height, sharp and in focus,
   eyes open and clearly visible."
3. **The role of each image:** "Image 1 is the identity reference… Use Image 1 only for who she is; never copy its
   grid, grey backdrop or turtleneck. Image 2 is her outfit only."
4. **The canon descriptor, repeated in full in every prompt.**
5. **The ending:** "No text, no letters, no logos."

## 3. Sung close-ups (`p-video-2-pro-avatar`, prompt upsampling ON)
This is a real prompt from the final cut (`v2/prompts/L02.prompt.txt`):

> A cinematic 35mm music video shot. She belts the hook with joy, moving like a real singer on stage: her head turns
> and tilts naturally with the phrases, she looks out over the crowd and back into the lens, relaxed natural blinks,
> one gloved hand rising with the long note. Camera: Eye-level, a gentle handheld drift toward her. She sings with
> her lips, jaw and tongue matching every syllable exactly, eyes on the lens. Her mood is joyful and euphoric: she
> loves singing this song, warm smiling eyes, open-hearted, mouth wide open on the vowels, radiant. Never snarling,
> never sneering, never menacing, no bared-teeth grimace. No bouncing: her shoulders, body and jacket stay steady;
> her energy comes from her face, eyes and hands. Her face, hair, purple streak, star clip, headset mic and armour
> jacket stay exactly as in the image; she stays the same 28-year-old woman.

Why it reads like this:
- "Joyful and euphoric" plus the "never snarling…" list, because "fierce" came out as a snarl.
- "No bouncing", because body bounce made the jacket wobble.
- The audio is her vocal window with a 0.5 s lead-in, trimmed in the edit.

## 4. Action worlds (`p-video-2-pro-reference`, H3 format, upsampler off)
Example: `v2/prompts/L06.prompt.txt`. The six sections, in order:
- **subject_definitions:** `<Subject 1>` is her, from `<Picture 1>` (identity sheet) and `<Picture 2>` (the plate),
  with the full canon descriptor. `<Audio 1>` is "her own voice alone… the complete soundtrack. Her mouth follows
  `<Audio 1>` exactly."
- **summary:** one line: shot type, the reference roles, and audio reuse.
- **retention_analysis:** what stays `fully_preserved` (her face, hair, streak side, clip side, outfit; the place;
  the framing), and `<Audio 1>: fully_copy`.
- **detailed_description:** the look (35mm, pores, grain, exposure), then `[Shot 1]` with the action timed to a sung
  word ("she snips a branch… on 'pruned'"), the camera, "one continuous take with no cuts", and the lyric inside
  `<d>[English] ...</d>` spoken by `(S1)`.
- **The lip-sync guard lines that mattered:** "Only her own lead vocal moves her mouth: she never mouths backing
  vocals, chants, harmonies or ad-libs, and whenever `<Audio 1>` is silent her lips are closed."
- **overall_soundscape:** "`<Audio 1>` copied in full; no added ambience." **non_diegetic_music:** N/A.

## 5. Song (Suno)
Style and lyrics: `v2/song.md`.
- **Name the delivery for each section:** "[Verse] half spoken, deadpan, every word crisp" and "[Chorus] powerful
  belt, one syllable per note, never rushed". Crisp diction is what makes lip sync and word timing work later.
- **Keep an exclude list.** It's the cheapest quality control there is.
