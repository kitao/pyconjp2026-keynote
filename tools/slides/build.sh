#!/bin/sh
# slides.md → 配布用 PDF
# 中間HTMLは必ずこのフォルダに置く（assets/ への相対パスを保つため）
cd "$(dirname "$0")/../.."

# Chrome は既定の場所を見る。別の場所に入れているときは環境変数 CHROME で渡す
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
OUT="${1:-pyconjp2026-keynote.pdf}"
npx --yes @marp-team/marp-cli@latest slides.md --no-stdin --html --allow-local-files \
  --theme-set theme/pyxel.css -o .build.html || exit 1
python3 "$(dirname "$0")/hl.py" .build.html   # 行ハイライトと鉤括弧のぶら下げ
"$CHROME" --headless --disable-gpu \
  --no-pdf-header-footer --virtual-time-budget=20000 \
  --print-to-pdf="$OUT" "file://$PWD/.build.html" 2>&1 | tail -1
rm -f .build.html
