#!/bin/sh
# Render a single slide to an image:  ./page.sh 8  ->  render/P8.png
cd "$(dirname "$0")/../.."

# Chrome is looked for in the default location; set CHROME to override it.
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
N="${1:-1}"
npx --yes @marp-team/marp-cli@latest slides.md --no-stdin --html --allow-local-files \
  --theme-set theme/pyxel.css --template bare -o .p.html </dev/null >/dev/null 2>&1 || exit 1
python3 tools/slides/hl.py .p.html   # hl.py lives in tools/slides/ (we cd'd to the root above)
python3 - "$N" << 'PYEOF'
import sys,re
n=int(sys.argv[1])
h=open(".p.html").read()
js = """
<style>html,body{margin:0;background:#fff}</style>
<script>window.addEventListener('load',function(){
  var ss=document.querySelectorAll('section');
  ss.forEach(function(s,i){ if(i!==%d-1){ var p=s.closest('svg')||s; p.style.display='none'; } });
  var t=ss[%d-1], w=t.closest('svg')||t;
  w.style.width='1920px'; w.style.height='1080px';
  document.body.style.width='1920px';
});</script>""" % (n,n)
open(".p1.html","w").write(h.replace("</body>", js+"</body>"))
PYEOF
"$CHROME" --headless --disable-gpu \
  --hide-scrollbars --window-size=1920,1080 --virtual-time-budget=8000 \
  --screenshot=.page.png "file://$PWD/.p1.html" >/dev/null 2>&1
rm -f .p.html .p1.html
cp .page.png "render/P$N.png"
echo "wrote render/P$N.png (not opened)"
