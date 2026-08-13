#!/bin/sh
# 全ページの computed style を吸い出して render/probe.json に落とす。
# 画像では分からない値（字の大きさ・太さ・色、線の太さ・色、リンクの色）を
# ページ横断で突き合わせるための素材。
cd "$(dirname "$0")/../.." || exit 1

npx --yes @marp-team/marp-cli@latest slides.md --no-stdin --html --allow-local-files \
  --theme-set theme/pyxel.css --template bare -o .probe.tmp.html </dev/null >/dev/null 2>&1 \
  || { echo "変換に失敗"; exit 1; }
python3 tools/slides/hl.py .probe.tmp.html

python3 - << 'PYEOF'
h = open(".probe.tmp.html").read()
js = "<script>" + open("tools/inspect/probe.js").read() + "</script>"
css = "<style>html,body{margin:0;padding:0;background:#fff}" \
      "svg[data-marpit-svg]{display:block;width:1920px;height:1080px}</style>"
open(".probe.tmp1.html", "w").write(h.replace("</body>", css + js + "</body>"))
PYEOF

"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
  --hide-scrollbars --window-size=1920,1080 --virtual-time-budget=25000 \
  --dump-dom "file://$PWD/.probe.tmp1.html" > .probe.dom.html 2>/dev/null

python3 - << 'PYEOF'
import re, json
h = open(".probe.dom.html", encoding="utf-8").read()
m = re.search(r'<pre id="PROBE_RESULT">(.*?)</pre>', h, re.S)
if not m:
    raise SystemExit("PROBE_RESULT が見つかりません（描画に失敗している）")
import html as H
data = json.loads(H.unescape(m.group(1)))
json.dump(data, open("render/probe.json", "w"), ensure_ascii=False)
kinds = {}
for r in data:
    kinds[r["t"]] = kinds.get(r["t"], 0) + 1
pages = max(r["p"] for r in data)
print(f"render/probe.json  {len(data)} 件 / {pages} ページ  " +
      "  ".join(f"{k}={v}" for k, v in sorted(kinds.items())))
PYEOF
rm -f .probe.tmp.html .probe.tmp1.html .probe.dom.html
