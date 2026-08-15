#!/bin/sh
# ./checkall.sh [開始 [終了]]   範囲のページをまとめて検品し、要注意だけを並べる。
# check.sh は1ページを詳しく見る道具。こちらは「どのページを見るべきか」を先に知る道具。
# 既定は 1〜36（3章の手前まで）。
cd "$(dirname "$0")/../.." || exit 1

# Chrome は既定の場所を見る。別の場所に入れているときは環境変数 CHROME で渡す
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
FROM="${1:-1}"
TO="${2:-36}"

# 通しで1回だけ描く（page.sh をページ数ぶん呼ぶと marp の起動で時間がかかる）
npx --yes @marp-team/marp-cli@latest slides.md --no-stdin --html --allow-local-files \
  --theme-set theme/pyxel.css -o .check.html >/dev/null 2>&1 || { echo "変換に失敗"; exit 1; }
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

# 版面の規則が当てはまらないページ（表紙・章扉・全面素材・締め）は対象外にする
SPECIAL = set()
md = open("slides.md").read().split("\n---\n")
for i, page in enumerate(md):
    m = re.search(r"<!--\s*_class:\s*([^>]*?)\s*-->", page)
    cls = m.group(1).split() if m else []
    if {"cover", "hero", "section", "full", "closing", "image-main"} & set(cls):
        SPECIAL.add(i)
L, R, T, B, RULE_Y = 131, 1789, 268, 940, 210
HOUSE_Y = 999          # 住人とページ番号の帯の上端

def load(pg):
    for f in sorted(glob.glob(".check-p*.png")):
        if f"-{pg:02d}" in f or f"-{pg}." in f:
            return np.array(Image.open(f).convert("RGB")).astype(int)
    return None

print(f"── P.{frm}〜P.{to} の一括検品 ──")
print(f"{'頁':>4}  {'版面外':>6}  {'右余り':>6}  {'下余り':>6}  {'罫下':>5}  {'住人上':>6}  所見")
bad = []
for pg in range(frm, to + 1):
    if pg in SPECIAL:
        print(f"   {pg:>3}  {'':>6}  {'':>6}  {'':>6}  {'':>5}  {'':>6}  （特別レイアウト・対象外）")
        continue
    a = load(pg)
    if a is None:
        continue
    ink = (np.abs(a - 255).sum(axis=2) > 26)

    # 版面の外に墨があるか（左右）
    outside = ink[RULE_Y + 8:995, :L].any() or ink[RULE_Y + 8:995, R:].any()

    body = ink[RULE_Y + 8:995, L:R]
    ys = np.where(body.any(axis=1))[0]
    xs = np.where(body.any(axis=0))[0]
    if len(ys) == 0:
        continue
    top, bot = RULE_Y + 8 + ys.min(), RULE_Y + 8 + ys.max() + 1
    right = L + xs.max() + 1

    rule_gap = top - RULE_Y                 # 罫からいちばん上の墨まで
    house_gap = HOUSE_Y - bot               # いちばん下の墨から住人の帯まで
    right_left = R - right
    below = B - bot

    notes = []
    if outside:
        notes.append("版面の外に墨")
    if bot > B:
        notes.append(f"版面の下を{bot - B}px超過")
    if house_gap < 45:
        notes.append(f"住人に近い({house_gap}px)")
    if right_left > 150:
        notes.append(f"右が{right_left}px余る")
    if below > 150 and bot <= B:
        notes.append(f"下が{below}px余る")

    mark = "  " if not notes else "★ "
    print(f"{mark}{pg:>3}  {'あり' if outside else '—':>6}  {right_left:>6}  {below:>6}  "
          f"{rule_gap:>5}  {house_gap:>6}  {' / '.join(notes)}")
    if notes:
        bad.append(pg)

print()
print("要注意:", ", ".join(f"P.{p}" for p in bad) if bad else "なし")
PYEOF

rm -f .check.html .check.pdf .check-p*.png
