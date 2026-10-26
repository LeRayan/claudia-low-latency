#!/usr/bin/env python3
"""LOW LATENCY storyboard (V2): the single source for v2/board.json, v2/board.md and every plate prompt.

V2 rule (from the HALF THE SIZE review): she is the one doing it. She distills, prunes, fuses and compiles; the world
gets faster because of her, she never gets smaller. Couture and spectacle, never sexualised. Faces always MCU or tighter.
"""
import json, pathlib

HERE = pathlib.Path(__file__).resolve().parent
BEATS = json.load(open(HERE / "beatmap.json"))
BAR = BEATS["bars"]  # BAR[n-1] = start of bar n
SONG_END = 151.2

ID_TEXT = ("a 28-year-old Caucasian American woman with a grown-up angular face, defined cheekbones and a strong jawline, "
           "pale matte skin and light freckles, natural brows, bare natural lips, one sharp graphic Pruna-purple eyeliner "
           "wing on each eye, a glossy black blunt jaw-length bob with heavy straight bangs and one glossy Pruna-purple "
           "(#9B1DBE) streak through the bangs, a small flat clay-orange eight-pointed star hair clip, a thin headset "
           "microphone at her cheek")
LOOK = ("a sculptural jacket of glossy black and deep Pruna-purple (#9B1DBE) structured panels like elegant armour, with "
        "exaggerated sharp pointed shoulders and a tall stand-up collar closed up to her chin, long fitted sleeves ending "
        "in black gloves, a thin silver line along every seam")
REF_ROLE = ("Image 1 is the identity reference: she is the same person as every panel of Image 1 (face structure, "
            "freckles, age, natural lips, the purple eyeliner wing, the black blunt bob with heavy bangs, exactly ONE "
            "Pruna-purple streak on her right side, exactly ONE clay-orange star clip above her left ear, the thin "
            "headset mic). Use Image 1 only for who she is; never copy its grid, grey backdrop or turtleneck. Image 2 is "
            "her outfit only: copy the armour jacket exactly; never copy its studio, its full-length framing or its pose.")
CLOSE = ("Her head and shoulders fill the frame: her face is large, at least a quarter of the frame height, sharp and in "
         "focus, eyes open and clearly visible.")
STYLE = ("Real photograph, cinematic 35mm film still from a theatrical pop music video: visible skin pores and natural "
         "skin texture, dramatic stage light, a deep black and Pruna-purple palette with silver highlights, haze, fine "
         "silver grain. She is commanding and in control, never sexualised: no cleavage, no pout, no bare skin below "
         "the collar. No text, no letters, no logos, no screens with writing.")

STAGE = ("a cathedral-sized data hall turned into a concert stage: towering racks of servers like organ pipes glowing "
         "purple, haze, beams of purple and white light, a raised black podium with a sleek glowing console")

TREATMENT = (
    "Claudia is the engineer and the diva of AI efficiency. On a cathedral stage of servers she conducts the show; "
    "each verse line is a theatrical world for one technique: a candlelit distillation lab, a fibre-optic bonsai she "
    "prunes with silver shears, a forge where streams of purple light fuse into one ingot, an amber memory vault, a "
    "staircase of glowing quantized cubes, a giant split-flap board she finishes before it flips. Everything gets "
    "faster because of her. She ends at the console: less compute, more me.")
DEVICE = (
    "THE LATENCY READOUT, drawn in code top-left: 'LATENCY 1,240 ms' at the start. Each technique, when she names "
    "it, lights up as a purple chip in a row under it (DISTILL, PRUNE, FUSE, CACHE, QUANTIZE, SPECULATE, COMPILE) "
    "and the latency rolls down on the beat. The bridge fires all seven chips one per word. On the last line it "
    "locks: 'LATENCY 9 ms · LESS COMPUTE ✓ MORE ME'.")

