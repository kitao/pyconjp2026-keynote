"""Drives the Pyxel editors frame by frame so a session can be captured.

Pointer position, button state and key presses are injected per frame, and the
editor's own update/draw are called by hand. That is what lets a scripted
sequence be recorded without a person at the keyboard.

The TON / VOL / EFX rows of the sound editor are typed one character at a time
through pyxel.btnp once the field has focus (see sound_field.py), so key
presses have to be injectable on an exact frame.

Used by cap4_image.py and cap4_sound.py.
"""

import pyxel

CURSOR = [
    "11111100",
    "17776100",
    "17761000",
    "17676100",
    "16167610",
    "11016761",
    "00001610",
    "00000100",
]


def draw_cursor(x, y):
    for j, row in enumerate(CURSOR):
        for i, c in enumerate(row):
            if c != "0":
                pyxel.pset(x + i, y + j, int(c))


class Driver:
    def __init__(self, scale, sec):
        self.scale = scale
        self.loop = {}
        self.seq = []  # [(x, y, is_down), ...]
        self.keys = {}  # frame index -> pyxel key
        self.cur = [120, 92]
        self.down = False
        self.prev = False
        self.held = 0
        self.cur_key = None
        self.prev_key = None

        self._init = pyxel.init
        self._run = pyxel.run
        self._btn = pyxel.btn
        self._btnp = pyxel.btnp
        self._btnr = pyxel.btnr

        def init(w, h, **kw):
            kw["headless"] = True
            kw["capture_scale"] = scale
            kw["capture_sec"] = sec
            self._init(w, h, **kw)

        def run(update, draw):
            self.loop["update"] = update
            self.loop["draw"] = draw

        def btn(key):
            if key == pyxel.MOUSE_BUTTON_LEFT:
                return self.down
            if key == self.cur_key:
                return True
            return self._btn(key)

        def btnp(key, hold=0, repeat=0):
            if key == pyxel.MOUSE_BUTTON_LEFT:
                if not self.down:
                    return False
                if not self.prev:
                    return True
                if hold and repeat and self.held >= hold:
                    return (self.held - hold) % repeat == 0
                return False
            if key == self.cur_key and self.prev_key != key:
                return True
            return self._btnp(key, hold=hold, repeat=repeat)

        def btnr(key):
            if key == pyxel.MOUSE_BUTTON_LEFT:
                return self.prev and not self.down
            return self._btnr(key)

        pyxel.init = init
        pyxel.run = run
        pyxel.btn = btn
        pyxel.btnp = btnp
        pyxel.btnr = btnr

    # -- Building the sequence -------------------------------------------------
    def wait(self, n, down=False):
        for _ in range(n):
            self.seq.append((self.cur[0], self.cur[1], down))

    def moveto(self, x, y, n=6, down=False):
        x0, y0 = self.cur
        for i in range(1, n + 1):
            t = i / n
            t = t * t * (3 - 2 * t)
            self.seq.append((round(x0 + (x - x0) * t), round(y0 + (y - y0) * t), down))
        self.cur = [x, y]

    def click(self, pre=1, post=2):
        self.wait(pre, False)
        self.seq.append((self.cur[0], self.cur[1], True))
        self.seq.append((self.cur[0], self.cur[1], True))
        self.wait(post, False)

    def key(self, k, post=5):
        """Press key k once on this frame.

        Repeats of the same key need post >= 1 to be seen as separate presses.
        """
        self.keys[len(self.seq)] = k
        self.wait(1, False)
        self.wait(post, False)

    # -- Playback ----------------------------------------------------------------
    def play(self, out, skip=0):
        for i, (x, y, d) in enumerate(self.seq):
            pyxel.mouse_x = x
            pyxel.mouse_y = y
            self.prev = self.down
            self.down = d
            self.held = self.held + 1 if (d and self.prev) else 0
            self.prev_key = self.cur_key
            self.cur_key = self.keys.get(i)
            self.loop["update"]()
            self.loop["draw"]()
            draw_cursor(x, y)
            pyxel.flip()
            if i == skip:
                pyxel.reset_screencast()
        pyxel.screencast(out, scale=self.scale)
