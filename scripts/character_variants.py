"""Character variants for an open character: one portrait from TEXT ONLY, then a 10-panel sheet with that portrait as
the only face reference, a stage-makeup version of the sheet, and both swapped into a real film still.
Edit V (one concrete description per variant) and run from the repo root: python3 scripts/character_variants.py
Fictional people only: never pass a real person's photo as a face reference. See CHARACTERS.md.
"""
import json,os,subprocess,sys
os.makedirs("characters/out", exist_ok=True)
from concurrent.futures import ThreadPoolExecutor
V={
 "C02a":"a 33-year-old white woman with a round face and a soft jaw, a slightly upturned nose, small dark brown eyes, a small gap between her two front teeth, clear even skin.",
 "C02b":"a 30-year-old Mediterranean woman with olive skin, a round face, thick dark eyebrows, a strong straight nose, dark brown eyes, a small gap between her two front teeth.",
 "C02c":"a 36-year-old Latina woman with warm tan skin, a round face with soft laugh lines, a slightly wide nose, dark brown eyes, a small gap between her two front teeth.",
 "C09a":"a 32-year-old white woman with a fuller face, soft round cheeks, fair rosy skin, a short nose, a dimple in her right cheek, dark brown eyes.",
 "C09b":"a 29-year-old mixed-race woman (Black and white) with light brown skin, a fuller face, full lips, a broad nose, a dimple in her right cheek, dark brown eyes.",
 "C09c":"a 34-year-old Filipina woman with warm light-brown skin, a fuller face, strong straight brows, a small beauty mark above her upper lip, dark brown eyes.",
}
CONST=("a glossy black blunt jaw-length bob with heavy straight bangs to the brows; exactly ONE glossy purple (#9B1DBE) streak through the bangs on her right side (the viewer's left when she faces the camera); exactly ONE small flat clay-orange eight-pointed star hair clip above her left ear; a thin beige headset microphone, its earpiece over her left ear and its thin boom along her left cheek to the corner of her mouth")
REAL=("Unretouched studio photograph: 85mm portrait lens, soft window light from the left, plain mid-grey backdrop, natural skin with visible pores and texture, no beauty retouching. Her irises are dark brown, almost black. She looks like a real person you could meet, a musician, not a fashion model. No text, no letters, no numbers, no logos.")
PORTRAIT="Head-and-shoulders portrait, facing the camera, calm and friendly, wearing a black ribbed turtleneck. She is {desc} Her hair and accessories: "+CONST+". No makeup. "+REAL
SHEET=("A character identity sheet: ten head-and-shoulders photographs of the SAME woman in a clean grid, two rows of five, thin white gutters, same scale, same grey backdrop and light, black ribbed turtleneck in every panel. Top row, left to right: front view; three-quarter view turned to her left; full profile facing her left; back of the head; full profile facing her right. Bottom row: eyes looking aside, lips closed; singing a high note with mouth wide open, eyes closed; a small closed-mouth smile; looking down, calm; laughing.\n\n"
       "Image 1 is the woman: match her face exactly in every panel (bone structure, nose, mouth, teeth, skin, eyes, age). In every panel: "+CONST+". No makeup. "+REAL)
GLAM=("Edit Image 1, a ten-panel sheet of one woman. Keep every panel exactly as it is: her face, bone structure, skin, eyes, teeth, expressions, haircut, purple streak, star clip, headset microphone, turtleneck, backdrop, light and grid.\n\nAdd only stage makeup for a big pop concert, the same in every panel: a sharp dramatic black winged eyeliner with a thin purple (#9B1DBE) line above it, full dark lashes, groomed bold brows, a soft sculpted contour, luminous skin and a matte deep berry lip. The same real woman, made up for the show. No text, no letters, no logos.")
CTX=("Edit Image 1, a still from a music video. Keep exactly: the framing, the camera angle, the position of her head and shoulders, the black and purple armour jacket, the stage behind her, the purple light, the haze, the film grain, the black blunt jaw-length bob with heavy bangs, the single purple streak on her right side, the single clay-orange star clip above her left ear and the thin headset microphone along her left cheek.\n\n"
     "Replace the woman completely with the woman in Image 2 (a ten-panel sheet of her face): her bone structure, skin tone, eyes (dark brown), nose, mouth, teeth and age {mk}, exactly as in Image 2. Do not keep anything of Image 1's face or makeup.\n\n"
     "She is singing happily, mouth naturally open on a vowel, relaxed eyes, like a real singer enjoying the gig, not a fashion pose. Unretouched: visible pores and skin texture under the stage light. No text, no letters, no logos.")
def sb(prompt,out,refs,what):
    open(out+".txt","w").write(prompt)
    cmd=[sys.executable,"scripts/sunburst.py","--prompt-file",out+".txt","--out",out,"--quality","xhigh","--n","1","--ar","16:9","--what",what]
    for r in refs: cmd+=["--ref",r]
    r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode: print("FAIL",out,(r.stdout+r.stderr)[-200:])
    return r.returncode
def one(k):
    d="characters/out/"
    sb(PORTRAIT.format(desc=V[k]),d+k+"-portrait",[],f"char portrait {k}")
    sb(SHEET,d+k+"-sheet",[d+k+"-portrait-1.png"],f"char sheet {k}")
    sb(GLAM,d+k+"-glam",[d+k+"-sheet-1.png"],f"char glam {k}")
    sb(CTX.format(mk="and no makeup"),d+k+"-ctx",["v2/plates/L03.jpg",d+k+"-sheet-1.png"],f"char ctx {k}")
    sb(CTX.format(mk="and her dramatic stage makeup (winged eyeliner with a purple line, bold brows, berry lip)"),d+k+"-ctxglam",["v2/plates/L03.jpg",d+k+"-glam-1.png"],f"char ctx glam {k}")
    return k
with ThreadPoolExecutor(6) as ex:
    for k in ex.map(one,V): print(k,"done")
