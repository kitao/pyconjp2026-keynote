"""Compare before and after renders of every slide and list what changed.

  python3 tools/inspect/diffall.py            compare render/hi_before with render/hi
  python3 tools/inspect/diffall.py A B        compare any two folders
  python3 tools/inspect/diffall.py A B --save also write the diffs to render/diff/

A single differing pixel is enough to list a slide, so nothing is missed.
"""

import sys, os, glob, json
import numpy as np
from PIL import Image

args = [a for a in sys.argv[1:] if not a.startswith("--")]
save = "--save" in sys.argv
A = args[0] if len(args) > 0 else "render/hi_before"
B = args[1] if len(args) > 1 else "render/hi"

pages = sorted(
    int(os.path.basename(f)[1:-4]) for f in glob.glob(f"{B}/P*.png")
)
if save:
    os.makedirs("render/diff", exist_ok=True)

SCALE = 2          # render/hi is 2x; probe coordinates are in 1920x1080

# Moving elements (GIFs, videos) land on a different frame every capture.
# Excluding a whole slide would hide real changes on it, so instead each diff
# is tested against the rectangles of those elements. The rectangles come from
# the motion records in render/probe.json, written by tools/inspect/probe.sh.
boxes = {}
try:
    for r in json.load(open("render/probe.json")):
        if r.get("t") == "motion":
            boxes.setdefault(r["p"], []).append(
                (r["x"] - 2, r["y"] - 2, r["x"] + r["w"] + 2, r["y"] + r["h"] + 2))
except Exception:
    print("no render/probe.json; run tools/inspect/probe.sh first\n")

changed, same, missing = [], [], []
for p in pages:
    fa, fb = f"{A}/P{p}.png", f"{B}/P{p}.png"
    if not os.path.exists(fa):
        missing.append(p)
        continue
    a = np.asarray(Image.open(fa).convert("RGB")).astype(np.int16)
    b = np.asarray(Image.open(fb).convert("RGB")).astype(np.int16)
    if a.shape != b.shape:
        changed.append((p, -1, "different size", None, 1))
        continue
    d = np.abs(a - b).sum(axis=2)
    n = int((d > 0).sum())
    if n == 0:
        same.append(p)
        continue
    ys, xs = np.nonzero(d)
    bbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    # Does any differing pixel fall outside the mask of moving elements?
    outside = n
    if p in boxes:
        mask = np.zeros(d.shape, dtype=bool)
        for bx0, by0, bx1, by1 in boxes[p]:
            mask[max(0, int(by0 * SCALE)):int(by1 * SCALE),
                 max(0, int(bx0 * SCALE)):int(bx1 * SCALE)] = True
        outside = int(((d > 0) & ~mask).sum())
    msg = f"{n:,}px differ  bbox x{bbox[0]}-{bbox[2]} y{bbox[1]}-{bbox[3]}"
    if outside != n:
        msg += f"  ({outside:,}px outside the moving elements)"
    changed.append((p, n, msg, bbox, outside))
    if save:
        m = (d > 0).astype(np.uint8) * 255
        Image.fromarray(m).save(f"render/diff/P{p}.png")

# Only a slide with no differing pixel outside those rectangles counts as a
# mere frame difference.
real = [c for c in changed if c[4] > 0]
anim = [c for c in changed if c[4] == 0]

print(f"── {A} → {B} ──")
print(f"unchanged {len(same)} / changed {len(changed)}"
      + (f" / missing {len(missing)}" if missing else ""))
if real:
    print(f"\n[ likely caused by the change ] {len(real)} slides - look at every one")
    for c in real:
        print(f"  P.{c[0]:<3} {c[2]}")
if anim:
    print(f"\n[ slides with moving elements ] {len(anim)} - probably just a "
          "different frame; check that the diff stays inside those elements")
    for c in anim:
        print(f"  P.{c[0]:<3} {c[2]}")
if missing:
    print("\nno counterpart: " + ", ".join(f"P.{p}" for p in missing))
