# Lessons

What worked and what failed while making two Claudia films: HALF THE SIZE first, then LOW LATENCY.

## Direction
- **She acts; she never shrinks.** Our first film's lyric ("cut me down to half the size") read as a woman being told
  to shrink. In LOW LATENCY she is the engineer doing the work. Couture that covers her, no pout, no "eyes closed in
  ecstasy". Camp and spectacle are fine; sexualised is not.
- **Less is more, if the less is well made.** Don't change a working shot for its own sake. Compare old and new
  takes on frames, and only swap when the new one is clearly better.
- **Movement:** still or light by default. A few different moves, each one motivated by the shot's world, and only
  when her face is large. Never one signature move repeated through the film.
- **Graphics:** no visualised "ML effects", no screens inside screens, no HUD. Lyrics are worth showing only if they
  look great.

## Video models
- **Lip-sync from her isolated vocal**, mono and normalised, never the full mix. The full mix gives mushy mouths.
- **Never mute the vocal window.** Muting stretches you guessed were instrumental cut 17% of her real singing, and her
  lips shut while the song kept going.
- **Sung close-ups go to `p-video-2-pro-avatar`** (plate as portrait, prompt upsampling on). It beat the reference
  model on lip sync. Keep the reference model for action worlds.
- **Faces big.** Whenever her face is visible it fills at least a quarter of the frame height. Small faces glitch,
  especially the eyes.
- **Silent tails.** Beat bleed in the stem at -30 to -40 dB keeps her lips moving after the last word. Gate the window
  to true silence and ask for a closed-mouth hold.
- **Ask for a joyful, euphoric tone.** "Fierce" or "commanding" turned into a snarl.
- **Never prompt "the lights go out".** The avatar model took it literally and blacked out her face.
- **Audio windows of 4–5 s crashed the reference model.** Request at least 6 s.
- **Upscaling to 4K sharpened hair and eyes but turned freckles into grime.** 768p is our master.

## Timing (when the producer can't hear)
- **Suno's word alignment runs about 110 ms late**, and is sometimes a whole second off on held notes.
- **A confident forced-alignment word can belong to the neighbouring line.** Trust it only within 0.25 s of Suno.
- **Read the whole song** as word-marked spectrograms and check that the word clock only ever moves forward.
- **Show a word 1 frame before its attack.** It reads as exactly on time.
- **Cut on the song's own frames.** Rounding each cut drifted the picture half a second off by the end.
- **Where nobody can read the words**, like vocal chops, show no lyrics rather than guesses.

## Lyrics drawn in code
- **One system for the whole song.** Each line is a lockup: capital rows justified to one width, small italic rows
  for the filler words, built word by word behind her.
- **Highlight theme phrases** ("CUT THE WEIGHTS"), never a lone ambiguous word ("SHINE").
- **"Tuck an edge, never lose a glyph."** Over her matte for the line's whole time on screen, no letter is more than
  15% hidden.
- **Mattes:** BiRefNet per frame, steadied with a 3-frame median inside each shot, soft alpha. A video-matting model
  lost her purple jacket against the purple stage.
