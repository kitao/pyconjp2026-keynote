"""P.26 右 ── サウンドエディタで「ぶつかったときの音」を作っていく動画。

何もない状態から始めて、
①ピアノロールに音符を1音ずつ置き、
②下の TON / VOL / EFX を1文字ずつ入力し、
③再生ボタンで2回鳴らす。
操作の物語＝「ドットを打つ → パラメータを決める → 聴いてみる」。
"""

import pyxel

from edrive import Driver

RES = "../../demo/game/game.pyxres"
OUT = "g4_sound"
SCALE = 5

drv = Driver(SCALE, sec=40)

import pyxel.editor  # noqa: E402

app = pyxel.editor.App(RES, "sound")
ed = app._editor
ed.sound_index_var = 0  # ぶつかったときの音

snd = pyxel.sounds[0]
notes = list(snd.notes)
tones = list(snd.tones)
volumes = list(snd.volumes)
effects = list(snd.effects)
print("音符", notes, "音色", tones, "音量", volumes, "効果", effects)
snd.notes.clear()
snd.tones.clear()
snd.volumes.clear()
snd.effects.clear()


def roll_pos(step, note):
    # PianoRoll は (30,25)。1ステップ4px・1音2px、下から上へ
    return 33 + step * 4, 27 + (59 - note) * 2


# フィールドの値 → 押すキー（pyxel.editor.sound_field のキー表と同じ並び）
KEYS = {
    "tone": [pyxel.KEY_T, pyxel.KEY_S, pyxel.KEY_P, pyxel.KEY_N],
    "vol": [getattr(pyxel, f"KEY_{i}") for i in range(8)],
    "efx": [pyxel.KEY_N, pyxel.KEY_S, pyxel.KEY_V, pyxel.KEY_F, pyxel.KEY_H, pyxel.KEY_Q],
}

drv.moveto(120, 100, 1)
drv.wait(12)

# ① 音符を置く
for i, n in enumerate(notes):
    x, y = roll_pos(i, n)
    drv.moveto(x, y, 12 if i == 0 else 9)
    drv.wait(2)
    drv.click(pre=0, post=6)

# ② 音符を置き終えたら、マウスは最後の音符のすぐ右下へ少しだけ退く
#    （音符の赤い四角に重ねない。大きく動かすと視線が散る）。ここからはキーボードだけ。
#    ↓ でフォーカスを 音符 → TON → VOL → EFX と移し、1文字ずつ入力する
#    （空のフィールドに降りるとカーソルは行頭に戻る）
drv.moveto(56, 106, 7)
drv.wait(8)
for vals, table in ((tones, "tone"), (volumes, "vol"), (effects, "efx")):
    drv.key(pyxel.KEY_DOWN, post=7)
    for v in vals:
        drv.key(KEYS[table][v], post=6)
    drv.wait(3)
drv.wait(8)

# ③ SPACE で再生（ヘルプ表示どおり PLAY:SPACE。マウスは動かさない）。
#    押した瞬間のコマ番号を控えて、あとで音を重ねる
plays = []
for _ in range(2):
    plays.append(len(drv.seq) + 1)
    # 音は 0.30 秒。鳴る → 間 → もう一度、と読めるよう無音を 2 秒ほどとる
    drv.key(pyxel.KEY_SPACE, post=72)

drv.wait(22)

print("コマ数", len(drv.seq))
print("再生コマ", plays)
open("g4_sound_plays.txt", "w").write(",".join(map(str, plays)) + "\n" + str(len(drv.seq)))
drv.play(OUT)

# 操作の結果、データが元通りに入力できたかの検算（play() の中で実際に操作される）
assert list(snd.notes) == notes, list(snd.notes)
assert list(snd.tones) == tones, list(snd.tones)
assert list(snd.volumes) == volumes, list(snd.volumes)
assert list(snd.effects) == effects, list(snd.effects)
print("検算OK: 操作でデータが元通りに入力された")

# 音を別に書き出しておく（動画に重ねるため）。長さは音そのものから計算する
_se = pyxel.sounds[0]
_se.save("snd_hit.wav", len(_se.notes) * _se.speed / 120)
print("done")
