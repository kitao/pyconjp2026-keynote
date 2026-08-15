"""Turn the trailer (trailer.py) into an MP4 with sound.

    python3 trailer/make_video.py     ->  trailer/trailer.mp4

Run it with a Python that has Pyxel installed (tools/requirements.txt); ffmpeg
is used as well. The picture is captured at 320x180 and scaled 4x to 1280x720
with nearest neighbour, so the pixel edges stay sharp. The sound is the BGM bed
with the firework effect mixed in at times derived from frame numbers.
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
# Screen capture (capture_sec) tops out at 60 seconds, so stop within that.
FRAMES = DUR_SEC * FPS - 2
OUT_MP4 = os.path.join(HERE, "trailer.mp4")

pyxel.init(320, 180, headless=True, capture_scale=1, capture_sec=60)

import trailer as mod  # noqa: E402

movie = mod.Movie()
movie.sound_setup()
# Export the firework effect and the BGM (the four channels gen_bgm writes).
pyxel.sounds[41].save("tr_se.wav", pyxel.sounds[41].total_sec())
BGM_LOOP = pyxel.sounds[44].total_sec()
for i in range(4):
    pyxel.sounds[44 + i].save(f"tr_bgm{i}.wav", BGM_LOOP)


def gif_to_frames(gif, outdir):
    """Split a GIF into one PNG per frame.

    GIF frame delays are quantised to 1/100 s and cannot express 30 fps, so
    handing the GIF straight to ffmpeg drifts. Extract the frames instead and
    let ffmpeg set the frame rate.
    """
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


# -- Picture ----------------------------------------------------------------
pyxel.reset_screencast()
for _ in range(FRAMES):
    movie.update()
    movie.draw()
    pyxel.flip()
pyxel.screencast("tr_take", scale=1)
n = gif_to_frames("tr_take.gif", "fr_trailer")
print("frames:", n)


def read_wav(path):
    with wave.open(path, "rb") as w:
        return (w.getnchannels(), w.getsampwidth(), w.getframerate(),
                array.array("h", w.readframes(w.getnframes())))


# -- Sound: quiet night, with only the fireworks placed on top --------------
# Take the sample rate from the WAV Pyxel wrote. Hard-coding it shifts pitch
# and length by whatever the mismatch is (reading 22050 Hz as 44100 Hz plays an
# octave high at half the length).
ch, sw, rate, _ = read_wav("tr_se.wav")
total = int(n / FPS * rate) * ch
track = array.array("h", bytes(total * 2))
print(f"mixing at {rate} Hz / {ch} ch / {sw * 8} bit")


# Edge ramps. Keep the head short so the attack stays sharp; the tail is longer
# to kill the click at the seam.
FADE_IN = max(1, rate // 1000)                   # about 1 ms
FADE_OUT = max(1, rate // 200)                   # about 5 ms


def mix(src, at_frame, gain):
    """Mix a sound in at the time of the given frame, ramping both edges."""
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


# -- Sound: same notes, same timing and same balance as the app (pyxel run).
# Sound.save() does not apply the channel gain, so it is applied here.
se = read_wav("tr_se.wav")[3]
shots = [t0 + 24 for t0, _, _ in movie.shots if t0 + 24 < n]   # fire on the burst frame

if movie.bgm:
    # Lay down the BGM, one pass per channel.
    bgm = [read_wav(f"tr_bgm{c}.wav")[3] for c in range(4)]
    loop_len = len(bgm[0])
    for c, src in enumerate(bgm):
        gain = (mod.Movie.CH_GAIN_SE if c == mod.Movie.SE_CH
                else mod.Movie.CH_GAIN_BGM)
        for pos in range(0, len(track), loop_len):
            mix(src, pos / rate * FPS, gain)
    # The fireworks interrupt the drum channel: the drum stops while a burst
    # sounds and resumes where it left off, matching resume=True in the app.
    drum = bgm[mod.Movie.SE_CH]
    for f in shots:
        a = int(f / FPS * rate)
        for j in range(a, min(a + len(se), len(track))):
            track[j] = max(-32768, min(32767,
                           track[j] - int(drum[j % loop_len] * mod.Movie.CH_GAIN_SE)))

for f in shots:
    mix(se, f, mod.Movie.CH_GAIN_SE)
print("fireworks mixed:", len(shots), "/ BGM:", "yes" if movie.bgm else "no")

# Scale the whole track to a level that carries when streamed. This is the
# volume knob: it does not change the balance between the individual sounds.
peak = max(abs(v) for v in track) or 1
scale = int(32767 * 0.72) / peak
for i in range(len(track)):
    track[i] = max(-32768, min(32767, int(track[i] * scale)))
print(f"scaled by {scale:.2f} (peak {peak} -> {int(peak * scale)})")

with wave.open("tr_track.wav", "wb") as w:
    w.setnchannels(ch)
    w.setsampwidth(sw)
    w.setframerate(rate)
    w.writeframes(track.tobytes())

# -- Encode: nearest-neighbour up to 1280x720, audio fades out over the last
# two seconds.
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
print("wrote:", OUT_MP4, round(n / FPS, 1), "sec")
