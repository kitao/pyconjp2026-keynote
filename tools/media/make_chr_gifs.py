"""住人キャラの2コマアニメGIFを作る。

素材は既に確定している chr_*.png（1コマ目）と chr_*_2.png（2コマ目）をそのまま使う。
コマ替えの間隔は Cursed Caverns 本体のコードに合わせる（Pyxel は 30fps）。

  entities/player.py :  frame_count // 4 % 2  →  4/30 秒 = 133ms
  entities/slime.py  :  frame_count // 4 % 2  →  133ms
  entities/mummy.py  :  frame_count // 4 % 2  →  133ms
  entities/flower.py :  frame_count // 8 % 2  →  8/30 秒 = 267ms

宝石（chr_gem_red）はタイルマップの静止タイルで、ゲーム中も動かないので作らない。
花粉（chr_pollen）は 2コマ目の素材（chr_pollen_2.png）を用意したが、GIF にはしない。
本体は1フレーム周期（33ms）で色が白赤→緑黄と入れ替わる。ゲームの中では舞う粒に見えるが、
止まった画面で50pxに置くと点滅にしか見えず、どぎつい。静止画のまま使う。
"""

from PIL import Image, ImageOps

import os
IMG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

# スライドは止まった画面なので、ゲームと同じ速さだと忙しない。
# 全キャラ共通で2倍ゆっくりにする（キャラごとの速さの差はそのまま保たれる）。
SLOW = 2

# 出力名 → (1コマ目, 2コマ目, ゲーム本体での1コマの長さms, 左右反転)
CHARS = [
    ("chr_player",      "chr_player",      "chr_player_2",      133, False),
    ("chr_player_r",    "chr_player",      "chr_player_2",      133, False),
    ("chr_player_l",    "chr_player",      "chr_player_2",      133, True),
    ("chr_slime_green", "chr_slime_green", "chr_slime_green_2", 133, False),
    ("chr_slime_red",   "chr_slime_red",   "chr_slime_red_2",   133, False),
    ("chr_mummy",       "chr_mummy",       "chr_mummy_2",       133, False),
    ("chr_mummy_r",     "chr_mummy",       "chr_mummy_2",       133, False),
    ("chr_mummy_l",     "chr_mummy",       "chr_mummy_2",       133, True),
    ("chr_flower",      "chr_flower",      "chr_flower_2",      267, False),
]

# GIF は半透明を持てないので、絵に使われていない色を透明用に割り当てる
KEY = (255, 0, 255)


def to_paletted(im):
    im = im.convert("RGBA")
    bg = Image.new("RGBA", im.size, KEY + (255,))
    bg.paste(im, (0, 0), im)
    p = bg.convert("RGB").quantize(colors=255, method=Image.MEDIANCUT)
    pal = p.getpalette()
    idx = 0
    best = 10 ** 9
    for i in range(len(pal) // 3):
        r, g, b = pal[i * 3:i * 3 + 3]
        dist = (r - KEY[0]) ** 2 + (g - KEY[1]) ** 2 + (b - KEY[2]) ** 2
        if dist < best:
            best, idx = dist, i
    return p, idx


def main():
    for out, a, b, ms, flip in CHARS:
        f1 = Image.open(f"{IMG}/{a}.png").convert("RGBA")
        f2 = Image.open(f"{IMG}/{b}.png").convert("RGBA")
        if flip:
            f1, f2 = ImageOps.mirror(f1), ImageOps.mirror(f2)
        p1, t1 = to_paletted(f1)
        p2, _ = to_paletted(f2)
        d = int(round(ms * SLOW / 10.0)) * 10
        p1.save(f"{IMG}/{out}.gif", save_all=True, append_images=[p2],
                duration=d, loop=0, disposal=2, transparency=t1)
        print(f"  {out}.gif   {d}ms/コマ（本体は{ms}ms）   {f1.size[0]}x{f1.size[1]}")


main()
