"""P.25 ③ キーで操作する — GIF。押しているキーだけ外から与える"""
import pyxel
from drive import Pilot, Rec

OUT = "g3_keys"
SCALE = 4
pyxel.init(160, 120, headless=True, capture_scale=SCALE, capture_sec=8)
pyxel.rseed(20260810)
rec = Rec(OUT, skip=150, frames=124, scale=SCALE)

pilot = Pilot()
held = 0
_btn = pyxel.btn


def btn(key):
    if key == pyxel.KEY_LEFT:
        return held < 0
    if key == pyxel.KEY_RIGHT:
        return held > 0
    return _btn(key)


pyxel.btn = btn

# ここからスライドのコードそのまま
x = 76
enemies = [[pyxel.rndi(0, 152), -i * 16] for i in range(16)]

while True:
    held = pilot.input(rec.n, x, enemies)  # 撮影用：キーを押す代わり

    pyxel.cls(1)
    pyxel.line(0, 112, 159, 112, 3)

    if pyxel.btn(pyxel.KEY_LEFT):
        x -= 2
    if pyxel.btn(pyxel.KEY_RIGHT):
        x += 2

    for enemy in enemies:
        enemy[1] += 2
        if enemy[1] > 120:
            enemy[0], enemy[1] = pyxel.rndi(0, 152), -8
        pyxel.rect(enemy[0], enemy[1], 8, 8, 8)

    pyxel.rect(x, 104, 8, 8, 10)
    pyxel.flip()
    # ここまで
    if not rec.tick():
        break

rec.save()
print("done")
