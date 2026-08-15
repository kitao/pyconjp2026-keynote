#!/bin/sh
# Open the same HTML that is used on stage.
#   Arrows, PageUp/Down, Space   next / previous slide
#   digits then Enter            jump to that slide (added by tools/slides/keys.js)
#   L                            laser pointer on / off (same file)
#   F                            full screen
#   P                            disabled; the presenter tools are not used, and
#                                this stops a stray window from opening
#
# The on-screen controls (OSC) are turned off (--bespoke.osc=false): they
# appear on every mouse move and get in the way of playing and scrubbing the
# videos. Nothing is lost, since the slides print the page number themselves.
cd "$(dirname "$0")/../.."
npx --yes @marp-team/marp-cli@latest slides.md --no-stdin --html --allow-local-files \
  --theme-set theme/pyxel.css --template bespoke --bespoke.osc=false \
  -o index.html </dev/null >/dev/null 2>&1 || exit 1

# Inject the key handling Marp's template does not provide.
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
echo "opened index.html (arrows to move, digits then Enter to jump, F for full screen)"
