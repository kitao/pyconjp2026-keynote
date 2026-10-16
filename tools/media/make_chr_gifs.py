"""Build the two-frame animated GIFs of the Cursed Caverns residents.

The art is already final: assets/chr/*.png is frame one and *_2.png frame two.
The frame interval matches the game's own code (Pyxel runs at 30 fps).

  entities/player.py :  frame_count // 4 % 2  ->  4/30 s = 133 ms
  entities/slime.py  :  frame_count // 4 % 2  ->  133 ms
  entities/mummy.py  :  frame_count // 4 % 2  ->  133 ms
  entities/flower.py :  frame_count // 8 % 2  ->  8/30 s = 267 ms

The gem (gem_red) is a static tilemap tile and does not move in the game
either, so it gets no GIF. The pollen has frame-two art, but it
is left as a still: in the game it swaps between white-red and green-yellow
every frame (33 ms) and reads as a drifting mote, whereas on a static slide at
50 px it reads as nothing but a harsh flicker.
"""

from PIL import Image

from pathlib import Path

IMG = Path(__file__).resolve().parents[2] / "assets" / "chr"

# A slide is a still frame, so the game's own speed feels restless here.
# Everything is slowed by the same factor of two, which keeps the relative
# difference between the characters intact.
SLOW = 2

# Output name -> (frame one, frame two, frame length in the game in ms)
CHARS = [
    ("player",      "player",      "player_2",      133),
    ("player_r",    "player",      "player_2",      133),
    ("slime_green", "slime_green", "slime_green_2", 133),
    ("slime_red",   "slime_red",   "slime_red_2",   133),
    ("mummy",       "mummy",       "mummy_2",       133),
    ("mummy_r",     "mummy",       "mummy_2",       133),
    ("flower",      "flower",      "flower_2",      267),
]

# GIF has no partial transparency, so a colour unused by the art is reserved
# as the transparent key.
KEY = (255, 0, 255)


def to_paletted(im, palette=None):
    bg = Image.new("RGB", im.size, KEY)
    bg.paste(im, (0, 0), im)
    p = (bg.quantize(palette=palette, dither=Image.Dither.NONE) if palette else
         bg.quantize(colors=255, method=Image.MEDIANCUT))
    pal = p.getpalette()
    idx = next(i for i in range(len(pal) // 3) if tuple(pal[i * 3:i * 3 + 3]) == KEY)
    return p, idx


def main():
    for out, a, b, ms in CHARS:
        f1 = Image.open(f"{IMG}/{a}.png").convert("RGBA")
        f2 = Image.open(f"{IMG}/{b}.png").convert("RGBA")
        # One palette for both frames also preserves colours unique to frame two.
        combined = Image.new("RGBA", (f1.width, f1.height * 2))
        combined.paste(f1, (0, 0))
        combined.paste(f2, (0, f1.height))
        palette, _ = to_paletted(combined)
        p1, t1 = to_paletted(f1, palette)
        p2, _ = to_paletted(f2, palette)
        d = int(round(ms * SLOW / 10.0)) * 10
        p1.save(f"{IMG}/{out}.gif", save_all=True, append_images=[p2],
                duration=d, loop=0, disposal=2, transparency=t1)
        print(f"  {out}.gif   {d} ms/frame (game: {ms} ms)   {f1.size[0]}x{f1.size[1]}")


if __name__ == "__main__":
    main()
