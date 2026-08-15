#!/bin/sh
# Write every slide to render/hi/P<N>.png at 2x resolution (3840x2160).
#   ./renderall.sh          every slide
#   ./renderall.sh 4        slides per batch (default 4)
# Starting Chrome is slow, so several slides are stacked and captured in one
# go, then cut apart afterwards.
cd "$(dirname "$0")/../.." || exit 1
BAND="${1:-4}"
SCALE=2
mkdir -p render/hi

npx --yes @marp-team/marp-cli@latest slides.md --no-stdin --html --allow-local-files \
  --theme-set theme/pyxel.css --template bare -o .all.tmp.html </dev/null >/dev/null 2>&1 \
  || { echo "conversion failed"; exit 1; }
python3 tools/slides/hl.py .all.tmp.html

python3 - "$BAND" "$SCALE" << 'PYEOF'
import sys, os, subprocess, glob
from PIL import Image

band, scale = int(sys.argv[1]), int(sys.argv[2])
html = open(".all.tmp.html").read()

# One section per slide
import re
total = len(re.findall(r'<section', html))
print(f"capturing {total} slides at {scale}x, {band} at a time")

CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
for start in range(1, total + 1, band):
    end = min(start + band - 1, total)
    n = end - start + 1
    js = """
<style>html,body{margin:0;padding:0;background:#fff}
svg[data-marpit-svg]{display:block;width:1920px;height:1080px}</style>
<script>window.addEventListener('load',function(){
  var ss=document.querySelectorAll('svg[data-marpit-svg]');
  ss.forEach(function(s,i){ var n=i+1; if(n<%d||n>%d){ s.style.display='none'; } });
  document.body.style.width='1920px';
});</script>""" % (start, end)
    open(".all.tmp1.html", "w").write(html.replace("</body>", js + "</body>"))
    out = f".band_{start}.png"
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                    f"--force-device-scale-factor={scale}",
                    f"--window-size=1920,{1080*n}", "--virtual-time-budget=20000",
                    f"--screenshot={out}", f"file://{os.getcwd()}/.all.tmp1.html"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    im = Image.open(out)
    for k in range(n):
        pg = start + k
        im.crop((0, 1080*scale*k, 1920*scale, 1080*scale*(k+1))).save(f"render/hi/P{pg}.png")
    os.remove(out)
    print(f"  P.{start}〜P.{end}  ({im.size[0]}x{im.size[1]})")

os.remove(".all.tmp1.html")
PYEOF
rm -f .all.tmp.html
echo "wrote render/hi/"
