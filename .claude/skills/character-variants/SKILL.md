---
name: character-variants
description: Make believable variants of an open character (e.g. Claudia by anabology): new fictional real-looking people who keep the character's constants (hair, streak, clip, mic). Text-only portrait, then a 10-panel identity sheet, then optional stage makeup and a test in a film still. Use when someone wants a new face, a cast of variants or a character sheet. Fictional people only.
---

# Character variants

Read CHARACTERS.md first. It has the method, the prompts and the biases to watch for.

## Rules
- **Fictional people only.** Never use a real person's photo as a face reference, and never aim for a likeness of a
  real person. If someone asks for that, decline and offer a fictional character instead.
- **Keep the character's constants** in every prompt, spelled out: one streak and which side it's on, one clip and
  which side, the mic, the haircut. That's what keeps the credit to the character's creator honest.
- **Age as a number,** never "young". She acts; she never shrinks. Nothing sexualised.

## Steps (show the human at each step)
1. **Agree the cast.** Write one concrete description per variant: age, face shape, skin, nose, eyes, two named
   imperfections. Name each person's ethnicity explicitly. Leaving it out does not make a variant neutral; in our
   tests it made seven out of seven white. Describe body and face features, not labels like "plus-size" or
   "androgynous".
2. **Portraits from text only** (`PORTRAIT` in `scripts/character_variants.py`), no face reference. Show them to the
   human; regenerate any that drifted toward a fashion model.
3. **One sheet per chosen portrait,** with the portrait as the ONLY face reference.
4. **Optional stage makeup** as an edit of the sheet, never in the first portrait.
5. **Swap each variant into one real film still** and compare: skin tone against the sheet, eye colour, age, the
   constants. Report what drifted, plainly.

Use `scripts/sunburst.py` (it logs spend to `spend.csv`): about $0.25–0.50 per image at xhigh. Stay inside the
human's budget.
