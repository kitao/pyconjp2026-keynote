"""全ページの「中身の実インクの下端」を、ページ番号と住人を除いて測る。

theme/pyxel.css の 237〜247 行が持っている実測一覧を更新するための道具。
DOM の矩形ではなく、実際に描かれた画素の下端を見る（角丸の裾や影も含む）。

  python3 tools/bottom.py
"""

import glob, os, json
import numpy as np
from PIL import Image

# 下の帯（本文とは別の層）。tools/inspect/measure.py と同じ考え方
PAGENO_X = (120, 260)      # 左下のページ番号
HOUSE_X = (1500, 1830)     # 右下の住人
FOOT_Y = 950               # この y から下は下の帯として扱う
HOUSE_TOP = 999            # 住人の頭

SLIDE_W, SLIDE_H = 1920, 1080
LIMIT = 940                # 版面の下端（文字の基準）

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
    k = im.size[0] // SLIDE_W          # 2倍で撮っているぶんを戻す
    a = np.asarray(im).astype(np.int16)
    ink = np.abs(a - 255).sum(axis=2) > 26
    # 下の帯にあたる列（ページ番号・住人）は、y>=FOOT_Y の範囲だけ無視する
    m = ink.copy()
    m[FOOT_Y * k:, PAGENO_X[0] * k:PAGENO_X[1] * k] = False
    m[FOOT_Y * k:, HOUSE_X[0] * k:HOUSE_X[1] * k] = False
    ys = np.nonzero(m.any(axis=1))[0]
    bottom = (ys.max() + 1) / k if len(ys) else 0
    rows.append((p, round(bottom, 1)))

print(f"{'頁':>3} {'中身の下端':>9}   {'940から':>7}   所見")
for p, b in rows:
    over = b - LIMIT
    note = []
    if over > 0:
        note.append(f"下端を{over:.0f}px 下回る")
    if b >= HOUSE_TOP:
        note.append(f"★住人の頭({HOUSE_TOP})に達している")
    tag = "  ※動きあり" if p in motion else ""
    print(f"{p:>3} {b:>9.1f}   {over:>+7.1f}   {' / '.join(note)}{tag}")

worst = sorted((r for r in rows if r[1] > LIMIT), key=lambda r: -r[1])
print(f"\n940を超えているページ {len(worst)} 枚: "
      + ", ".join(f"P.{p}={b:.0f}" for p, b in worst))
