"""変更前後の全ページ画像を突き合わせ、変わったページを全部挙げる。

  python3 tools/diffall.py                       render/hi_before と render/hi を比べる
  python3 tools/diffall.py A B                   任意の2つのフォルダを比べる
  python3 tools/diffall.py A B --save            違うページの差分画像を render/diff/ に出す

変わったページは1枚も見逃さないため、1ピクセルでも違えば挙げる。
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

SCALE = 2          # render/hi は2倍解像度。probe の座標は1920x1080基準

# 動きのある要素（GIF・動画）は撮るたびにコマが変わる。ページ単位で除外すると
# そのページの本当の変化まで見逃すので、差分の位置がその要素の矩形に入るかで判定する。
# 矩形は render/probe.json の motion レコード（tools/probe.sh で作る）
boxes = {}
try:
    for r in json.load(open("render/probe.json")):
        if r.get("t") == "motion":
            boxes.setdefault(r["p"], []).append(
                (r["x"] - 2, r["y"] - 2, r["x"] + r["w"] + 2, r["y"] + r["h"] + 2))
except Exception:
    print("※ render/probe.json がありません。先に tools/probe.sh を走らせてください\n")

changed, same, missing = [], [], []
for p in pages:
    fa, fb = f"{A}/P{p}.png", f"{B}/P{p}.png"
    if not os.path.exists(fa):
        missing.append(p)
        continue
    a = np.asarray(Image.open(fa).convert("RGB")).astype(np.int16)
    b = np.asarray(Image.open(fb).convert("RGB")).astype(np.int16)
    if a.shape != b.shape:
        changed.append((p, -1, "寸法が違う", None, 1))
        continue
    d = np.abs(a - b).sum(axis=2)
    n = int((d > 0).sum())
    if n == 0:
        same.append(p)
        continue
    ys, xs = np.nonzero(d)
    bbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    # 動く要素の矩形をすべて塗ったマスクの外に、差分が1画素でも残るかを見る
    outside = n
    if p in boxes:
        mask = np.zeros(d.shape, dtype=bool)
        for bx0, by0, bx1, by1 in boxes[p]:
            mask[max(0, int(by0 * SCALE)):int(by1 * SCALE),
                 max(0, int(bx0 * SCALE)):int(bx1 * SCALE)] = True
        outside = int(((d > 0) & ~mask).sum())
    msg = f"差分 {n:,}px  範囲 x{bbox[0]}〜{bbox[2]} y{bbox[1]}〜{bbox[3]}"
    if outside != n:
        msg += f"  （うち動く要素の外 {outside:,}px）"
    changed.append((p, n, msg, bbox, outside))
    if save:
        m = (d > 0).astype(np.uint8) * 255
        Image.fromarray(m).save(f"render/diff/P{p}.png")

# 動く要素の矩形の外に差分が1画素も残らないものだけ「コマ違い」とする
real = [c for c in changed if c[4] > 0]
anim = [c for c in changed if c[4] == 0]

print(f"── {A} → {B} ──")
print(f"変化なし {len(same)}ページ / 変化あり {len(changed)}ページ"
      + (f" / 比較先なし {len(missing)}ページ" if missing else ""))
if real:
    print(f"\n■ CSS の変更によるとみられる差分（{len(real)}ページ）— 全部その目で確かめること")
    for c in real:
        print(f"  P.{c[0]:<3} {c[2]}")
if anim:
    print(f"\n□ 動きのある要素を含むページ（{len(anim)}ページ）— コマ違いの可能性。"
          "差分の位置がその要素の中に収まっているかを見る")
    for c in anim:
        print(f"  P.{c[0]:<3} {c[2]}")
if missing:
    print("\n比較先が無いページ: " + ", ".join(f"P.{p}" for p in missing))
