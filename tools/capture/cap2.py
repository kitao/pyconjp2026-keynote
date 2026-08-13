"""P.24 ② 図形を動かす — GIF"""
import pyxel
from drive import Rec

OUT = "g2_move"
SCALE = 4
pyxel.init(160, 120, headless=True, capture_scale=SCALE, capture_sec=8)
pyxel.rseed(20260810)
rec = Rec(OUT, skip=150, frames=124, scale=SCALE)

# ここからスライドのコードそのまま
enemies = [[pyxel.rndi(0, 152), -i * 16] for i in range(16)]

while True:
    pyxel.cls(1)
    pyxel.line(0, 112, 159, 112, 3)

    for enemy in enemies:
        enemy[1] += 2
        if enemy[1] > 120:
            enemy[0], enemy[1] = pyxel.rndi(0, 152), -8
        pyxel.rect(enemy[0], enemy[1], 8, 8, 8)

    pyxel.rect(76, 104, 8, 8, 10)
    pyxel.flip()
    # ここまで
    if not rec.tick():
        break

rec.save()
print("done")
