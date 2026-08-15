"""Teaser for the PyCon JP 2026 keynote.

A moonlit sea. Waves roll in, fireworks rise, and the water carries their
light. At the end the residents of Cursed Caverns walk the shore to see you
off. Roughly 60 seconds at 30 fps.

Everything is drawn with Pyxel drawing commands; only the residents come from
an image (trailer/cast.png).

    pyxel run trailer/trailer.py      plays it as is
    trailer/make_video.py             mixes the sound and writes an MP4
"""
import os
import sys

import pyxel


# Assets (fonts, residents) are loaded by relative path. After pyxel.init the
# working directory is this file's folder, so Movie must be built after init.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

from telop import Telop, fade, span

W, H = 320, 180
FPS = 30
SEC = FPS
DUR = 60 * SEC

HORIZON = 104                # Horizon line
SHORE = H - 16               # Shore in the foreground
MOONX, MOONY, MOONR = 246, 28, 11

ACT_FW = 12 * SEC            # First firework goes up
ACT_CAMEO = 44 * SEC         # Residents start walking


class Movie:
    # Colour ramps for the stars: gold, silver, red, green and blue, each
    # ordered bright to dark. A star walks right along its ramp as it burns,
    # and once it runs off the end it has burnt out.
    RAMPS = {"gold":  (7, 10, 9, 4, 1),
             "silver": (7, 6, 12, 5, 1),
             "red":   (7, 14, 8, 4, 1),
             "green": (7, 11, 3, 5, 1),
             "blue":  (7, 12, 5, 1, 0)}
    # Shell types (core, middle, outer). Each layer packs stars of a different
    # composition, so the concentric rings differ in colour. A layer is
    # (colour while burning, colour after the change). In a colour-changing
    # star the outer composition burns away and the inner one shows through;
    # stars that do not change carry None.
    SHELLS = ((("gold", None), ("red", None), ("gold", "silver")),
              (("silver", None), ("blue", None), ("silver", "red")),
              (("red", None), ("gold", None), ("green", "gold")),
              (("green", None), ("silver", None), ("gold", "red")),
              (("gold", None), ("green", None), ("red", "silver")),
              (("blue", None), ("silver", None), ("blue", "gold")))
    LIFE = 70            # Frames until a star burns out
    CHANGE = 0.45        # Point in the burn at which a star changes colour
    # Directions the stars fly, laid out as latitude x longitude on a sphere.
    # The z component is depth: stars thrown towards the viewer travel further
    # and read brighter (used by _spark and by the colour step).
    DIRS = []
    for _lat in range(-2, 3):
        _phi = _lat * 30 + ((_lat * 37) % 11) - 5
        _n = 4 + (5 - abs(_lat)) * 2          # Fewer stars near the poles
        for _lon in range(_n):
            # Offset each star rather than spacing them evenly
            _th = _lon * 360 / _n + ((_lon * 53 + _lat * 29) % 17) - 8
            DIRS.append((pyxel.cos(_th) * pyxel.cos(_phi), pyxel.sin(_phi),
                         pyxel.sin(_th) * pyxel.cos(_phi)))

    # The firework is noise only; mixing in a pitched waveform makes it sound
    # synthetic. Playing a very low note directly turns the waveform into
    # audible steps, so it slides down from slightly higher instead. Burst and
    # tail are one sound, played into channel 3 on top of the BGM drum, which
    # pauses for the duration and then resumes.
    BOOM = ("g#0f0f0f0f0f0", "nnnnnn", "764321", "nsffff", 14)  # 104->87 Hz, 0.56 s
    SE_CH = 3
    # Channel levels. make_video.py mixes with the same values.
    CH_GAIN_SE = 0.185
    CH_GAIN_BGM = 0.150
    BGM_PRESET, BGM_TRANSP, BGM_INSTR, BGM_SEED = 3, 0, 3, 0

    def sound_setup(self, bgm=True):
        """Prepare the sounds (41 = firework, 44-47 = one per BGM channel).

        Overall balance is set by the channel gains. The firework plays into
        channel 3, so that channel is set to the firework's level.
        """
        for c in range(4):
            pyxel.channels[c].gain = self.CH_GAIN_BGM
        pyxel.channels[self.SE_CH].gain = self.CH_GAIN_SE
        pyxel.sounds[41].set(*self.BOOM)
        self.bgm = bgm
        if bgm:
            for i, mml in enumerate(pyxel.gen_bgm(self.BGM_PRESET, self.BGM_TRANSP,
                                                  self.BGM_INSTR, self.BGM_SEED)):
                pyxel.sounds[44 + i].mml(mml)
            pyxel.musics[0].set([44], [45], [46], [47])
            pyxel.playm(0, loop=True)

    def __init__(self, base="."):
        self.base = base
        self.telop = Telop(self.base)
        self.t = 0
        pyxel.rseed(20260822)
        self.stars = [(pyxel.rndi(0, W - 1), pyxel.rndi(2, HORIZON - 12),
                       pyxel.rndi(0, 119)) for _ in range(70)]
        # Clouds: (speed, phase, height, width, thickness)
        self.clouds = ((0.10, 30, 16, 46, 7), (0.07, 210, 38, 34, 6),
                       (0.14, 130, 58, 28, 5), (0.06, 300, 80, 52, 8))
        # Firework score: (launch second, count, frames between launches).
        # A burst stays visible for 2.3 s, so the gap decides how many bloom at
        # once. Even inside a cluster the gap stays above 0.7 s; tighter than
        # that reads as rapid fire. The score starts sparse, thickens
        # gradually, peaks with the cluster at 45-47 s and then thins out, so
        # the closing line ("See you in Hiroshima!" from 48 s) is read against
        # a quietening sky. The last launch is at 54.4 s and fades with the
        # blackout from 57 s.
        plan = ((12.0, 1, 0), (14.6, 1, 0), (17.0, 2, 26), (20.4, 1, 0), (22.6, 2, 24),
                (25.6, 2, 22), (28.4, 1, 0), (30.4, 3, 22), (34.0, 1, 0), (36.0, 3, 22),
                (39.4, 2, 26), (42.8, 1, 0), (44.8, 3, 22),
                (49.2, 2, 28), (52.8, 1, 0), (54.4, 1, 0))
        # Launch positions span the full width. Stepping by the golden ratio
        # keeps consecutive bursts far apart while still covering the width
        # evenly over the whole run.
        FW_L, FW_R = 60, W - 60
        self.shots = []
        k = 0
        for sec, n, gap in plan:
            t0 = int(sec * SEC)
            for i in range(n):
                fx = FW_L + int(((k * 0.6180339887) % 1.0) * (FW_R - FW_L))
                self.shots.append((t0 + i * gap, fx, (k * 5) % 6))
                k += 1
        cast = os.path.join(self.base, "cast.png")
        self.has_cast = os.path.exists(cast)
        if self.has_cast:
            pyxel.images[1].load(0, 0, cast)

    # -- Sky (furthest back) ------------------------------------------------
    def sky(self):
        """Glow along the horizon, plus the stars. Moon, clouds and fireworks
        are drawn over this."""
        t = self.t
        pyxel.cls(0)
        # Raise the density one row at a time so the glow has no visible edge.
        GLOW = 30
        for j in range(GLOW):
            f = (j / GLOW) ** 2.2
            pyxel.dither(f)
            pyxel.rect(0, HORIZON - GLOW + j, W, 1, 1)
        for j in range(10):
            pyxel.dither((j / 10) ** 2)
            pyxel.rect(0, HORIZON - 10 + j, W, 1, 5)
        pyxel.dither(1.0)
        for x, y, ph in self.stars:
            k = ((t + ph) // 30) % 5
            pyxel.pset(x, y, 7 if k == 1 else (12 if k == 3 else 6))

    # -- Clouds ---------------------------------------------------------------
    def cloud(self):
        """Clouds sit in front of the stars and the moon, behind the fireworks."""
        t = self.t
        for sp, ph, cy, cw, ch in self.clouds:
            cx = int(t * sp + ph) % (W + cw * 2) - cw
            # Thin drifting streaks: dense in the middle, thinning at the ends.
            for j in range(ch):
                f = 1 - abs(j - (ch - 1) / 2) / max(1, (ch - 1) / 2)
                x0 = cx + int(cw * 0.10 * j)
                bw = int(cw * (0.35 + 0.65 * f))
                for x in range(x0, x0 + bw):
                    e = min(x - x0, x0 + bw - x) / max(1, bw * 0.35)
                    if e < 1 and (x * 3 + j * 7) % 5 < 3:
                        continue                      # Fray the edges
                    pyxel.pset(x, cy + j, 1 if (j + x) % 7 else 5)

    # -- Moon -----------------------------------------------------------------
    def moon(self):
        """The moon is far behind the fireworks, so it is drawn first and a
        burst passing in front of it hides it."""
        # Halo: dithered rings that thin out as they go.
        for j, (r, col) in enumerate(((MOONR + 7, 1), (MOONR + 5, 1), (MOONR + 4, 5),
                                      (MOONR + 3, 5), (MOONR + 2, 5))):
            pyxel.dither(0.22 + j * 0.18)
            pyxel.circ(MOONX, MOONY, r, col)
        pyxel.dither(1.0)
        pyxel.circ(MOONX, MOONY, MOONR, 10)
        pyxel.circ(MOONX - 3, MOONY - 3, MOONR - 6, 15)
        for dx, dy, r in ((4, -3, 2), (-3, 4, 2), (6, 4, 1), (-6, -2, 1)):
            pyxel.circ(MOONX + dx, MOONY + dy, r, 9)

    # -- Sea ------------------------------------------------------------------
    def sea(self):
        t = self.t
        pyxel.rect(0, HORIZON, W, H - HORIZON, 1)
        depth = SHORE - HORIZON
        for i in range(depth):
            y = HORIZON + i
            d = i / depth
            hsh = (y * 2654435761) & 0xFFFFF
            sway = int(round((1 + d * 2) * pyxel.sin(t * 0.7 + i * 11)))
            gap = 10 + int(d * 16)
            ln = 1 + int(d * 3)
            x = -(hsh % gap)
            while x < W:
                jitter = ((hsh >> (x % 13)) & 3) - 1
                bright = ((hsh >> (x % 7)) & 7) == 0 and d > 0.3
                px0 = x + sway + jitter
                pyxel.line(px0, y, px0 + ln + (1 if bright else 0), y,
                           12 if bright else 5)
                x += gap + ((hsh >> (x % 11)) & 7)
        # Moon path on the water
        for i in range(0, depth, 2):
            y = HORIZON + i
            d = i / depth
            hw = 2 + int(d * 10)
            sx = MOONX + int(3 * pyxel.sin(t * 0.8 + i * 26))
            x = sx - hw
            while x < sx + hw:
                deg = x * 5 + t * 2.4 + i * 51
                ln = 1 + int(pyxel.sin(deg) > 0.2) + int(d * 2)
                if pyxel.sin(deg * 1.7 + i * 13) > -0.35:
                    c = 7 if abs(x - sx) <= 1 and d > 0.3 else (15 if d > 0.5 else 10)
                    pyxel.line(x, y, x + ln, y, c)
                x += ln + 2
        # Shore
        pyxel.rect(0, SHORE, W, H - SHORE, 0)
        for x in range(0, W, 3):
            if (x // 3) % 4:
                pyxel.pset(x, SHORE, 1)

    # -- Fireworks --------------------------------------------------------------
    @staticmethod
    def _spark(fx, top, dx, dy, dz, k, reach, speed=1.0):
        """A spark k frames after the burst: drag slows it, gravity keeps pulling."""
        tau = 16.0                                  # Frames for the speed to fall to 1/e
        r = reach * speed * (1 - 2.718281828 ** (-k / tau)) * (1 + 0.16 * dz)
        drop = 0.5 * 0.02 * k * k                   # Fall grows with the square of time
        return fx + r * dx, top + r * dy * 0.9 + drop

    def fireworks(self):
        for t0, fx, col in self.shots:
            ft = self.t - t0
            if ft < 0:
                continue
            # Burst height, chosen so the upward sparks stay on screen.
            top = 46 + (fx % 4) * 6
            shell = self.SHELLS[col % len(self.SHELLS)]
            if ft == 24:                                # Burst sound
                pyxel.play(self.SE_CH, 41, resume=True)
            if ft < 24:                                 # Rising trail
                for j, c in enumerate((7, 10, 9, 4)):
                    k = ft - j * 2
                    if k >= 0:
                        y = HORIZON - (HORIZON - top) * k / 24
                        pyxel.pset(fx, int(y), c)
                continue
            bt = ft - 24
            if bt > self.LIFE:
                continue
            burn = bt / self.LIFE            # How far the star has burnt (0 = burst, 1 = out)
            TAIL, REACH = 9, 54              # Frames of tail, and how far a star reaches
            # Stars are packed in layers inside the shell. Every star in a
            # layer flies at the same speed, so each layer forms a ring of its
            # own diameter and its own colour.
            for layer, (lspeed, (c1, c2)) in enumerate(zip((0.58, 0.79, 1.0), shell)):
                # In a changing star the inner colour shows once the outer
                # composition has burnt away.
                changed = c2 and burn > self.CHANGE
                ramp = self.RAMPS[c2 if changed else c1]
                # As it burns it cools and walks its ramp from bright to dark.
                # A star that has changed starts again from the bright end.
                lit = (burn - self.CHANGE) / (1 - self.CHANGE) if changed else burn
                # Past the end of the ramp the star has burnt out and is not drawn.
                base = lit * len(ramp)
                # Rotate per shell and per layer so the rings never line up the same way.
                spin = (fx * 7 + t0 * 13) % 360 + layer * 17
                cs, sn = pyxel.cos(spin), pyxel.sin(spin)
                for n, (dx, dy, dz) in enumerate(self.DIRS):
                    dx, dy = dx * cs - dy * sn, dx * sn + dy * cs
                    prev = None
                    for j in range(TAIL + 1):
                        k = bt - j
                        if k < 3:
                            break
                        p = self._spark(fx, top, dx, dy, dz, k, REACH, lspeed)
                        if prev is not None and p[1] < HORIZON - 2:
                            # base walks towards the dark end over time. The
                            # tail is the ember left behind, so it is darker
                            # still. Each spark is aged slightly differently so
                            # they do not all wink out together.
                            step = (int(base + j * 0.34 + (n % 3) * 0.25)
                                    + (1 if dz < -0.3 else 0))
                            if step < len(ramp):
                                pyxel.line(int(prev[0]), int(prev[1]),
                                           int(p[0]), int(p[1]), ramp[step])
                        prev = p
                    # Late in the burn, thin out the leading points. The
                    # streaks remain, so the burst scatters as it fades.
                    if bt > 40 and (n + bt // 3) % 3:
                        continue
                    if bt < 18 and dz > 0.15:
                        hx, hy = self._spark(fx, top, dx, dy, dz, bt, REACH, lspeed)
                        if hy < HORIZON - 2:
                            pyxel.pset(int(hx), int(hy), 7)
            # Reflection: light of the same width falls straight below the
            # burst and scatters on the waves. It lingers a little after the
            # sparks in the sky have gone.
            REFL = self.LIFE + 16
            if bt < REFL:
                rr = int(REACH * (1 - (1 - min(bt, 30) / 30) ** 2))
                fade = max(0.0, 1 - bt / REFL) ** 1.5
                depth = SHORE - HORIZON
                # The reflection takes the colour of the sparks above, and
                # follows them when they change.
                oc1, oc2 = shell[2]
                oramp = self.RAMPS[oc2 if oc2 and burn > self.CHANGE else oc1]
                for dy in range(0, depth, 2):
                    y = HORIZON + dy
                    d = dy / depth
                    w2 = int(rr * (1 - d * 0.45))
                    if w2 < 2:
                        continue
                    ox = int(round((1 + d * 5) * pyxel.sin(self.t * 1.0 + dy * 26)))
                    # Darker and sparser towards the viewer
                    c = oramp[1 if d < 0.3 else (2 if d < 0.6 else 3)]
                    x = fx - w2 + ox
                    while x < fx + w2 + ox:
                        # The scatter is fixed to the water (derived from x, y);
                        # the sway is carried entirely by the offset ox.
                        h = ((x - ox) * 73856093 ^ y * 19349663) & 0xFFFF
                        if (h & 7) < 6.5 * fade * (1 - d * 0.6):
                            pyxel.line(x, y, x + (h >> 5 & 1), y, c)
                        x += 2 + (h >> 3 & 3)

    # -- Residents seeing you off ----------------------------------------------
    def cameo(self, tt):
        if not self.has_cast:
            return
        y = SHORE - 10
        walk = (self.t // 10) % 2      # Step cycle, matched to the walking speed
        for i, u in enumerate((0, 20, 40, 60, 80)):
            pyxel.blt(int(-16 + tt * 0.66 - i * 20), y, 1, u + (10 if walk else 0), 0,
                      10, 10, 6)

    # -- Captions ----------------------------------------------------------------
    MAIN_Y, SUB_Y = 34, 56
    # The title card is bilingual: two Japanese lines and two English lines,
    # each pair set close together.
    T1_Y, T2_Y, T3_Y, T4_Y = 14, 32, 56, 72

    def credits(self):
        T = self.telop
        cx = W // 2
        t = self.t
        if (k := span(t, 2 * SEC, 13 * SEC)) is not None:
            T.reveal(cx, self.MAIN_Y, "PyCon JP 2026", k, speed=4)
        if (k := span(t, 6 * SEC, 13 * SEC)) is not None:
            T.reveal(cx, self.SUB_Y, "K E Y N O T E", k, large=False, speed=3)
        if (k := span(t, 15 * SEC, 25 * SEC)) is not None:
            T.reveal(cx, self.T1_Y, "Pyxelで、プログラミングを遊ぼう！", k, speed=3)
        if (k := span(t, 17 * SEC, 25 * SEC)) is not None:
            T.reveal(cx, self.T2_Y, "―「楽しく作る」をデザインする", k, large=False, speed=3)
        if (k := span(t, 19 * SEC, 25 * SEC)) is not None:
            T.reveal(cx, self.T3_Y, "Let’s Play Programming with Pyxel!", k, large=False,
                     speed=2)
        if (k := span(t, 20 * SEC + 15, 25 * SEC)) is not None:
            T.reveal(cx, self.T4_Y, "― Designing the Fun of Making", k, large=False,
                     speed=2)
        if (k := span(t, 30 * SEC, 37 * SEC)) is not None:
            T.reveal(cx, self.MAIN_Y, "北尾 崇 / Takashi Kitao", k, speed=3)
        if (k := span(t, 31 * SEC + 15, 37 * SEC)) is not None:
            T.reveal(cx, self.SUB_Y, "Pyxel作者 / Creator of Pyxel", k, large=False, speed=3)
        if (k := span(t, 39 * SEC, 46 * SEC)) is not None:
            T.reveal(cx, self.MAIN_Y, "8.22 SAT 17:05", k, speed=4)
        if (k := span(t, 40 * SEC + 15, 46 * SEC)) is not None:
            T.reveal(cx, self.SUB_Y, "HIROSHIMA ― 広島国際会議場", k, large=False, speed=3)
        if (k := span(t, 48 * SEC, 60 * SEC)) is not None:
            T.reveal(cx, self.MAIN_Y, "See you in Hiroshima!", k, speed=4)
        if (k := span(t, 50 * SEC, 60 * SEC)) is not None:
            T.reveal(cx, self.SUB_Y, "#pyconjp2026", k, large=False, speed=3)

    # -- One frame -----------------------------------------------------------
    def draw(self):
        t = self.t
        # Back to front: stars -> moon -> clouds -> sea -> fireworks
        self.sky()
        self.moon()
        self.cloud()
        self.sea()
        if t >= ACT_FW:
            self.fireworks()
        if t >= ACT_CAMEO:
            self.cameo(t - ACT_CAMEO)
        self.credits()
        if t < 2 * SEC:
            fade(1 - t / (2 * SEC))
        if t > DUR - 3 * SEC:
            fade((t - (DUR - 3 * SEC)) / (2 * SEC))

    def update(self):
        self.t += 1


def main():
    pyxel.init(W, H, title="PyCon JP 2026 KEYNOTE teaser", display_scale=4)
    movie = Movie()
    movie.sound_setup()

    def update():
        movie.update()
        if movie.t >= DUR:
            pyxel.quit()

    pyxel.run(update, movie.draw)


if __name__ == "__main__":
    main()
