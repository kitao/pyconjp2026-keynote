"""P.23 ゲームを作ってみよう① 図形を描く — 静止画を撮る。

スライドのコードそのまま。撮影のために show() を flip()+screenshot() に置き換えただけ。
"""

import pyxel

OUT = "g1_shapes"

pyxel.init(160, 120, headless=True, capture_scale=4)

pyxel.cls(1)
pyxel.line(0, 112, 159, 112, 3)
pyxel.rect(76, 104, 8, 8, 10)
pyxel.rect(40, 20, 8, 8, 8)

pyxel.flip()
pyxel.screenshot(OUT, scale=4)
print("done")
