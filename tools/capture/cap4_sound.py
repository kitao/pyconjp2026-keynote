"""Slide 26, right: building the collision sound in the sound editor, as a video.

Starting from nothing it
  1. places the notes on the piano roll one at a time,
  2. types the TON / VOL / EFX rows one character at a time, and
  3. plays the result twice.
The story of the interaction is: place the dots, set the parameters, listen.
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
ed.sound_index_var = 0  # The collision sound

snd = pyxel.sounds[0]
notes = list(snd.notes)
tones = list(snd.tones)
volumes = list(snd.volumes)
effects = list(snd.effects)
print("notes:", notes, "tones:", tones, "volumes:", volumes, "effects:", effects)
snd.notes.clear()
snd.tones.clear()
snd.volumes.clear()
snd.effects.clear()


def roll_pos(step, note):
    # PianoRoll sits at (30, 25): 4 px per step, 2 px per semitone, bottom up.
    return 33 + step * 4, 27 + (59 - note) * 2


# Field value -> key to press, in the same order as the key table in
# pyxel.editor.sound_field.
KEYS = {
    "tone": [pyxel.KEY_T, pyxel.KEY_S, pyxel.KEY_P, pyxel.KEY_N],
    "vol": [getattr(pyxel, f"KEY_{i}") for i in range(8)],
    "efx": [pyxel.KEY_N, pyxel.KEY_S, pyxel.KEY_V, pyxel.KEY_F, pyxel.KEY_H, pyxel.KEY_Q],
}

drv.moveto(120, 100, 1)
drv.wait(12)

# 1. Place the notes.
for i, n in enumerate(notes):
    x, y = roll_pos(i, n)
    drv.moveto(x, y, 12 if i == 0 else 9)
    drv.wait(2)
    drv.click(pre=0, post=6)

# 2. With the notes placed, the pointer steps just below and right of the last
#    note, clear of its red marker; a larger move would pull the eye away.
#    From here it is keyboard only: the down key moves focus from the notes to
#    TON, VOL and EFX in turn, and each row is typed one character at a time
#    (dropping into an empty field puts the cursor back at the start).
drv.moveto(56, 106, 7)
drv.wait(8)
for vals, table in ((tones, "tone"), (volumes, "vol"), (effects, "efx")):
    drv.key(pyxel.KEY_DOWN, post=7)
    for v in vals:
        drv.key(KEYS[table][v], post=6)
    drv.wait(3)
drv.wait(8)

# 3. Play with SPACE, as the on-screen help says (PLAY:SPACE); the pointer
#    stays put. Record the frame of each press so the sound can be mixed in
#    later.
plays = []
for _ in range(2):
    plays.append(len(drv.seq) + 1)
    # The sound is 0.30 s. Leave about two seconds of silence so it reads as
    # play, pause, play again.
    drv.key(pyxel.KEY_SPACE, post=72)

drv.wait(22)

print("frames:", len(drv.seq))
print("play frames:", plays)
open("g4_sound_plays.txt", "w").write(",".join(map(str, plays)) + "\n" + str(len(drv.seq)))
drv.play(OUT)

# Verify that the interaction reproduced the original data; play() performs
# the actual clicks and key presses.
assert list(snd.notes) == notes, list(snd.notes)
assert list(snd.tones) == tones, list(snd.tones)
assert list(snd.volumes) == volumes, list(snd.volumes)
assert list(snd.effects) == effects, list(snd.effects)
print("check: the interaction reproduced the original data")

# Export the sound separately so it can be mixed into the video. Its length is
# derived from the sound itself.
_se = pyxel.sounds[0]
_se.save("snd_hit.wav", len(_se.notes) * _se.speed / 120)
print("done")