# (id, first_bar, end_bar_exclusive, section, lyric, set, framing, action, camera, plate body)
SHOTS = [
    ("L01", 0, 4, "intro", "Prune it! Distill it! Fuse it! Ship it!", "stage", "MCU",
     "On the podium she punches each word of the chant into the air with a gloved fist, one word per beat, eyes on the "
     "lens; the purple beams fire on each word.",
     "Locked medium close-up, a tiny push on each word.",
     f"Medium close-up, eye level, she stands on the right third at the podium of {STAGE}, one gloved fist raised "
     f"beside her face, shouting a word, eyes fierce on the lens. {CLOSE}"),
    # Rayan on v8: the low angle read unnatural, her head too static, the eyes glitchy. Eye level, a natural performer.
    ("L02", 4, 8, "chorus 1", "Low latency, baby / Zero wasted time", "stage", "MCU",
     "She belts the hook with joy, moving like a real singer on stage: her head turns and tilts naturally with the "
     "phrases, she looks out over the crowd and back into the lens, relaxed natural blinks, one gloved hand rising "
     "with the long note.",
     "Eye-level, a gentle handheld drift toward her.",
     f"Medium close-up at eye level, the camera straight at her face, at the podium of {STAGE}, she is on the left "
     f"third, head turned slightly toward the crowd, singing an open note with joy, eyes open and bright, one gloved "
     f"hand raised beside her. {CLOSE} Her eyes are sharp and natural, clearly lit."),
    ("L03", 8, 11, "chorus 1", "Cut the weights, keep the shine / Every token mine", "stage", "CU",
     "Close-up: she sings straight into the lens, amused and certain, holding the long note of 'mine' with power.",
     "Locked.",
     f"Close-up of her face and shoulders on the right third, the stage behind her a soft blur of purple light and "
     f"haze, singing, eyes on the lens, amused and certain. {CLOSE}"),
    ("L04", 11, 16, "chorus 1 tail", "Every token mine", "stage", "MCU",
     "She sings on at the console, working the glowing faders with deliberate, precise hands, shoulders still, "
     "eyes on the lens.",
     "Slow lateral track along the console.",
     f"Medium close-up, eye level, she works the glowing console at the podium of {STAGE} with both gloved hands, "
     f"mid-groove, lips closed, a sly half-smile at the lens, on the left third. {CLOSE}"),
    ("L05", 16, 19, "verse 1", "A giant teacher had a trillion things to say / I sat in the front row and I learned it in a day",
     "distillation lab", "MCU",
     "In a candlelit alchemist's lab of giant glass alembics, glowing purple liquid drips down a coil into one tiny vial "
     "she holds up between two fingers; she tells the lens the lines, deadpan.",
     "Slow dolly-in toward her and the vial; she turns her head to the dripping alembic, then back to the lens.",
     "Medium close-up, eye level. She stands on the right third in a candlelit alchemist's laboratory of enormous glass "
     "alembics and copper coils, glowing purple liquid dripping down into one tiny glass vial that she holds up beside "
     f"her face between two gloved fingers, deadpan, talking to the lens. {CLOSE} Warm candlelight and purple glow."),
    ("L06", 19, 23, "verse 1", "I pruned the lazy neurons that were only there for show / Now I'm lighter on my feet and I'm faster than you know",
     "fibre-optic bonsai", "MCU",
     "Beside a vast bonsai tree whose branches are glowing fibre-optic strands, she snips a branch with huge silver "
     "shears on 'pruned'; the cut strands go dark and fall; she looks back at the lens, amused.",
     "Slow orbit a quarter-turn around her as she cuts; she glances at the branch on the snip, then back to the lens.",
     "Medium close-up, eye level. She stands on the left third beside a vast bonsai tree whose branches are thousands of "
     "glowing purple and white fibre-optic strands, holding huge silver pruning shears open around one branch, looking "
     f"into the lens with an amused face. {CLOSE} Dark room, the tree is the only light."),
    ("L07", 23, 26, "pre-chorus", "Fuse it, fuse it / One kernel, one go", "the forge", "MCU",
     "At a forge, two streams of molten purple light pour together into one glowing ingot between her gloved hands; she "
     "sings rising, sparks in the air.",
     "Slow push-in as the two streams meet; she looks down at the ingot as it fuses, then up into the lens.",
     "Medium close-up, eye level. She stands at a dark forge, her gloved hands guiding two streams of molten glowing "
     "purple light that pour together into one shining ingot in front of her chest, sparks drifting, singing, eyes on "
     f"the lens, on the right third. {CLOSE}"),
    ("L08", 26, 30, "chorus 2", "Low latency, baby / Zero wasted time", "stage", "MCU low",
     "Back on the stage, bigger: purple beams sweep behind her; she belts with one arm thrown out to the side, "
     "commanding.",
     "Low-angle slow tilt up.",
     f"Medium close-up from a low angle at the podium of {STAGE}, beams of purple light sweeping behind her, she is on "
     f"the right third, one arm thrown out to the side, singing a powerful note with her eyes open. {CLOSE}"),
    ("L09", 30, 35, "chorus 2", "Cut the weights, keep the shine / Every token mine", "stage", "CU profile",
     "Three-quarter profile close-up, she sings toward the light, then turns her eyes to the lens on 'mine'.",
     "Locked.",
     f"Close-up in three-quarter profile, she faces the viewer's left with her LEFT side to the camera (the star clip "
     f"and headset mic in view), singing toward the beams of purple light, the stage of servers a blur behind her. "
     f"{CLOSE}"),
    ("L10", 35, 38, "post-chorus", "Prune, prune, distill, distill / Fuse it, ship it, faster still", "stage", "MCU",
     "She chants and hammers the console on each word with both fists, the server racks behind her flashing on the "
     "beat.",
     "Locked, a punch-in on each bar.",
     f"Medium close-up, eye level, she leans over the glowing console at the podium of {STAGE}, both gloved fists "
     f"striking it, shouting a word, eyes on the lens, centred. {CLOSE}"),
    ("L11", 38, 42, "post-chorus", "Prune, prune, distill, distill / Fuse it, ship it, faster still", "stage", "CU",
     "Close-up chant to the lens, grinning, fierce.",
     "Locked.",
     f"Close-up of her face and shoulders, centred, shouting a word of a chant with a fierce grin, eyes on the lens, "
     f"purple light and haze behind her. {CLOSE}"),
    ("L12", 42, 44, "verse 2", "I keep my memory warm so I never think twice", "memory vault", "MCU",
     "In a mirrored vault of warm amber drawers she pulls one open without looking, deadpan, talking to the lens.",
     "Slow lateral track along the drawers, keeping her face large; she glances at the drawer, then back to the lens.",
     "Medium close-up, eye level. She stands on the right third in a vault whose walls are thousands of small glowing "
     "warm-amber drawers, one gloved hand pulling a drawer open beside her without looking at it, deadpan, talking to "
     f"the lens. {CLOSE}"),
    ("L13", 44, 46, "verse 2", "Four bits a weight and I'm every bit as precise", "quantized stairs", "MCU",
     "On a staircase of glowing cubes she places one cube with perfect precision, then looks to the lens.",
     "Slow crane up beside the cube staircase, staying close on her face; she looks at the cube she places, then at the lens.",
     "Medium close-up, eye level. She stands on the left third on a staircase built of glowing purple and white cubes "
     "like big pixels, setting one small glowing cube into place with precise gloved fingers beside her face, eyes on "
     f"the lens, deadpan. {CLOSE}"),
    ("L14", 46, 49, "verse 2", "I guess your next ten words before you finish your line / And if I guess them wrong, I'm still ahead of time",
     "split-flap board", "MCU",
     "In front of a giant black split-flap board whose flaps are blank and spinning, she taps it with one finger and "
     "turns to the lens, amused, as if she already knows.",
     "Slow push-in; the flaps spin behind her; she turns from the board to the lens with a knowing look.",
     "Medium close-up, eye level. She stands on the right third in front of a giant wall of black split-flap display "
     "flaps, blurred mid-spin with no letters visible, one gloved finger touching the wall, turning to the lens with an "
     f"amused, knowing face, talking. {CLOSE}"),
    ("L15", 49, 52, "pre-chorus 2", "Fuse it, fuse it / One kernel, one go", "the forge", "CU",
     "Close at the forge: the fused ingot glows under her face as she sings rising.",
     "Locked.",
     "Close-up, eye level. Her face lit from below by a shining ingot of molten purple light held between her gloved "
     f"hands, sparks drifting, singing, eyes on the lens, centred. {CLOSE}"),
    ("L16", 52, 56, "bridge", "Quantize! Distill! Prune! Fuse! Cache! Compile!", "the console", "MCU",
     "The beat drops to kick and claps: at the console she shouts each word and slams one glowing key per word, six "
     "keys, six bursts of light.",
     "Hard, controlled push-in on each shouted word, settling between words; she slams each key with a precise strike.",
     f"Medium close-up, eye level, she stands at the glowing console at the podium of {STAGE}, one gloved hand slamming "
     f"a glowing key, shouting a word, eyes fierce on the lens, on the left third. {CLOSE}"),
    ("L17", 56, 60, "final chorus", "Low latency, baby / Zero wasted time", "stage", "MCU low",
     "Key change: the whole stage blazes purple; she belts, both arms spread like a conductor.",
     "Slow low-angle push-in.",
     f"Medium close-up from a low angle at the podium of {STAGE}, the whole stage blazing purple behind her, both arms "
     f"spread wide like a conductor, singing a powerful note, eyes open, centred. {CLOSE}"),
    ("L18", 60, 64, "final chorus", "Cut the weights, keep the shine / Every token mine", "stage", "CU",
     "Close-up, she sings triumphant, purple streamers drifting through the beams.",
     "Locked.",
     f"Close-up of her face and shoulders on the right third, purple paper streamers drifting through beams of light "
     f"behind her, singing triumphantly, eyes on the lens. {CLOSE}"),
    ("L19", 64, 68, "final chorus", "Low latency, baby / Zero wasted time", "stage", "MCU",
     "She belts at the console, one gloved hand pushing a glowing master fader all the way up.",
     "Slow lateral track.",
     f"Medium close-up, eye level, at the podium of {STAGE}, she pushes a glowing master fader up with one gloved hand, "
     f"singing a powerful note, eyes open, on the left third. {CLOSE}"),
    ("L20", 68, 72, "final chorus", "Cut the weights, keep the shine / Every token mine", "stage", "CU",
     "Close-up, the climax: she belts the long held final 'mine' with full power, mouth wide open, chin lifting, eyes "
     "on the lens, holding the note with full energy to the very end. No smiling while she sings.",
     "Locked.",
     f"Close-up of her face, centred, singing the last line with a proud smile beginning, eyes on the lens, the stage "
     f"a blur of purple light. {CLOSE}"),
    ("L21", 72, None, "outro", "Less compute. More me.", "the console", "CU",
     "The beat stops and the stage behind her is dark, but her face stays clearly lit by the purple glow of the console; she says the words deadpan into the "
     "lens, each word crisp and clearly articulated, then allows herself one small smile only after the last word.",
     "Locked.",
     "Close-up, eye level, her face lit only by the soft purple glow of a console below the frame, the dark stage "
     f"behind her, deadpan with the hint of a smile, eyes on the lens, centred. {CLOSE}"),
]


