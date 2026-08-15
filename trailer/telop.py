"""Caption parts for the trailer.

Characters rise one by one, stepping from a dark colour to a bright one.
Each glyph is outlined in black and given a drop shadow so that it stays
readable over any background.
"""
import os

import pyxel

# Colour ramp a glyph walks through as it settles, dark to bright, so it
# fades in rather than popping. Against the night sky the darkest colour (1)
# is nearly invisible, so a mid blue is inserted to give the ramp more steps.
RAMP = (1, 5, 12, 6, 7)
RAMP_STEP = 2    # Frames per step. 5 steps x 2 frames = 10 frames per glyph.
KEY = 3          # Transparent key of the scratch image. Outside the caption
                 # palette (0, 1, 5, 6, 7, 12) so it never collides.
# Outline and shadow offsets: ring the glyph in black and drop it downwards.
OUTLINE = ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0),
           (-1, 1), (0, 1), (1, 1), (0, 2), (1, 2))


class Telop:
    def __init__(self, base="."):
        self.big = pyxel.Font(os.path.join(base, "umplus_j12r.bdf"))    # Headings
        self.small = pyxel.Font(os.path.join(base, "umplus_j10r.bdf"))  # Sub-lines
        self.buf = pyxel.Image(360, 20)                 # Scratch image for one line
        self._center = {}                               # Centre per line, measured once

    def _draw_line(self, s, t, font, speed):
        """Draw one line into the scratch image as of frame t.

        Returns (width, whether every glyph has settled).
        """
        self.buf.rect(0, 0, self.buf.width, self.buf.height, KEY)
        done = True
        cx = 3
        for i, ch in enumerate(s):
            age = (t - i * speed) if t is not None else 10 ** 6
            if age < 0:                                 # Not visible yet
                done = False
            else:
                stage = min(age // RAMP_STEP, len(RAMP) - 1)
                if stage < len(RAMP) - 1:
                    done = False
                for dx, dy in OUTLINE:                  # Outline and shadow
                    self.buf.text(cx + dx, 3 + dy, ch, 0, font)
                self.buf.text(cx, 3, ch, RAMP[stage], font)
            cx += font.text_width(ch)
        return cx + 4, done

    def _ink_center(self, bw):
        """Centre of the range that actually carries ink in the scratch image."""
        lo, hi = None, None
        for x in range(bw):
            for y in range(self.buf.height):
                if self.buf.pget(x, y) != KEY:
                    if lo is None:
                        lo = x
                    hi = x
                    break
        return (bw - 1) // 2 if lo is None else (lo + hi + 1) // 2

    def reveal(self, x, y, s, t, large=True, speed=3):
        """Draw the line as of frame t. x is the centre of the line, y its top.

        The centre is taken from the fully drawn line, so the line does not
        shift sideways while the glyphs are still appearing one by one.
        """
        font = self.big if large else self.small
        key = (s, large, speed)
        if key not in self._center:
            bw, _ = self._draw_line(s, None, font, speed)
            self._center[key] = self._ink_center(bw)
        bw, done = self._draw_line(s, t, font, speed)
        pyxel.blt(x - self._center[key], y, self.buf, 0, 0, bw, self.buf.height, KEY)
        return done


def fade(alpha):
    """Fade the whole screen to black. alpha 0 = clear, 1 = solid.

    Dithered rather than blended, to keep the retro look.
    """
    if alpha <= 0:
        return
    pyxel.dither(min(alpha, 1.0))
    pyxel.rect(0, 0, pyxel.width, pyxel.height, 0)
    pyxel.dither(1.0)


def span(t, t0, t1):
    """Frames elapsed within [t0, t1) when t falls inside it, else None."""
    return t - t0 if t0 <= t < t1 else None
