#!/bin/sh
# slides.md -> the PDF that gets handed out
# The intermediate HTML must stay in this folder so the relative paths into
# assets/ keep resolving.
cd "$(dirname "$0")/../.."

# Chrome is looked for in the default location; set CHROME to override it.
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
OUT="${1:-pyconjp2026-keynote.pdf}"
npx --yes @marp-team/marp-cli@latest slides.md --no-stdin --html --allow-local-files \
  --theme-set theme/pyxel.css -o .build.html || exit 1
python3 "$(dirname "$0")/hl.py" .build.html   # Line highlights and hanging brackets
"$CHROME" --headless --disable-gpu \
  --no-pdf-header-footer --virtual-time-budget=20000 \
  --print-to-pdf="$OUT" "file://$PWD/.build.html" 2>&1 | tail -1
rm -f .build.html
