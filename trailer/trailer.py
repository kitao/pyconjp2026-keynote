"""PyCon JP 2026 基調講演の予告動画。

月あかりの海。波が寄せ、花火が上がり、水面がその光を映す。
最後に Cursed Caverns の住人たちが浜を歩いて見送る。約60秒・30fps。

絵はすべて Pyxel の描画命令で描く（住人だけ trailer/cast.png）。

  pyxel run trailer/trailer.py     でそのまま再生できる
  動画化は trailer/make_video.py（音を重ねて MP4 にする）
"""
import os
import sys

import pyxel


# 素材（フォント・住人）は相対パスで読む。pyxel.init のあとはカレントが
# このファイルの場所になるので、Movie を作るのは必ず init のあと
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

from telop import Telop, fade, span

W, H = 320, 180
FPS = 30
SEC = FPS
DUR = 60 * SEC

HORIZON = 104                # 水平線
SHORE = H - 16               # 手前の浜
MOONX, MOONY, MOONR = 246, 28, 11

ACT_FW = 12 * SEC            # 花火が上がりはじめる
ACT_CAMEO = 44 * SEC         # 住人が歩き出す


class Movie:
    # 星の色の道。金・銀・紅・翠・藍の5系統を、明るい側から暗い側へ並べてある。
    # 燃え進むほどこの道を右へたどり、道を出はずれたら燃えつき
    RAMPS = {"gold":  (7, 10, 9, 4, 1),
             "silver": (7, 6, 12, 5, 1),
             "red":   (7, 14, 8, 4, 1),
             "green": (7, 11, 3, 5, 1),
             "blue":  (7, 12, 5, 1, 0)}
    # 玉の型（芯・中花・外花）。層ごとに星の組成が違うので、同心円の輪ごとに色が違う。
    # 各層は（燃えはじめの色, 変色したあとの色）。変色星は外側の組成が燃え尽きると
    # 内側の組成が現れて色が変わる。変わらない星は None
    SHELLS = ((("gold", None), ("red", None), ("gold", "silver")),
              (("silver", None), ("blue", None), ("silver", "red")),
              (("red", None), ("gold", None), ("green", "gold")),
              (("green", None), ("silver", None), ("gold", "red")),
              (("gold", None), ("green", None), ("red", "silver")),
              (("blue", None), ("silver", None), ("blue", "gold")))
    LIFE = 70            # 星が燃えつきるまでのコマ数
    CHANGE = 0.45        # 変色星が色を変える時点（燃焼のこの割合で切り替わる）
    # 星が飛ぶ方向。球の緯度×経度で作る。z成分は奥行きで、手前に飛ぶ星ほど
    # 遠くまで届いて明るく見える（_spark と描画の色で使う）
    DIRS = []
    for _lat in range(-2, 3):
        _phi = _lat * 30 + ((_lat * 37) % 11) - 5
        _n = 4 + (5 - abs(_lat)) * 2          # 緯度ごとに数を変える
        for _lon in range(_n):
            # 等間隔にせず、粒ごとに角度をずらす
            _th = _lon * 360 / _n + ((_lon * 53 + _lat * 29) % 17) - 8
            DIRS.append((pyxel.cos(_th) * pyxel.cos(_phi), pyxel.sin(_phi),
                         pyxel.sin(_th) * pyxel.cos(_phi)))

    # 花火の音はノイズだけで作る。音程のある波形を混ぜると人工的な音になる。
    # 低い音をそのまま鳴らすと波形が階段になって耳障りなので、少し高いところから
    # 滑り落として低さを出す。破裂から残響までを1つの音にして、チャンネル3へ
    # 割り込ませる（BGMのドラムを一瞬止めて、鳴り終わったら戻す）
    BOOM = ("g#0f0f0f0f0f0", "nnnnnn", "764321", "nsffff", 14)  # 104→87Hz・0.56秒
    SE_CH = 3
    # チャンネルの音量。動画側（make_video.py）もこの値で混ぜる
    CH_GAIN_SE = 0.185
    CH_GAIN_BGM = 0.150
    BGM_PRESET, BGM_TRANSP, BGM_INSTR, BGM_SEED = 3, 0, 3, 0

    def sound_setup(self, bgm=True):
        """音を用意する（41=花火、44〜47=BGMの各チャンネル）

        全体の大小はチャンネルの gain で決める。花火はチャンネル3に割り込ませるので、
        そのチャンネルの gain は花火に合わせる
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
        # 雲（速さ, 位相, 高さ, 幅, 厚み）
        self.clouds = ((0.10, 30, 16, 46, 7), (0.07, 210, 38, 34, 6),
                       (0.14, 130, 58, 28, 5), (0.06, 300, 80, 52, 8))
        # 花火の台本。(打ち上げの秒, 発数, 発と発の間のコマ)
        # 開いた玉は2.3秒見えるので、同時に何発咲くかは間隔で決まる。
        # 束の中でも0.7秒以上は空ける（それより詰めると連写に見える）。
        # ぽつりと始めて少しずつ厚くし、45〜47秒の束をひと山にして、そのあとは引く。
        # 締めの「See you in Hiroshima!」（48秒〜）は静まりかけた空で読ませる。
        # 最後の打ち上げは54.4秒。暗転（57秒〜）とともに消える
        plan = ((12.0, 1, 0), (14.6, 1, 0), (17.0, 2, 26), (20.4, 1, 0), (22.6, 2, 24),
                (25.6, 2, 22), (28.4, 1, 0), (30.4, 3, 22), (34.0, 1, 0), (36.0, 3, 22),
                (39.4, 2, 26), (42.8, 1, 0), (44.8, 3, 22),
                (49.2, 2, 28), (52.8, 1, 0), (54.4, 1, 0))
        # 上げる位置は画面の全幅。黄金比で送ると、続けて上がる玉は必ず離れた
        # 場所に出て、全体としては左右へ均等に行き渡る（発数も位置の空きもそろう）
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

    # ── 空（いちばん奥）────────────────────
    def sky(self):
        """水平線際の明るさと星。この上に月・雲・花火が重なる"""
        t = self.t
        pyxel.cls(0)
        # 水平線際の明るさ。1行ずつ濃度を上げて、帯の切れ目を作らない
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

    # ── 雲 ──────────────────────────────
    def cloud(self):
        """雲は星より手前、月より手前、花火より奥"""
        t = self.t
        for sp, ph, cy, cw, ch in self.clouds:
            cx = int(t * sp + ph) % (W + cw * 2) - cw
            # 細くたなびく筋。真ん中が濃く、端へ向かって薄れて消える
            for j in range(ch):
                f = 1 - abs(j - (ch - 1) / 2) / max(1, (ch - 1) / 2)
                x0 = cx + int(cw * 0.10 * j)
                bw = int(cw * (0.35 + 0.65 * f))
                for x in range(x0, x0 + bw):
                    e = min(x - x0, x0 + bw - x) / max(1, bw * 0.35)
                    if e < 1 and (x * 3 + j * 7) % 5 < 3:
                        continue                      # 端はほつれさせる
                    pyxel.pset(x, cy + j, 1 if (j + x) % 7 else 5)

    # ── 月 ──────────────────────────────
    def moon(self):
        """月は花火よりずっと遠い。花火より先に描いて、玉が横切れば隠れる"""
        # 暈は外へ向かって薄くなるようディザで重ねる
        for j, (r, col) in enumerate(((MOONR + 7, 1), (MOONR + 5, 1), (MOONR + 4, 5),
                                      (MOONR + 3, 5), (MOONR + 2, 5))):
            pyxel.dither(0.22 + j * 0.18)
            pyxel.circ(MOONX, MOONY, r, col)
        pyxel.dither(1.0)
        pyxel.circ(MOONX, MOONY, MOONR, 10)
        pyxel.circ(MOONX - 3, MOONY - 3, MOONR - 6, 15)
        for dx, dy, r in ((4, -3, 2), (-3, 4, 2), (6, 4, 1), (-6, -2, 1)):
            pyxel.circ(MOONX + dx, MOONY + dy, r, 9)

    # ── 海 ──────────────────────────────
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
        # 月の道
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
        # 浜
        pyxel.rect(0, SHORE, W, H - SHORE, 0)
        for x in range(0, W, 3):
            if (x // 3) % 4:
                pyxel.pset(x, SHORE, 1)

    # ── 花火 ─────────────────────────────
    @staticmethod
    def _spark(fx, top, dx, dy, dz, k, reach, speed=1.0):
        """開いてからkコマ後の火花。抵抗でゆっくり減速し、重力が絶えず効く"""
        tau = 16.0                                  # 速度が1/eになるまでのコマ数
        r = reach * speed * (1 - 2.718281828 ** (-k / tau)) * (1 + 0.16 * dz)
        drop = 0.5 * 0.02 * k * k                   # 落下は時間の2乗で効く
        return fx + r * dx, top + r * dy * 0.9 + drop

    def fireworks(self):
        for t0, fx, col in self.shots:
            ft = self.t - t0
            if ft < 0:
                continue
            # 開く高さ。上へ伸びる火花が画面の外で切れないところに置く
            top = 46 + (fx % 4) * 6
            shell = self.SHELLS[col % len(self.SHELLS)]
            if ft == 24:                                # 開いた音
                pyxel.play(self.SE_CH, 41, resume=True)
            if ft < 24:                                 # 打ち上げの尾
                for j, c in enumerate((7, 10, 9, 4)):
                    k = ft - j * 2
                    if k >= 0:
                        y = HORIZON - (HORIZON - top) * k / 24
                        pyxel.pset(fx, int(y), c)
                continue
            bt = ft - 24
            if bt > self.LIFE:
                continue
            burn = bt / self.LIFE            # 星が燃え進んだ割合（0=開花 1=燃えつき）
            TAIL, REACH = 9, 54              # 尾を描くコマ数と、星が届く距離
            # 星は玉の中で層に分けて詰められている。層ごとに同じ速さで飛ぶので、
            # 同じ直径の輪ができ、その輪ごとに色が違う
            for layer, (lspeed, (c1, c2)) in enumerate(zip((0.58, 0.79, 1.0), shell)):
                # 変色星は、外側の組成が燃え尽きたところで内側の色が現れる
                changed = c2 and burn > self.CHANGE
                ramp = self.RAMPS[c2 if changed else c1]
                # 燃え進むほど温度が下がり、色の道を明→暗へたどって消える。
                # 変色した星は、変わった直後にまた明るいところから始まる
                lit = (burn - self.CHANGE) / (1 - self.CHANGE) if changed else burn
                # 色の道を出はずれたら、その星はもう燃え尽きている（描かない）
                base = lit * len(ramp)
                # 玉ごと・層ごとに向きを回して、いつも同じ角度に並ばないようにする
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
                            # 星の色（base）が時間とともに暗い側へ動く。尾は星が
                            # 通ったあとの燃えかすなので、そのぶんさらに暗い。
                            # 粒ごとに寿命を少しずらして、消えぎわをばらけさせる
                            step = (int(base + j * 0.34 + (n % 3) * 0.25)
                                    + (1 if dz < -0.3 else 0))
                            if step < len(ramp):
                                pyxel.line(int(prev[0]), int(prev[1]),
                                           int(p[0]), int(p[1]), ramp[step])
                        prev = p
                    # 後半は先端の点を間引く。数が減っても筋は残るので、
                    # ばらけながら薄くなっていくように見える
                    if bt > 40 and (n + bt // 3) % 3:
                        continue
                    if bt < 18 and dz > 0.15:
                        hx, hy = self._spark(fx, top, dx, dy, dz, bt, REACH, lspeed)
                        if hy < HORIZON - 2:
                            pyxel.pset(int(hx), int(hy), 7)
            # 水面への映り。玉の真下に、玉と同じ幅の光が落ちて波に散る。
            # 空の火花が消えたあとも水面の光は少し残ってから引く
            REFL = self.LIFE + 16
            if bt < REFL:
                rr = int(REACH * (1 - (1 - min(bt, 30) / 30) ** 2))
                fade = max(0.0, 1 - bt / REFL) ** 1.5
                depth = SHORE - HORIZON
                # 映るのは空の火花と同じ色。星が変色すれば水面の色も変わる
                oc1, oc2 = shell[2]
                oramp = self.RAMPS[oc2 if oc2 and burn > self.CHANGE else oc1]
                for dy in range(0, depth, 2):
                    y = HORIZON + dy
                    d = dy / depth
                    w2 = int(rr * (1 - d * 0.45))
                    if w2 < 2:
                        continue
                    ox = int(round((1 + d * 5) * pyxel.sin(self.t * 1.0 + dy * 26)))
                    # 手前へ行くほど暗く、まばらになる
                    c = oramp[1 if d < 0.3 else (2 if d < 0.6 else 3)]
                    x = fx - w2 + ox
                    while x < fx + w2 + ox:
                        # 散り方は水面に固定（x,yから作る）。揺れは横ずれ（ox）だけで表す
                        h = ((x - ox) * 73856093 ^ y * 19349663) & 0xFFFF
                        if (h & 7) < 6.5 * fade * (1 - d * 0.6):
                            pyxel.line(x, y, x + (h >> 5 & 1), y, c)
                        x += 2 + (h >> 3 & 3)

    # ── 住人の見送り ────────────────────────
    def cameo(self, tt):
        if not self.has_cast:
            return
        y = SHORE - 10
        walk = (self.t // 10) % 2      # 足の運びも歩く速さに合わせる
        for i, u in enumerate((0, 20, 40, 60, 80)):
            pyxel.blt(int(-16 + tt * 0.66 - i * 20), y, 1, u + (10 if walk else 0), 0,
                      10, 10, 6)

    # ── クレジット ─────────────────────────
    MAIN_Y, SUB_Y = 34, 56
    # タイトル画面は日英2段。日本語の2行・英語の2行を、それぞれ近づけて組む
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

    # ── 1コマ ────────────────────────────
    def draw(self):
        t = self.t
        # 奥から手前へ。星 → 月 → 雲 → 海 → 花火
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
