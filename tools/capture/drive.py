"""撮影用の共通部品。ゲーム本体のコードには手を入れない。

- pilot(): 左右キーの入力を作る。人が操作しているように、決め打ちの往復ではなく
  「危ない隕石から離れる／危なくなければ真ん中へ戻る」を数フレームおきに判断する
- Rec(): 頭の何フレームかを捨ててから録る。1コマ目から録ると、
  隕石が等間隔で降ってくる「開始直後の並び」がループのたびに出て不自然になる
"""

import pyxel

THINK_EVERY = 5  # 考え直す間隔。数コマおきに判断させると、左右に小刻みに震える
LOOKAHEAD = 45  # これから何コマ先までの隕石を見るか（人は画面の上まで見ている）
SAFE = 22  # この幅だけ空いていれば、そこに居座る
MOVE_COST = 0.30  # 遠くへ行くほど損。人はわざわざ画面の端まで走らない
MIN_MOVE = 6  # これ未満しか変わらないなら動かない。1〜2コマの小突きが消える
DEADZONE = 3  # 目標に着いたら止まる。0にすると1pxを行き来して止まらない
PLAYER_Y = 104


class Pilot:
    """人の操作に見せるための当たり判定回避。

    毎コマ最寄りの隕石から逃げると、隕石が多いときに左右へ震え続けて忙しなく見える。
    人は「安全な場所を選んで動き、着いたら次に危なくなるまで止まっている」ので、
    目標を決める → 着いたら止まる → その場が危なくなったら選び直す、にしている。
    """

    def __init__(self):
        self.target = None
        self.next_think = 0

    def input(self, frame, x, enemies):
        moving = self.target is not None and abs(self.target - x) > DEADZONE
        # 動いている間は考え直さない。人は動かしはじめたら、そこまでは動かす。
        # 毎回考え直すと目標が数pxずつ動いて、1〜2コマの小突きが延々と続く
        if not moving and frame >= self.next_think:
            self.next_think = frame + THINK_EVERY
            if self.target is None or self._clearance(x, enemies) < SAFE:
                t = self._pick(x, enemies)
                # わずかな差のために動かない
                self.target = t if abs(t - x) >= MIN_MOVE else x
        if self.target is None:
            return 0
        d = self.target - x
        if abs(d) <= DEADZONE:
            return 0
        return 1 if d > 0 else -1

    def _clearance(self, cx, enemies):
        """cx に居たとき、これから降ってくる隕石との左右の余裕"""
        clear = 999
        for ex, ey in enemies:
            t = (PLAYER_Y - ey) / 2  # 自機の高さに届くまでのコマ数
            if 0 <= t <= LOOKAHEAD:
                clear = min(clear, abs(ex - cx))
        return clear

    def _pick(self, x, enemies):
        best, best_score = x, -1e9
        for cx in range(0, 153, 4):
            # 余裕は頭打ちにする。そうしないと、今いる場所が十分安全でも
            # わずかに広いだけの場所へ画面の端まで走ってしまう
            score = min(self._clearance(cx, enemies), 44) - abs(cx - x) * MOVE_COST
            if score > best_score:
                best_score, best = score, cx
        return best


class Rec:
    """頭を捨ててから指定コマ数だけ録る"""

    def __init__(self, out, skip, frames, scale):
        self.out = out
        self.skip = skip
        self.frames = frames
        self.scale = scale
        self.n = 0

    def tick(self):
        self.n += 1
        if self.n == self.skip:
            pyxel.reset_screencast()
        return self.n < self.skip + self.frames

    def save(self):
        pyxel.screencast(self.out, scale=self.scale)
