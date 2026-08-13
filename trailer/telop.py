"""予告動画のテロップ部品。

出し方は「1文字ずつ、暗い色から明るい色へ起き上がる」。
どんな背景でも読めるよう、字は黒で縁取り、下に影を落とす。
"""
import os

import pyxel

# 文字が生まれてから落ち着くまでの色の道。暗→明で「じわっと」出る。
# 夜空の上では暗い色（1）がほとんど見えないので、中間の青を挟んで段を増やす
RAMP = (1, 5, 12, 6, 7)
RAMP_STEP = 2    # 1段あたりのコマ数。5段×2コマで、1文字が落ち着くまで10コマ
KEY = 3          # 下書きの抜き色。テロップの色域（0,1,5,6,7,12）と重ならない
# 縁取りと影の置き方。どんな背景でも字が読めるように、黒で囲って下に落とす
OUTLINE = ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0),
           (-1, 1), (0, 1), (1, 1), (0, 2), (1, 2))


class Telop:
    def __init__(self, base="."):
        self.big = pyxel.Font(os.path.join(base, "umplus_j12r.bdf"))    # 見出し・タイトル
        self.small = pyxel.Font(os.path.join(base, "umplus_j10r.bdf"))  # 添えの英文・補足
        self.buf = pyxel.Image(360, 20)                 # 1行ぶんの下書き
        self._center = {}                               # 行ごとの中央位置（測り直さない）

    def _draw_line(self, s, t, font, speed):
        """下書きに1行を描く。t コマ目の姿。戻り値は（幅, 全文が定着したか）"""
        self.buf.rect(0, 0, self.buf.width, self.buf.height, KEY)
        done = True
        cx = 3
        for i, ch in enumerate(s):
            age = (t - i * speed) if t is not None else 10 ** 6
            if age < 0:                                 # まだ出ていない字
                done = False
            else:
                stage = min(age // RAMP_STEP, len(RAMP) - 1)
                if stage < len(RAMP) - 1:
                    done = False
                for dx, dy in OUTLINE:                  # 縁取りと影
                    self.buf.text(cx + dx, 3 + dy, ch, 0, font)
                self.buf.text(cx, 3, ch, RAMP[stage], font)
            cx += font.text_width(ch)
        return cx + 4, done

    def _ink_center(self, bw):
        """下書きの中で実際に色が置かれた範囲の、中央の位置"""
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
        """t コマ目の姿を描く。x は行の中央、y は上端

        中央は「全文を描いたときの左右端」で決める。1文字ずつ出るあいだ、
        行がずれないようにするため
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
    """画面全体を黒へ落とす。alpha 0=素通し 1=真っ黒。レトロらしくディザで落とす"""
    if alpha <= 0:
        return
    pyxel.dither(min(alpha, 1.0))
    pyxel.rect(0, 0, pyxel.width, pyxel.height, 0)
    pyxel.dither(1.0)


def span(t, t0, t1):
    """t が [t0, t1) にあるときだけ、その区間内の経過コマを返す（外なら None）"""
    return t - t0 if t0 <= t < t1 else None
