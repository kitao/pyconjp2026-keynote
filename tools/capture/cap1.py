"""Slide 23, step 1 of building the game: draw shapes. Captures a still.

The code is exactly as it appears on the slide; only show() is replaced with
flip() + screenshot() so the frame can be captured.
"""

import pyxel

OUT = "g1_shapes"

pyxel.init(160, 120, headless=True, capture_scale=4)

pyxel.cls(1)
pyxel.line(0, 112, 159, 112, 3)
pyxel.rect(76, 104, 8, 8, 10)
pyxel.rect(40, 20, 8, 8, 8)

pyxel.flip()
pyxel.screenshot(OUT, scale=4)
print("done")
