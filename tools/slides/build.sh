#!/bin/sh
# slides.md -> the PDF that gets handed out
# The intermediate HTML must stay in this folder so the relative paths into
# assets/ keep resolving.
set -eu
cd "$(dirname "$0")/../.."
trap 'rm -f .build.html' EXIT

# Chrome is looked for in the default location; set CHROME to override it.
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
OUT="${1:-pyconjp2026-keynote.pdf}"
npx --no-install marp slides.md --no-stdin --html --allow-local-files \
  --theme-set theme/pyxel.css -o .build.html || exit 1
python3 "$(dirname "$0")/hl.py" .build.html   # Line highlights and hanging brackets
# The print is driven through the DevTools protocol rather than Chrome's
# --print-to-pdf, which does not wait for the bundled faces (see topdf.js).
# puppeteer-core is installed by npm ci; it drives the Chrome above.
CHROME="$CHROME" \
  node tools/slides/topdf.js "$PWD/.build.html" "$OUT"
rm -f .build.html
# Chrome turns a page on its side now and again; checkpdf.py stops that shipping
python3 "$(dirname "$0")/checkpdf.py" "$OUT" || exit 1
ls -l "$OUT"