def t(bar):
    if bar is None:
        return SONG_END
    return 0.0 if bar == 0 else BAR[bar - 1]


# Cuts sit on bar lines, but never inside a word: where a cut would split a word (Suno's own word alignment), it
# moves to that word's start if that is within 0.6 s. Held notes over 1.5 s may be cut through (an open vowel).
WORDS = [c["timestamp"] for c in json.load(open(HERE / "audio/suno_aligned.words.json"))["chunks"]]


def safe_cut(t0):
    for s, e in WORDS:
        if s < t0 < e and e - s < 1.5:
            return round(s - 0.02, 3) if t0 - s <= 0.6 else round(e + 0.02, 3)
    return t0


board = {"title": "LOW LATENCY", "song": "v2/audio/LOW-LATENCY-PICK.wav", "bpm": BEATS["bpm"], "treatment": TREATMENT,
         "device": DEVICE, "look": LOOK, "id_text": ID_TEXT, "shots": []}
for (sid, a, b, sec, lyric, set_, framing, action, cam, body) in SHOTS:
    start = 0.0 if a == 0 else safe_cut(round(t(a), 3))
    end = SONG_END if b is None else safe_cut(round(t(b), 3))
    prompt = f"{body}\n\n{REF_ROLE}\n\nShe is {ID_TEXT}. She wears {LOOK}.\n\n{STYLE}"
    board["shots"].append({"id": sid, "bars": [a, b], "start": start, "end": end, "dur": round(end - start, 3),
                           "section": sec, "lyric": lyric, "set": set_, "framing": framing, "action": action,
                           "camera": cam, "identity": "full",
                           "refs": ["v2/sheets/claudia-identity-v2.png", "v2/look/LOOK-PICK.png"],
                           "plate": f"v2/plates/{sid}-PICK.png", "plate_prompt": prompt})
