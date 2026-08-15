"""Measure how far down the actual ink reaches on every slide.

The page number and the residents in the footer are excluded. It looks at the
painted pixels rather than the DOM rectangles, so rounded corners and shadows
count. Used to refresh the measured list kept in theme/pyxel.css.

  python3 tools/bottom.py
"""

import glob, os, json
import numpy as np
from PIL import Image

# The footer band, which is a separate layer from the body; same idea as in
# tools/inspect/measure.py.
PAGENO_X = (120, 260)      # Page number, bottom left
HOUSE_X = (1500, 1830)     # Residents, bottom right
FOOT_Y = 950               # Everything below this y counts as the footer band
HOUSE_TOP = 999            # Top of the residents

SLIDE_W, SLIDE_H = 1920, 1080
LIMIT = 940                # Bottom of the type area, as used for text

try:
    motion = {int(k) for k in json.load(open("render/motion.json"))}
except Exception:
    motion = set()

rows = []
files = sorted(glob.glob("render/hi/P*.png"),
               key=lambda f: int(os.path.basename(f)[1:-4]))
for f in files:
    p = int(os.path.basename(f)[1:-4])
    im = Image.open(f).convert("RGB")
    k = im.size[0] // SLIDE_W          # Undo the 2x capture scale
    a = np.asarray(im).astype(np.int16)
    ink = np.abs(a - 255).sum(axis=2) > 26
    # Ignore the footer columns (page number, residents) only below FOOT_Y
    m = ink.copy()
    m[FOOT_Y * k:, PAGENO_X[0] * k:PAGENO_X[1] * k] = False
    m[FOOT_Y * k:, HOUSE_X[0] * k:HOUSE_X[1] * k] = False
    ys = np.nonzero(m.any(axis=1))[0]
    bottom = (ys.max() + 1) / k if len(ys) else 0
    rows.append((p, round(bottom, 1)))

print(f"{'pg':>3} {'ink bottom':>10}   {'vs 940':>7}   notes")
for p, b in rows:
    over = b - LIMIT
    note = []
    if over > 0:
        note.append(f"{over:.0f}px past the bottom")
    if b >= HOUSE_TOP:
        note.append(f"reaches the residents ({HOUSE_TOP})")
    tag = "  (has motion)" if p in motion else ""
    print(f"{p:>3} {b:>9.1f}   {over:>+7.1f}   {' / '.join(note)}{tag}")

worst = sorted((r for r in rows if r[1] > LIMIT), key=lambda r: -r[1])
print(f"\nslides past 940: {len(worst)}  "
      + ", ".join(f"P.{p}={b:.0f}" for p, b in worst))
