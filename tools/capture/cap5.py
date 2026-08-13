"""P.27 ⑤ 絵と音を入れる — 動画（音つき）

GIF だとループ再生になって音も乗らないので、P.26 と同じく MP4 にする。
音は headless では鳴らないので、BGM と効果音を別々に WAV へ書き出しておき、
make_video.py 側で「BGM を敷いて、当たったコマに効果音を重ねる」形で合成する。
"""
import pyxel
from drive import Pilot, Rec

OUT = "g5_done"
SCALE = 4
# 当たったらゲームオーバー。開始から撮り、当たって止まった画を1秒残して終える。
# この種だと初被弾は 209コマめ（7.0秒）。頭から撮るので BGM も曲の頭から鳴る
SKIP = 0
FRAMES = 240
FPS = 30
pyxel.init(160, 120, headless=True, capture_scale=SCALE, capture_sec=10)
pyxel.rseed(20260849)
rec = Rec(OUT, skip=SKIP, frames=FRAMES, scale=SCALE)

pilot = Pilot()
game_over = False
TAIL = 30   # 撮影用：止まった画を1秒ぶん残す
tail = None
held = 0
hits = []  # 効果音を鳴らすコマ（録画開始からの相対）
_btn = pyxel.btn


def btn(key):
    if key == pyxel.KEY_LEFT:
        return held < 0
    if key == pyxel.KEY_RIGHT:
        return held > 0
    return _btn(key)


pyxel.btn = btn

# ここからスライドのコードそのまま
pyxel.load("../../demo/game/game.pyxres")
pyxel.gen_bgm(7, 0, 3, 0, play=True)
x = 76
enemies = [[pyxel.rndi(0, 152), -i * 16] for i in range(16)]

while True:
    held = pilot.input(rec.n, x, enemies)  # 撮影用：キーを押す代わり

    pyxel.blt(0, 0, 0, 0, 0, 160, 120)

    if pyxel.btn(pyxel.KEY_LEFT) and not game_over:
        x -= 2
    if pyxel.btn(pyxel.KEY_RIGHT) and not game_over:
        x += 2

    for enemy in enemies:
        if not game_over:
            enemy[1] += 2
            if enemy[1] > 120:
                enemy[0], enemy[1] = pyxel.rndi(0, 152), -8
            if abs(enemy[0] - x) < 8 and abs(enemy[1] - 104) < 8:
                pyxel.play(3, 0)
                game_over = True
                hits.append(rec.n - SKIP)  # 撮影用：あとで音を重ねる位置
                tail = TAIL  # 撮影用：止まった画を1秒残す
        pyxel.blt(enemy[0], enemy[1], 0, 8, 120, 8, 8, 0)

    pyxel.blt(x, 104, 0, 0, 120, 8, 8, 0)
    pyxel.flip()
    # ここまで
    if not rec.tick():
        break
    if tail is not None:  # 撮影用：止まった画を数コマ残して終える
        tail -= 1
        if tail <= 0:
            break

rec.save()

# 音を別に書き出す（動画に重ねるため）。
# BGM は頭から流れているので、捨てたぶん(SKIP)も含めた長さで書き出して、
# 合成側で SKIP コマぶん先頭を落として使う。
# gen_bgm が返すのは MML のリストで、musics には入らない。書き出すには
# 同じ引数で呼び直して（seed が同じなので同じ曲）、空いている枠に入れ直す
hits = [h for h in hits if h >= 0]
mml_list = pyxel.gen_bgm(7, 0, 3, 0)
for i, mml in enumerate(mml_list):
    pyxel.sounds[16 + i].mml(mml)
pyxel.musics[7].set(*[[16 + i] for i in range(len(mml_list))])
pyxel.musics[7].save("bgm.wav", (SKIP + FRAMES) / FPS + 1)
# 効果音の長さは音そのものから決める。指定が実際より長いと、その秒数を
# 埋めるためにループして「バンバン」と2回鳴った音になる。
# notes 4つ × speed 9 ÷ 120 = 0.30 秒
_se = pyxel.sounds[0]
_se.save("snd_hit.wav", len(_se.notes) * _se.speed / 120)
open("g5_done_hits.txt", "w").write(",".join(map(str, hits)) + "\n" + str(SKIP))
print("当たったコマ", hits)
print("done")
