"""Build the two-frame animated GIFs of the Cursed Caverns residents.

The art is already final: chr_*.png is frame one and chr_*_2.png frame two.
The frame interval matches the game's own code (Pyxel runs at 30 fps).

  entities/player.py :  frame_count // 4 % 2  ->  4/30 s = 133 ms
  entities/slime.py  :  frame_count // 4 % 2  ->  133 ms
  entities/mummy.py  :  frame_count // 4 % 2  ->  133 ms
  entities/flower.py :  frame_count // 8 % 2  ->  8/30 s = 267 ms

The gem (chr_gem_red) is a static tilemap tile and does not move in the game
either, so it gets no GIF. The pollen (chr_pollen) has frame-two art, but it
is left as a still: in the game it swaps between white-red and green-yellow
every frame (33 ms) and reads as a drifting mote, whereas on a static slide at
50 px it reads as nothing but a harsh flicker.
"""

from PIL import Image, ImageOps

import os
IMG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

# A slide is a still frame, so the game's own speed feels restless here.
# Everything is slowed by the same factor of two, which keeps the relative
# difference between the characters intact.
SLOW = 2

# Output name -> (frame one, frame two, frame length in the game in ms, flip)
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

# GIF has no partial transparency, so a colour unused by the art is reserved
# as the transparent key.
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
        print(f"  {out}.gif   {d} ms/frame (game: {ms} ms)   {f1.size[0]}x{f1.size[1]}")


main()
