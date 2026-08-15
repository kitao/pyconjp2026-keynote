#!/bin/sh
# Stack the given slides into one image:  ./shot.sh <name> 1 8 18 ...
cd "$(dirname "$0")/../.."

# Chrome is looked for in the default location; set CHROME to override it.
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
OUT="$1"; shift
npx --yes @marp-team/marp-cli@latest slides.md --no-stdin --html --allow-local-files \
  --theme-set theme/pyxel.css --template bare -o .p.html </dev/null >/dev/null 2>&1 || exit 1
python3 - "$@" << 'PYEOF'
import sys
ns=[int(x) for x in sys.argv[1:]]
h=open(".p.html").read()
js="""<style>html,body{margin:0;background:#888}</style><script>window.addEventListener('load',function(){
var K=%s; var ss=document.querySelectorAll('section');
ss.forEach(function(s,i){ var w=s.closest('svg')||s;
  if(K.indexOf(i+1)<0){ w.style.display='none'; }
  else { w.style.width='1920px'; w.style.height='1080px'; w.style.display='block'; w.style.marginBottom='12px'; }});
document.body.style.width='1920px';});</script>""" % (ns,)
open(".p1.html","w").write(h.replace("</body>",js+"</body>"))
PYEOF
H=$(( $# * 1094 + 20 ))
"$CHROME" --headless --disable-gpu \
  --hide-scrollbars --window-size=1920,$H --virtual-time-budget=8000 \
  --screenshot="render/$OUT.png" "file://$PWD/.p1.html" >/dev/null 2>&1
rm -f .p.html .p1.html
open "render/$OUT.png"
echo "render/$OUT.png"
