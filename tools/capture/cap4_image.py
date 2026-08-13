"""P.26 左 ── イメージエディタで宇宙飛行士を描いていく動画。

隕石はもう描いてある状態から始めて、左の8x8を1色ずつ塗っていく。
色を選ぶ → その色の画素を横につないで引く、の繰り返し。
"""

import pyxel

from edrive import Driver

RES = "../../demo/game/game.pyxres"
OUT = "g4_image"
SCALE = 5

drv = Driver(SCALE, sec=30)

import pyxel.editor  # noqa: E402

app = pyxel.editor.App(RES, "image")
ed = app._editor
ed.focus_x_var = 0
ed.focus_y_var = 15  # y=120 ... 自機と隕石の行

img = pyxel.images[0]

# 描くもとの絵を控えてから、左の8x8を消す（これから描くので）
art = [[img.pget(x, 120 + y) for x in range(8)] for y in range(8)]
for y in range(8):
    for x in range(8):
        img.pset(x, 120 + y, 0)


def pal_pos(c):
    # ColorPicker は (11,156)・1色8x8・8列
    return 16 + (c % 8) * 8, 161 + (c // 8) * 8


def cell_pos(cx, cy):
    # CanvasPanel は (11,16)・1マス8px
    return 16 + cx * 8, 21 + cy * 8


# 色ごとに、横に続く画素をまとめる
runs = {}
for y in range(8):
    x = 0
    while x < 8:
        c = art[y][x]
        if c == 0:
            x += 1
            continue
        x2 = x
        while x2 + 1 < 8 and art[y][x2 + 1] == c:
            x2 += 1
        runs.setdefault(c, []).append((x, x2, y))
        x = x2 + 1

# 面積の大きい色から。輪郭より先に形が出るので、絵が育つように見える
order = sorted(runs, key=lambda c: -sum(b - a + 1 for a, b, _ in runs[c]))

drv.moveto(120, 92, 1)
drv.wait(10)

for c in order:
    px, py = pal_pos(c)
    drv.moveto(px, py, 7)
    drv.click(pre=0, post=1)
    drv.wait(1)
    for x1, x2, y in runs[c]:
        sx, sy = cell_pos(x1, y)
        drv.moveto(sx, sy, 4)
        drv.seq.append((sx, sy, True))
        if x2 > x1:
            ex, _ = cell_pos(x2, y)
            drv.moveto(ex, sy, max(2, (x2 - x1) * 2), down=True)
        drv.wait(1, down=True)
        drv.wait(1, down=False)

# 描き上がりを少し見せてから頭に戻す
drv.moveto(120, 92, 8)
drv.wait(40)

print("コマ数", len(drv.seq))
drv.play(OUT)
print("done")
