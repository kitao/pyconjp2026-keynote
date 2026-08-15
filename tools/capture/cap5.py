"""Slide 27, step 5: add art and sound. Captures a video with audio.

A GIF would loop and carry no sound, so this becomes an MP4 like slide 26.
Headless Pyxel plays nothing, so the BGM and the effect are exported as
separate WAVs; make_video.py lays down the BGM and mixes the effect in at the
frames where a hit occurred.
"""
import pyxel
from drive import Pilot, Rec

OUT = "g5_done"
SCALE = 4
# A hit ends the game. Recording starts from frame one and holds the stopped
# frame for a second. With this seed the first hit lands on frame 209 (7.0 s);
# recording from the start also means the BGM begins at the top of the loop.
SKIP = 0
FRAMES = 240
FPS = 30
pyxel.init(160, 120, headless=True, capture_scale=SCALE, capture_sec=10)
pyxel.rseed(20260849)
rec = Rec(OUT, skip=SKIP, frames=FRAMES, scale=SCALE)

pilot = Pilot()
game_over = False
TAIL = 30   # Capture only: hold the stopped frame for one second
tail = None
held = 0
hits = []  # Frames to sound the effect on, relative to the recording start
_btn = pyxel.btn


def btn(key):
    if key == pyxel.KEY_LEFT:
        return held < 0
    if key == pyxel.KEY_RIGHT:
        return held > 0
    return _btn(key)


pyxel.btn = btn

# From here on, exactly the code shown on the slide
pyxel.load("../../demo/game/game.pyxres")
pyxel.gen_bgm(7, 0, 3, 0, play=True)
x = 76
enemies = [[pyxel.rndi(0, 152), -i * 16] for i in range(16)]

while True:
    held = pilot.input(rec.n, x, enemies)  # Capture only: stands in for key presses

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
                hits.append(rec.n - SKIP)  # Capture only: where to mix the effect
                tail = TAIL  # Capture only: hold the stopped frame
        pyxel.blt(enemy[0], enemy[1], 0, 8, 120, 8, 8, 0)

    pyxel.blt(x, 104, 0, 0, 120, 8, 8, 0)
    pyxel.flip()
    # End of the slide code
    if not rec.tick():
        break
    if tail is not None:  # Capture only: end after holding the stopped frame
        tail -= 1
        if tail <= 0:
            break

rec.save()

# Export the sound separately so it can be mixed into the video.
# The BGM runs from the very start, so it is exported long enough to cover the
# skipped frames too, and the mixer drops those SKIP frames off the front.
# gen_bgm returns a list of MML strings and does not populate musics, so it is
# called again with the same arguments (same seed, same tune) and the result is
# parked in free slots.
hits = [h for h in hits if h >= 0]
mml_list = pyxel.gen_bgm(7, 0, 3, 0)
for i, mml in enumerate(mml_list):
    pyxel.sounds[16 + i].mml(mml)
pyxel.musics[7].set(*[[16 + i] for i in range(len(mml_list))])
pyxel.musics[7].save("bgm.wav", (SKIP + FRAMES) / FPS + 1)
# Take the length of the effect from the sound itself. Asking for longer than
# it actually is makes it loop to fill the time, which sounds like two hits.
# 4 notes x speed 9 / 120 = 0.30 s
_se = pyxel.sounds[0]
_se.save("snd_hit.wav", len(_se.notes) * _se.speed / 120)
open("g5_done_hits.txt", "w").write(",".join(map(str, hits)) + "\n" + str(SKIP))
print("hit frames:", hits)
print("done")
