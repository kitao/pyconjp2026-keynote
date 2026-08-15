#!/bin/sh
# ./check.sh N   Render one slide and report every fault a machine can find.
# The point of this tool is to stop "I looked at the bit I changed, it is done".
# Do not report a result without reading the output.
cd "$(dirname "$0")/../.." || exit 1
[ -z "$1" ] && { echo "usage: ./check.sh <slide number>"; exit 1; }
tools/inspect/page.sh "$1" >/dev/null 2>&1 || { echo "render failed"; exit 1; }

python3 - "$1" << 'PYEOF'
import sys, math
from PIL import Image

n = int(sys.argv[1])
im = Image.open(f"render/P{n}.png").convert("RGB")
px = im.load()
W, H = im.size

# The type area (fixed by the template)
L, R = 131, 1789
T, B = 268, 940          # Body area. The rule sits at y=210; the page number
                         # and the residents live at y>=999.
RULE_Y = 210

def ink(x, y, th=26):
    c = px[x, y]
    return math.sqrt(sum((c[i] - 255) ** 2 for i in range(3))) > th

print(f"-- slide {n} --")

# 1) Ink outside the type area
over = []
for y in range(RULE_Y + 8, 995):
    for x in (list(range(0, L)) + list(range(R, W))):
        if ink(x, y):
            over.append((x, y)); break
    if len(over) > 3: break
print(f"[outside]  {'none' if not over else 'yes ' + str(over[:3])}")

# 2) Space left unused on each side of the body area
xs, ys = [], []
for y in range(RULE_Y + 8, 995):
    for x in range(L, R):
        if ink(x, y): xs.append(x); ys.append(y)
if xs:
    print(f"[extent]   {min(xs)},{min(ys)} .. {max(xs)+1},{max(ys)+1}")
    print(f"[unused]   right {R-(max(xs)+1)}px / bottom {B-(max(ys)+1)}px"
          f"{'  <- over 100px to spare' if (R-(max(xs)+1) > 100 or B-(max(ys)+1) > 100) else ''}")

# 3) Gaps between horizontal bands, i.e. whether proximity still groups things
rows = [any(ink(x, y) for x in range(L, R)) for y in range(RULE_Y + 8, 995)]
bands, s = [], None
for i, v in enumerate(rows):
    y = RULE_Y + 8 + i
    if v and s is None: s = y
    if not v and s is not None: bands.append((s, y)); s = None
if s is not None: bands.append((s, 995))
print(f"[bands]    {len(bands)}")
prev = None
gaps = []
for a, b in bands:
    g = a - prev if prev is not None else None
    if g is not None: gaps.append(g)
    print(f"   {a:4}..{b:4}  height {b-a:3}  gap {g if g is not None else '-'}")
    prev = b
if len(gaps) >= 3:
    mn, mx = min(gaps), max(gaps)
    if mx and mn / mx > 0.75:
        print(f"   <- gaps run {mn}-{mx}, near uniform; the groups may not read as groups")

# 4) Symmetry of a left/right pair
half = (L + R) // 2
def box(x0, x1):
    xs, ys = [], []
    for y in range(RULE_Y + 8, 995):
        for x in range(x0, x1):
            if ink(x, y): xs.append(x); ys.append(y)
    return (min(xs), min(ys), max(xs)+1, max(ys)+1) if xs else None
lb, rb = box(L, half), box(half, R)
if lb and rb:
    lw, lh = lb[2]-lb[0], lb[3]-lb[1]
    rw, rh = rb[2]-rb[0], rb[3]-rb[1]
    d = abs(lh - rh)
    print(f"[pair]     left {lw}x{lh} / right {rw}x{rh}"
          f"{'  <- heights differ by ' + str(d) + 'px' if d > 4 else '  heights match'}")
PYEOF

open "render/P$1.png"
