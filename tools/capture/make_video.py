"""撮った GIF を MP4 にする。必要なら音も重ねる。

GIF はループ再生になってしまい音も乗らないので、ツールの作成風景は動画で置く。
GIF の 1/100 秒刻みのコマ間隔をそのまま使うと 30fps にならないので、
いったん PNG に展開して、きっちり 30fps で並べ直す。
"""

import array
import os
import subprocess
import sys
import wave

FPS = 30
RATE = 22050  # pyxel の書き出す WAV のサンプリング周波数


def gif_to_frames(gif, outdir):
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
            break
    return n


def build_audio(src_wav, out_wav, total_frames, at_frames, base_wav=None, base_skip=0):
    """total_frames ぶんの音に、指定コマの位置で src_wav を重ねる

    base_wav を渡すと、その base_skip コマめ以降を地の音（BGM）として敷く。
    渡さなければ無音の上に重ねる
    """
    with wave.open(src_wav, "rb") as w:
        ch, sw, rate = w.getnchannels(), w.getsampwidth(), w.getframerate()
        clip = array.array("h", w.readframes(w.getnframes()))
    total = int(total_frames / FPS * rate) * ch
    if base_wav:
        with wave.open(base_wav, "rb") as w:
            base = array.array("h", w.readframes(w.getnframes()))
        off = int(base_skip / FPS * rate) * ch
        buf = base[off : off + total]
        buf.extend([0] * (total - len(buf)))
    else:
        buf = array.array("h", [0] * total)
    # 効果音は1つのチャンネルで鳴るので、まず効果音だけの列を作る。
    # 鳴っている途中でもう一度 play すると鳴り直しになるので、ここは上書き。
    # 足し込むと、連続で当たったときに音が重なって不自然に大きくなる
    se = array.array("h", [0] * total)
    for fr in at_frames:
        off = int(fr / FPS * rate) * ch
        for i in range(min(len(clip), len(se) - off)):
            se[off + i] = clip[i]
    # BGM と効果音は別のチャンネルで同時に鳴るので、ここで足し合わせる。
    # 置き換えにすると、鳴っているあいだ BGM が消える
    for i in range(total):
        if se[i]:
            buf[i] = max(-32768, min(32767, buf[i] + se[i]))
    with wave.open(out_wav, "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(sw)
        w.setframerate(rate)
        w.writeframes(buf.tobytes())


def encode(frames_dir, out_mp4, audio=None):
    cmd = ["ffmpeg", "-y", "-framerate", str(FPS), "-i", f"{frames_dir}/%05d.png"]
    if audio:
        cmd += ["-i", audio]
    cmd += [
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16",
        "-preset", "slow", "-movflags", "+faststart",
    ]
    if audio:
        cmd += ["-c:a", "aac", "-b:a", "128k", "-shortest"]
    cmd += [out_mp4]
    subprocess.run(cmd, check=True, capture_output=True)


if __name__ == "__main__":
    which = sys.argv[1]
    if which == "image":
        n = gif_to_frames("g4_image.gif", "fr_image")
        encode("fr_image", "g4_image.mp4")
        print("g4_image.mp4", n, "コマ", round(n / FPS, 1), "秒")
    elif which == "sound":
        n = gif_to_frames("g4_sound.gif", "fr_sound")
        plays, total = open("g4_sound_plays.txt").read().split("\n")
        at = [int(x) for x in plays.split(",")]
        build_audio("snd_hit.wav", "g4_sound_track.wav", n, at)
        encode("fr_sound", "g4_sound.mp4", audio="g4_sound_track.wav")
        print("g4_sound.mp4", n, "コマ", round(n / FPS, 1), "秒", "鳴らすコマ", at)
    else:
        # ⑤ の完成画面。BGM を地に敷き、隕石に当たったコマで効果音を重ねる
        n = gif_to_frames("g5_done.gif", "fr_done")
        hits, skip = open("g5_done_hits.txt").read().split("\n")
        at = [int(x) for x in hits.split(",") if x]
        # 実機で鳴る音とずらさない。録画の開始コマぶん曲は進んでいる
        build_audio("snd_hit.wav", "g5_done_track.wav", n, at,
                    base_wav="bgm.wav", base_skip=int(skip))
        encode("fr_done", "g5_done.mp4", audio="g5_done_track.wav")
        print("g5_done.mp4", n, "コマ", round(n / FPS, 1), "秒", "鳴らすコマ", at)
