#!/bin/sh
# Dump the computed styles of every slide into render/probe.json.
# This is the raw material for comparing values across slides that an image
# cannot show: type size, weight and colour, rule width and colour, link colour.
cd "$(dirname "$0")/../.." || exit 1

# Chrome is looked for in the default location; set CHROME to override it.
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"

npx --yes @marp-team/marp-cli@latest slides.md --no-stdin --html --allow-local-files \
  --theme-set theme/pyxel.css --template bare -o .probe.tmp.html </dev/null >/dev/null 2>&1 \
  || { echo "conversion failed"; exit 1; }
python3 tools/slides/hl.py .probe.tmp.html

python3 - << 'PYEOF'
h = open(".probe.tmp.html").read()
js = "<script>" + open("tools/inspect/probe.js").read() + "</script>"
css = "<style>html,body{margin:0;padding:0;background:#fff}" \
      "svg[data-marpit-svg]{display:block;width:1920px;height:1080px}</style>"
open(".probe.tmp1.html", "w").write(h.replace("</body>", css + js + "</body>"))
PYEOF

"$CHROME" --headless --disable-gpu \
  --hide-scrollbars --window-size=1920,1080 --virtual-time-budget=25000 \
  --dump-dom "file://$PWD/.probe.tmp1.html" > .probe.dom.html 2>/dev/null

python3 - << 'PYEOF'
import re, json
h = open(".probe.dom.html", encoding="utf-8").read()
m = re.search(r'<pre id="PROBE_RESULT">(.*?)</pre>', h, re.S)
if not m:
    raise SystemExit("PROBE_RESULT missing; the render failed")
import html as H
data = json.loads(H.unescape(m.group(1)))
json.dump(data, open("render/probe.json", "w"), ensure_ascii=False)
kinds = {}
for r in data:
    kinds[r["t"]] = kinds.get(r["t"], 0) + 1
pages = max(r["p"] for r in data)
print(f"render/probe.json  {len(data)} entries / {pages} slides  " +
      "  ".join(f"{k}={v}" for k, v in sorted(kinds.items())))
PYEOF
rm -f .probe.tmp.html .probe.tmp1.html .probe.dom.html
