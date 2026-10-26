# Making believable character variants

How we made new, believable versions of an open character: same Claudia constants, different real-looking people.
It took three rounds. The generator is `scripts/character_variants.py`, and the example images are in
`characters/`.

**Fictional people only.** Everything here starts from text. Never use a real person's photo as a face reference,
and never try to make someone look like a real person.

## The method
1. **Portrait from text only, with no face references.** A head-and-shoulders photo of one specific woman: her age as
   a number, her face shape, skin, nose, eyes, and two concrete imperfections (a gap between her front teeth, a
   dimple, a beauty mark, soft under-eye shadows).
2. **10-panel sheet with that portrait as the only face reference.** Two rows of five: front, three-quarter, both
   profiles, the back of the head, plus five expressions. Describe the grid in words. When we gave two face
   references at once, six "different" variants came out as one face.
3. **Character constants, written out every time:** "exactly ONE purple streak through the bangs on her right side
   (the viewer's left)", "exactly ONE star clip above her left ear", plus the mic and the bob. These make every
   variant recognisably Claudia.
4. **Makeup as a separate edit.** Start from the bare-faced sheet, then add stage makeup in an edit that keeps
   everything else. "The same real woman, made up for the show." Glam on top of a real face reads as a singer
   dressed for a gig; glam baked into the first portrait reads as a model.
5. **Test the variant in a real film still** before committing to it (`characters/round3-in-the-film.jpg`).

Write realism as physical detail: "Unretouched studio photograph, 85mm portrait lens, soft window light, natural skin
with visible pores and texture, no beauty retouching. She looks like a real person you could meet, a musician, not a
fashion model." Never use the word "realistic".

## Fighting the defaults (our biases and the model's)

Image models carry a default person, and so did we. Here's what we saw, honestly.

**Unspecified means white.** In our first round of 10 variants (`characters/round1-unspecified-defaults.jpg`), we
named an ethnicity for only three of them. All seven others came out as white women, most of them freckled and
fair. That "default" is a choice the model makes for you. If you want a range of people, name each person
specifically, every time. In our third round we did: a white woman, a Mediterranean woman, a Latina woman, a
mixed-race (Black and white) woman, a Filipina woman.

**Some words barely move the model.** "Plus-size" came out only slightly fuller. "Androgynous" came out as a
conventionally feminine face with bangs. Describe the face itself (a fuller face, soft round cheeks, a broad nose,
flat calm brows) instead of a label.

**Eyes go light.** Claudia's canon says "dark calm eyes", and our own final Claudia still has light grey-green eyes.
In the variant rounds we had to write "Her irises are dark brown, almost black" to get dark eyes at all.

**"Woman" drifts toward a young fashion model:** symmetrical, retouched, pouty, glossy. Ages given as numbers
(29–42 in our rounds), named imperfections and "not a fashion model" are what pull it back to a real person.

**Our own bias showed up in the film itself.** Our first film's lyric ("cut me down to half the size", "squeeze
me"), the cropped jacket and chest-centred framings read as a woman being told to shrink. Nobody prompted
"sexualised"; it crept in through a dozen small defaults. The fix was a direction, not a word: she is the one doing
the work. Couture that covers her, the collar closed to the chin, framing on her face and hands, no pout, no "eyes
closed in ecstasy".

**And a check, not a rule:** after you swap a variant into a stage still, compare her skin tone against her sheet.
Coloured stage light and the edit can drift it, so check by eye.

We don't claim to have solved any of this. Name what you want, look at what you get, and say what you saw.

## Prompts that worked
- **Portrait:** `PORTRAIT` in `scripts/character_variants.py`, with the six descriptions in `V`.
- **Sheet:** `SHEET`. Image 1 is the portrait; the grid is described in words.
- **Stage makeup:** `GLAM`, an edit of the sheet: winged liner with a thin purple line, bold brows, a berry lip.
- **Into the film:** `CTX`, an edit of a real plate: "Replace the woman completely with the woman in Image 2… Do not
  keep anything of Image 1's face or makeup."
- **Fixing one panel:** "Change ONLY the second panel of the bottom row… keep every other panel pixel for pixel."