# v10 (Rayan: "it changes clip multiple times" at the end): cuts on word boundaries only, and the whole climax
# "Every token mine" with its 12.7 s held "mine" is ONE avatar take (the avatar model allows up to 3 min).
CUTS = {"L16": (None, 109.88), "L17": (109.88, 117.45), "L18": (117.45, 125.0), "L19": (125.0, 141.3)}
board["shots"] = [s for s in board["shots"] if s["id"] != "L20"]
for s in board["shots"]:
    if s["id"] in CUTS:
        a, b = CUTS[s["id"]]
        s["start"] = s["start"] if a is None else a
        s["end"] = b
        s["dur"] = round(s["end"] - s["start"], 3)
    if s["id"] == "L19":
        s["section"], s["lyric"] = "final chorus climax", "Every token mine"
        s["action"] = ("At the console she pushes the glowing master fader all the way up on 'Every token', then belts the "
                       "long held 'mine' with full power to the very end, both arms rising, the whole stage blazing purple "
                       "around her, radiant and triumphant.")
        s["camera"] = "One continuous take: a slow, steady push-in from medium close-up to close-up over the held note."
AVATAR_OK = {"L19"}  # longer than the reference model's 14.4 s cap; rendered with the avatar model
assert all(s["dur"] <= 14.375 or s["id"] in AVATAR_OK for s in board["shots"]), [(s["id"], s["dur"]) for s in board["shots"] if s["dur"] > 14.375]
(HERE / "board.json").write_text(json.dumps(board, indent=1))
md = [f"# LOW LATENCY: storyboard\n", f"{len(board['shots'])} shots, {board['bpm']} BPM, every cut on a bar line.\n",
      f"**Treatment.** {TREATMENT}\n", f"**Device.** {DEVICE}\n", f"**Look.** {LOOK}.\n",
      "| Shot | Bars | Time | Section | Lyric | Set · framing | Action |", "|---|---|---|---|---|---|---|"]
for s in board["shots"]:
    md.append(f"| {s['id']} | {s['bars'][0]}–{s['bars'][1] or 'end'} | {s['start']:.1f}–{s['end']:.1f} ({s['dur']:.1f} s) | "
              f"{s['section']} | {s['lyric']} | {s['set']} · {s['framing']} | {s['action']} |")
(HERE / "board.md").write_text("\n".join(md) + "\n")
print(len(board["shots"]), "shots")
