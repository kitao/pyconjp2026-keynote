#!/bin/sh
# ./checkall.sh [from [to]]   Inspect a range of slides and list only the ones
# worth a closer look. check.sh examines one slide in detail; this one tells
# you which slides to examine. Defaults to 1-36 (up to the start of chapter 3).
cd "$(dirname "$0")/../.." || exit 1

# Chrome is looked for in the default location; set CHROME to override it.
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
FROM="${1:-1}"
TO="${2:-36}"

# Render everything in one pass; calling page.sh per slide spends most of the
# time starting marp over and over.
npx --yes @marp-team/marp-cli@latest slides.md --no-stdin --html --allow-local-files \
  --theme-set theme/pyxel.css -o .check.html >/dev/null 2>&1 || { echo "conversion failed"; exit 1; }
python3 tools/slides/hl.py .check.html
"$CHROME" --headless --disable-gpu \
  --no-pdf-header-footer --virtual-time-budget=20000 \
  --print-to-pdf=.check.pdf "file://$PWD/.check.html" >/dev/null 2>&1
pdftoppm -r 96 -png -f "$FROM" -l "$TO" .check.pdf .check-p >/dev/null 2>&1

python3 - "$FROM" "$TO" << 'PYEOF'
import sys, glob, os, re
from PIL import Image
import numpy as np

frm, to = int(sys.argv[1]), int(sys.argv[2])

# Skip the slides the type-area rules do not apply to: cover, chapter title,
# full-bleed art and the closing.
SPECIAL = set()
md = open("slides.md").read().split("\n---\n")
for i, page in enumerate(md):
    m = re.search(r"<!--\s*_class:\s*([^>]*?)\s*-->", page)
    cls = m.group(1).split() if m else []
    if {"cover", "hero", "section", "full", "closing", "image-main"} & set(cls):
        SPECIAL.add(i)
L, R, T, B, RULE_Y = 131, 1789, 268, 940, 210
HOUSE_Y = 999          # Top of the band holding the residents and page number

def load(pg):
    for f in sorted(glob.glob(".check-p*.png")):
        if f"-{pg:02d}" in f or f"-{pg}." in f:
            return np.array(Image.open(f).convert("RGB")).astype(int)
    return None

print(f"-- slides {frm}-{to} --")
print(f"{'pg':>4}  {'out':>6}  {'right':>6}  {'below':>6}  {'rule':>5}  {'house':>6}  notes")
bad = []
for pg in range(frm, to + 1):
    if pg in SPECIAL:
        print(f"   {pg:>3}  {'':>6}  {'':>6}  {'':>6}  {'':>5}  {'':>6}  (special layout, skipped)")
        continue
    a = load(pg)
    if a is None:
        continue
    ink = (np.abs(a - 255).sum(axis=2) > 26)

    # Any ink outside the type area, left or right
    outside = ink[RULE_Y + 8:995, :L].any() or ink[RULE_Y + 8:995, R:].any()

    body = ink[RULE_Y + 8:995, L:R]
    ys = np.where(body.any(axis=1))[0]
    xs = np.where(body.any(axis=0))[0]
    if len(ys) == 0:
        continue
    top, bot = RULE_Y + 8 + ys.min(), RULE_Y + 8 + ys.max() + 1
    right = L + xs.max() + 1

    rule_gap = top - RULE_Y                 # Rule to the topmost ink
    house_gap = HOUSE_Y - bot               # Bottom ink to the residents' band
    right_left = R - right
    below = B - bot

    notes = []
    if outside:
        notes.append("ink outside the type area")
    if bot > B:
        notes.append(f"{bot - B}px below the type area")
    if house_gap < 45:
        notes.append(f"close to the residents ({house_gap}px)")
    if right_left > 150:
        notes.append(f"{right_left}px spare on the right")
    if below > 150 and bot <= B:
        notes.append(f"{below}px spare below")

    mark = "  " if not notes else "★ "
    print(f"{mark}{pg:>3}  {'yes' if outside else '-':>6}  {right_left:>6}  {below:>6}  "
          f"{rule_gap:>5}  {house_gap:>6}  {' / '.join(notes)}")
    if notes:
        bad.append(pg)

print()
print("worth a look:", ", ".join(f"P.{p}" for p in bad) if bad else "none")
PYEOF

rm -f .check.html .check.pdf .check-p*.png
