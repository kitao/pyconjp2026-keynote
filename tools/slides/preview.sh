#!/bin/sh
# 本番と同じHTMLをブラウザで開く。
#   ← → PageUp/Down Space   ページ送り
#   数字 → Enter             そのページへ移動（tools/slides/keys.js が足している操作）
#   F                        全画面
#   P                        無効（発表者ツールは使わない。誤って別ウィンドウが開くのを防ぐ）
#
# 画面の下に出る補助UI（OSC）は出さない（--bespoke.osc=false）。
# マウスを動かすたびに現れて、動画の再生・シークの邪魔になるため。
# ページ番号はスライド自身が左下に出しているので、これで失うものはない。
cd "$(dirname "$0")/../.."
npx --yes @marp-team/marp-cli@latest slides.md --no-stdin --html --allow-local-files \
  --theme-set theme/pyxel.css --template bespoke --bespoke.osc=false \
  -o index.html </dev/null >/dev/null 2>&1 || exit 1

# Marp のテンプレに無い操作を差し込む（数字を打って Enter でページ移動）
python3 - << 'PYEOF'
h = open("index.html").read()
js = open("tools/slides/keys.js").read()
tag = "<script>\n" + js + "</script>"
if "</body>" in h:
    h = h.replace("</body>", tag + "</body>", 1)
else:
    h += tag
open("index.html", "w").write(h)
PYEOF

python3 tools/slides/hl.py index.html
open index.html
echo "index.html を開きました（← → で送り、数字→Enter でジャンプ、F で全画面）"
