"""Build the resource file used by the demo (demo/game/game.pyxres).

It takes the art and sound the demo needs out of the book's sample data and
packs them into a fresh file.
"""

import pyxel

# The astronaut and meteor art comes from the sample data shipped with the book
# "Learn Python with Games" (Gijutsu-Hyohron). That data is not part of this
# repository; point SRC at your own copy.
SRC = "../../../gihyo_pyxel/chapter5/space_rescue.pyxres"
OUT = "../../demo/game/game.pyxres"

pyxel.init(160, 120)
pyxel.load(SRC)

img = pyxel.images[0]

# Move the sample sprites to the positions the slide code reads from.
# The screen has ground on it, so the player is the astronaut rather than the
# spaceship: astronaut (16,0) -> (0,120), meteor (24,0) -> (8,120).
# blt within a single bank panics on the RefCell, so copy pixel by pixel.
def copy(sx, sy, dx, dy, w=8, h=8):
    buf = [[img.pget(sx + i, sy + j) for i in range(w)] for j in range(h)]
    for j in range(h):
        for i in range(w):
            img.pset(dx + i, dy + j, buf[j][i])


copy(16, 0, 0, 120)
copy(24, 0, 8, 120)

# Background 160x120 at (0,0), reading the same as the shapes-only version:
# navy sky (cls 1) and a green ground line at y=112.
img.rect(0, 0, 160, 120, 1)

# Stars. The seed is fixed so a re-run produces the same sky.
pyxel.rseed(7)
for _ in range(38):
    x = pyxel.rndi(0, 159)
    y = pyxel.rndi(0, 104)
    img.pset(x, y, 5 if pyxel.rndi(0, 2) else 6)
for _ in range(9):
    x = pyxel.rndi(0, 159)
    y = pyxel.rndi(0, 100)
    img.pset(x, y, 7)

# Planet surface. Keep the green line of the shapes version as the lit edge.
# No scattered single pixels here: the sky is made of exactly that, so dots on
# the ground read as more stars. Use horizontal bands and craters instead.
# The skyline dips in a few places. An uneven horizon is what makes it read as
# terrain; a ruled band with texture on it just reads as more sky.
# It only ever dips, never rises, so it cannot collide with the player at y=104..111.
top = [112] * 160
for sx, w in ((17, 11), (54, 16), (97, 8), (127, 13)):
    for x in range(sx, min(sx + w, 160)):
        top[x] = 113

for x in range(160):
    y = top[x]
    img.rect(x, y + 1, 1, 119 - y, 5)  # one solid mass
    img.pset(x, y, 3)  # the lit edge, same line as the shapes version

# Cracks. 1px high only. A 2px bar reads as a floating rectangle, not a crack.
for cx, cy, w in ((6, 117, 7), (36, 116, 9), (73, 118, 6), (105, 116, 8), (140, 117, 7)):
    img.rect(cx, cy, w, 1, 1)

# The book sample brings its own sounds along with the art. This game keeps
# exactly one sound effect, so drop them all and reset speed to the editor
# default before writing ours.
for s in pyxel.sounds:
    s.notes.clear()
    s.tones.clear()
    s.volumes.clear()
    s.effects.clear()
    s.speed = 30

# Sound 0: the ship is hit. The only sound effect here -- with 16 meteors, a
# sound on every one that goes past is just noise.
# Noise tone with slide down and a fade at the end. Slide is what makes it read
# as an impact, and it puts TON=N / EFX=SSSF on screen in the editor video.
pyxel.sounds[0].set("g3c3g2c2", "n", "7654", "sssf", 9)

pyxel.save(OUT)
print("saved", OUT)
