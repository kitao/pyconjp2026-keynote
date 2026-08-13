#!/bin/sh
# 指定ページの見出し欄をDOMで測る:  ./measure-header.sh 16 4 7   （ページ / 英題を下げる量 / ロゴを下げる量）
cd "$(dirname "$0")/../.."
npx --yes @marp-team/marp-cli@latest slides.md --no-stdin --html --allow-local-files \
  --theme-set theme/pyxel.css --template bare -o .p.html </dev/null >/dev/null 2>&1 || exit 1
python3 - "$1" << 'PYEOF'
import sys
n=int(sys.argv[1]); h=open(".p.html").read()
js = """
<script>window.addEventListener('load',function(){
  var s=document.querySelectorAll('section')[%d-1];
  var sr=s.getBoundingClientRect(), k=1080/sr.height;
  var h1=s.querySelector('h1'), h2=s.querySelector('h1+h2');
  function T(e){return Math.round((e.getBoundingClientRect().top-sr.top)*k)}
  function B(e){return Math.round((e.getBoundingClientRect().bottom-sr.top)*k)}
  var d=document.createElement('div'); d.id='MEAS';
  d.textContent='['+s.className+'] h1='+T(h1)+'..'+B(h1)+' h2='+T(h2)+'..'+B(h2)+' 罫='+(B(h2)-2);
  document.body.appendChild(d);
});</script>""" % n
open(".p1.html","w").write(h.replace("</body>", js+"</body>"))
PYEOF
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
  --virtual-time-budget=6000 --dump-dom "file://$PWD/.p1.html" 2>/dev/null \
  | grep -o 'id="MEAS">[^<]*' | sed 's/id="MEAS">//'
rm -f .p.html .p1.html
