"""予告（trailer.py）を音付きの MP4 にする。

  python3 trailer/make_video.py     →  trailer/trailer.mp4

Pyxel 入りの Python で実行する（tools/requirements.txt）。ffmpeg も使う。
320x180 で録り、最近傍の4倍で 1280x720 にする（ドットの角を保つ）。
音は BGM を敷いたうえに、花火の効果音をコマ番号から計算した時刻へ重ねる。
"""
import array
import os
import subprocess
import sys
import wave

import pyxel

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)

FPS = 30
DUR_SEC = 60
# 画面の録りだめ（capture_sec）の上限が60秒なので、その中に収まるコマ数で止める
FRAMES = DUR_SEC * FPS - 2
OUT_MP4 = os.path.join(HERE, "trailer.mp4")

pyxel.init(320, 180, headless=True, capture_scale=1, capture_sec=60)

import trailer as mod  # noqa: E402

movie = mod.Movie()
movie.sound_setup()
# 花火の音と、BGM（gen_bgm の4チャンネルぶん）を書き出す
pyxel.sounds[41].save("tr_se.wav", pyxel.sounds[41].total_sec())
BGM_LOOP = pyxel.sounds[44].total_sec()
for i in range(4):
    pyxel.sounds[44 + i].save(f"tr_bgm{i}.wav", BGM_LOOP)


def gif_to_frames(gif, outdir):
    """GIF を1コマずつ PNG にする。GIF のコマ間隔は1/100秒刻みで30fpsを表せず、
    そのまま渡すと時間がずれるので、コマを取り出して ffmpeg に fps を指定させる"""
    from PIL import Image

    os.makedirs(outdir, exist_ok=True)
    for f in os.listdir(outdir):
        os.remove(os.path.join(outdir, f))
    im = Image.open(gif)
    n = 0
    while True:
        im.convert("RGB").save(os.path.join(outdir, f"{n:05d}.png"))
        n += 1
        try:
            im.seek(im.tell() + 1)
        except EOFError:
            return n


# ── 映像 ─────────────────────────────────
pyxel.reset_screencast()
for _ in range(FRAMES):
    movie.update()
    movie.draw()
    pyxel.flip()
pyxel.screencast("tr_take", scale=1)
n = gif_to_frames("tr_take.gif", "fr_trailer")
print("コマ数", n)


def read_wav(path):
    with wave.open(path, "rb") as w:
        return (w.getnchannels(), w.getsampwidth(), w.getframerate(),
                array.array("h", w.readframes(w.getnframes())))


# ── 音。夜の静けさの中に、花火の音だけを置く ──────────
# 標本化周波数は Pyxel が書き出した WAV に合わせる。決め打ちにすると、
# 値がずれたぶんだけ音程と長さが変わってしまう（22050 を 44100 とみなすと
# 1オクターブ高く、長さは半分になる）
ch, sw, rate, _ = read_wav("tr_se.wav")
total = int(n / FPS * rate) * ch
track = array.array("h", bytes(total * 2))
print(f"音は {rate}Hz / {ch}ch / {sw * 8}bit で組み立てる")


# 端をなます長さ。頭は立ち上がりを鈍らせないよう最小限に、尻は継ぎ目の音を消す
FADE_IN = max(1, rate // 1000)                   # 約1ミリ秒
FADE_OUT = max(1, rate // 200)                   # 約5ミリ秒


def mix(src, at_frame, gain):
    """コマ番号の時刻に音を重ねる。端は短くなまして継ぎ目の音を消す"""
    pos = int(at_frame / FPS * rate) * ch
    n_src = len(src)
    for k in range(n_src):
        j = pos + k
        if j >= len(track):
            break
        g = gain
        if k < FADE_IN:
            g *= k / FADE_IN
        elif k > n_src - FADE_OUT:
            g *= max(0.0, (n_src - k) / FADE_OUT)
        v = track[j] + int(src[k] * g)
        track[j] = max(-32768, min(32767, v))


# ── 音。アプリ（pyxel run）と同じ音・同じ間隔・同じ配合にする。
# Sound.save() はチャンネルの gain を反映しないので、ここで同じ値を掛ける ──
se = read_wav("tr_se.wav")[3]
shots = [t0 + 24 for t0, _, _ in movie.shots if t0 + 24 < n]   # 開いたコマで鳴らす

if movie.bgm:
    # BGMを4チャンネルぶん敷く
    bgm = [read_wav(f"tr_bgm{c}.wav")[3] for c in range(4)]
    loop_len = len(bgm[0])
    for c, src in enumerate(bgm):
        gain = (mod.Movie.CH_GAIN_SE if c == mod.Movie.SE_CH
                else mod.Movie.CH_GAIN_BGM)
        for pos in range(0, len(track), loop_len):
            mix(src, pos / rate * FPS, gain)
    # 花火はドラムと同じチャンネルに割り込む。鳴っているあいだドラムは止まり、
    # 鳴り終わると元の位置から戻る（アプリの resume=True と同じ状態にする）
    drum = bgm[mod.Movie.SE_CH]
    for f in shots:
        a = int(f / FPS * rate)
        for j in range(a, min(a + len(se), len(track))):
            track[j] = max(-32768, min(32767,
                           track[j] - int(drum[j % loop_len] * mod.Movie.CH_GAIN_SE)))

for f in shots:
    mix(se, f, mod.Movie.CH_GAIN_SE)
print("効果音を重ねた回数", len(shots), "／ BGM", "あり" if movie.bgm else "なし")

# 配信で聞こえる大きさに、トラック全体を一定倍する（音量つまみと同じ扱い。
# 個々の音の関係は変わらない）
peak = max(abs(v) for v in track) or 1
scale = int(32767 * 0.72) / peak
for i in range(len(track)):
    track[i] = max(-32768, min(32767, int(track[i] * scale)))
print(f"全体を {scale:.2f} 倍（最大 {peak} → {int(peak * scale)}）")

with wave.open("tr_track.wav", "wb") as w:
    w.setnchannels(ch)
    w.setsampwidth(sw)
    w.setframerate(rate)
    w.writeframes(track.tobytes())

# ── 合成。最近傍で1280x720にして、音は最後の2秒でフェードアウト ──────
subprocess.run([
    "ffmpeg", "-y", "-framerate", str(FPS), "-i", "fr_trailer/%05d.png",
    "-i", "tr_track.wav",
    "-vf", "scale=1280:720:flags=neighbor",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-preset", "slow",
    "-movflags", "+faststart",
    "-c:a", "aac", "-b:a", "160k",
    "-af", f"afade=t=out:st={n / FPS - 2:.1f}:d=2",
    "-shortest", OUT_MP4,
], check=True, capture_output=True)
print("書き出した:", OUT_MP4, round(n / FPS, 1), "秒")
