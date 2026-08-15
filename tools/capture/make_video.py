"""Turn a captured GIF into an MP4, mixing in sound where needed.

A GIF loops and carries no audio, so the editor sessions are shipped as video.
GIF frame delays are quantised to 1/100 s and cannot express 30 fps, so the
frames are expanded to PNGs and laid out again at exactly 30 fps.
"""

import array
import os
import subprocess
import sys
import wave

FPS = 30
RATE = 22050  # Sample rate of the WAVs Pyxel writes


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
    """Mix src_wav into a track of total_frames at the given frame positions.

    With base_wav, that file from frame base_skip onwards becomes the bed
    (the BGM); without it the effect is mixed over silence.
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
    # The effect plays on a single channel, so build the effect track first.
    # Playing again while it still sounds restarts it, so writes overwrite
    # here. Adding instead would stack repeated hits into an unnatural peak.
    se = array.array("h", [0] * total)
    for fr in at_frames:
        off = int(fr / FPS * rate) * ch
        for i in range(min(len(clip), len(se) - off)):
            se[off + i] = clip[i]
    # BGM and effect sound on separate channels at the same time, so they are
    # summed here. Overwriting would silence the BGM whenever the effect plays.
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
        print("g4_image.mp4", n, "frames", round(n / FPS, 1), "sec")
    elif which == "sound":
        n = gif_to_frames("g4_sound.gif", "fr_sound")
        plays, total = open("g4_sound_plays.txt").read().split("\n")
        at = [int(x) for x in plays.split(",")]
        build_audio("snd_hit.wav", "g4_sound_track.wav", n, at)
        encode("fr_sound", "g4_sound.mp4", audio="g4_sound_track.wav")
        print("g4_sound.mp4", n, "frames", round(n / FPS, 1), "sec", "at", at)
    else:
        # Step 5, the finished screen: lay down the BGM and mix the effect in
        # on the frames where a meteor hit.
        n = gif_to_frames("g5_done.gif", "fr_done")
        hits, skip = open("g5_done_hits.txt").read().split("\n")
        at = [int(x) for x in hits.split(",") if x]
        # Keep it aligned with what the app plays: the tune has already
        # advanced by the number of frames skipped before recording.
        build_audio("snd_hit.wav", "g5_done_track.wav", n, at,
                    base_wav="bgm.wav", base_skip=int(skip))
        encode("fr_done", "g5_done.mp4", audio="g5_done_track.wav")
        print("g5_done.mp4", n, "frames", round(n / FPS, 1), "sec", "at", at)
