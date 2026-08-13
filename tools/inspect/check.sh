#!/bin/sh
# ./check.sh N   指定ページを描画し、機械で見つかる不具合を全部出す。
# 「直した箇所だけ見て完成と言う」のを防ぐための道具。
# 出力を読まずに報告しないこと。
cd "$(dirname "$0")/../.." || exit 1
[ -z "$1" ] && { echo "使い方: ./check.sh <ページ番号>"; exit 1; }
tools/inspect/page.sh "$1" >/dev/null 2>&1 || { echo "描画に失敗"; exit 1; }

python3 - "$1" << 'PYEOF'
import sys, math
from PIL import Image

n = int(sys.argv[1])
im = Image.open(f"render/P{n}.png").convert("RGB")
px = im.load()
W, H = im.size

# 版面（テンプレの不変項目）
L, R = 131, 1789
T, B = 268, 940          # 本文の版面。罫は y=210、ページ番号と住人は y>=999
RULE_Y = 210

def ink(x, y, th=26):
    c = px[x, y]
    return math.sqrt(sum((c[i] - 255) ** 2 for i in range(3))) > th

print(f"── P{n} の検品 ──")

# 1) 版面からのはみ出し
over = []
for y in range(RULE_Y + 8, 995):
    for x in (list(range(0, L)) + list(range(R, W))):
        if ink(x, y):
            over.append((x, y)); break
    if len(over) > 3: break
print(f"[版面はみ出し] {'なし' if not over else 'あり ' + str(over[:3])}")

# 2) 本文領域の上下左右の使い残し
xs, ys = [], []
for y in range(RULE_Y + 8, 995):
    for x in range(L, R):
        if ink(x, y): xs.append(x); ys.append(y)
if xs:
    print(f"[中身の範囲] {min(xs)},{min(ys)} .. {max(xs)+1},{max(ys)+1}")
    print(f"[使い残し]   右 {R-(max(xs)+1)}px / 下 {B-(max(ys)+1)}px"
          f"{'  ← 100px以上余っている' if (R-(max(xs)+1) > 100 or B-(max(ys)+1) > 100) else ''}")

# 3) 横帯ごとの隙間（近接の原則が守られているか）
rows = [any(ink(x, y) for x in range(L, R)) for y in range(RULE_Y + 8, 995)]
bands, s = [], None
for i, v in enumerate(rows):
    y = RULE_Y + 8 + i
    if v and s is None: s = y
    if not v and s is not None: bands.append((s, y)); s = None
if s is not None: bands.append((s, 995))
print(f"[横帯] {len(bands)}本")
prev = None
gaps = []
for a, b in bands:
    g = a - prev if prev is not None else None
    if g is not None: gaps.append(g)
    print(f"   {a:4}..{b:4}  高さ{b-a:3}  すき間 {g if g is not None else '—'}")
    prev = b
if len(gaps) >= 3:
    mn, mx = min(gaps), max(gaps)
    if mx and mn / mx > 0.75:
        print(f"   ← すき間が {mn}〜{mx} で均一。塊の区切りが立っていない可能性")

# 4) 左右2枚組の対称性
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
    print(f"[左右] 左 {lw}x{lh} / 右 {rw}x{rh}"
          f"{'  ← 高さが ' + str(d) + 'px ずれている' if d > 4 else '  高さ一致'}")
PYEOF

open "render/P$1.png"
