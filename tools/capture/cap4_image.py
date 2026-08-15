"""Slide 26, left: drawing the astronaut in the image editor, as a video.

It starts with the meteor already drawn and fills the 8x8 sprite on the left
one colour at a time: pick a colour, then drag out the runs of pixels that use
it, and repeat.
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
ed.focus_y_var = 15  # y=120: the row holding the player and the meteor

img = pyxel.images[0]

# Keep a copy of the finished art, then clear the 8x8 that is about to be drawn.
art = [[img.pget(x, 120 + y) for x in range(8)] for y in range(8)]
for y in range(8):
    for x in range(8):
        img.pset(x, 120 + y, 0)


def pal_pos(c):
    # ColorPicker sits at (11, 156): 8x8 per swatch, 8 per row.
    return 16 + (c % 8) * 8, 161 + (c // 8) * 8


def cell_pos(cx, cy):
    # CanvasPanel sits at (11, 16): 8 px per cell.
    return 16 + cx * 8, 21 + cy * 8


# Group the pixels of each colour into horizontal runs.
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

# Largest area first. The shape appears before the outline, so the drawing
# looks like it is growing rather than being traced.
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

# Hold on the finished sprite for a moment before looping back.
drv.moveto(120, 92, 8)
drv.wait(40)

print("frames:", len(drv.seq))
drv.play(OUT)
print("done")
