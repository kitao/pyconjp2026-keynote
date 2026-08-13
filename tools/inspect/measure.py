"""ページの寸法を測る道具。

毎回その場で測定コードを書くと、範囲の取り方を間違えて別の要素を
拾ってしまう（壁を住人と数える、枠線と背景を混ぜる、など）。
位置が決まっているものは、ここに定数として置く。

  python3 tools/inspect/measure.py 32          # P.32 の縦の構成を出す
  python3 tools/inspect/measure.py 32 --bands  # 墨のある帯を全部並べる
"""

import sys
import numpy as np
from PIL import Image

# ── テンプレの不変項目（動かしてはいけない） ──────────────
SLIDE_W, SLIDE_H = 1920, 1080
PAD_L, PAD_R = 131, 1789        # 版面の左右
BODY_TOP, BODY_BOT = 268, 940   # 本文の版面
RULE_Y = 210                    # 見出しの下の罫

# ── 下の帯（本文とは別の層。測るときは必ず除く） ────────────
# 住人は右下、ページ番号は左下。どちらも y999 以降。
HOUSE_X0, HOUSE_X1 = 1550, 1810   # 住人だけを見る幅。3体は x1559〜1788 に並ぶ
# 幅を狭めると1体目（x1559〜1608）を本文と数えてしまい、「版面を大きく超過」という嘘の値が出る
PAGENO_X0, PAGENO_X1 = 120, 240   # ページ番号だけを見る幅
FOOT_Y0 = 950                     # この下は下の帯として扱う

# 本文を測るときの幅。中身は版面の中央1500px（左端210）に置くのが基本だが、
# 版面いっぱいに広がる型（two-up / .chron / .pack）もあるので版面で取る。
BODY_X0, BODY_X1 = PAD_L, PAD_R


def load(page):
    a = np.array(Image.open(f"render/P{page}.png").convert("RGB")).astype(int)
    if a.shape[1] != SLIDE_W:
        raise SystemExit(f"想定と違う画像の幅: {a.shape[1]}（{SLIDE_W} のはず）")
    return a


def ink(a, th=26):
    return np.abs(a - 255).sum(axis=2) > th


def bands(m, y0, y1, x0, x1, min_h=3):
    """墨のある横帯を上から順に返す。"""
    sub = m[y0:y1, x0:x1]
    rows = sub.sum(axis=1) > 2
    out, s = [], None
    for i, v in enumerate(rows):
        if v and s is None:
            s = i
        if not v and s is not None:
            if i - s >= min_h:
                out.append((y0 + s, y0 + i - 1))
            s = None
    if s is not None and (y1 - y0) - s >= min_h:
        out.append((y0 + s, y1 - 1))
    return out


def span_x(m, y0, y1, x0, x1):
    sub = m[y0:y1 + 1, x0:x1]
    xs = np.where(sub.any(axis=0))[0]
    return (x0 + xs.min(), x0 + xs.max()) if len(xs) else (None, None)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    page = int(sys.argv[1])
    show_bands = "--bands" in sys.argv
    a = load(page)
    m = ink(a)

    # 本文（下の帯は含めない）
    body = bands(m, RULE_Y + 8, FOOT_Y0, BODY_X0, BODY_X1)
    # 下の帯（それぞれ専用の幅で見る。ここを広く取ると本文を巻き込む）
    house = bands(m, FOOT_Y0, SLIDE_H, HOUSE_X0, HOUSE_X1)
    pageno = bands(m, FOOT_Y0, SLIDE_H, PAGENO_X0, PAGENO_X1)

    print(f"── P.{page} ──")
    if not body:
        print("本文に墨がない")
        return
    top, bot = body[0][0], body[-1][1]
    l, r = span_x(m, RULE_Y + 8, FOOT_Y0 - 1, BODY_X0, BODY_X1)

    print(f"本文      y{top}〜{bot}   x{l}〜{r}")
    print(f"  罫({RULE_Y})からの下がり  {top - RULE_Y} px")
    print(f"  版面の下({BODY_BOT})まで   {BODY_BOT - bot} px" +
          ("   ← はみ出している" if bot > BODY_BOT else ""))
    print(f"  版面の右({PAD_R})まで     {PAD_R - r} px")
    if house:
        print(f"住人      y{house[0][0]}〜{house[-1][1]}   本文からのあき {house[0][0] - bot} px")
    if pageno:
        print(f"ページ番号 y{pageno[0][0]}〜{pageno[-1][1]}")

    if show_bands:
        print("\n墨のある帯:")
        prev = None
        for y0, y1 in body:
            bl, br = span_x(m, y0, y1, BODY_X0, BODY_X1)
            gap = "" if prev is None else f"  ↑あき {y0 - prev} px"
            print(f"  y{y0:4}〜{y1:<4} 高さ{y1 - y0 + 1:4}  x{bl}〜{br}{gap}")
            prev = y1


if __name__ == "__main__":
    main()
