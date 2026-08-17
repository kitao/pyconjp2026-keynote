#!/bin/sh
# Rebuilds the bundled type faces in assets/font/
#
# The deck ships its own faces so that it looks the same on every machine.
# Without them the face falls back to whatever the system has -- Hiragino here,
# Yu Gothic on Windows -- and the weight and the line widths change with it.
#
# Two things about the way they are cut, both learned the hard way:
#
#   * They are static cuts, one file per weight, not one variable file. Chrome
#     writes a variable instance into the PDF as a Type 3 font, and readers
#     built on poppler draw those as nothing at all -- whole pages came out
#     blank.
#   * Each file's internal weight (OS/2.usWeightClass) is set to the weight the
#     CSS asks for, not to the weight the glyphs were cut at. If the two differ,
#     the browser thinks it has to synthesise the weight, and the synthesised
#     runs are dropped from the PDF. So the file cut at 385 says 400, the one
#     cut at 425 says 500, and so on -- the shapes carry the tuned weight, the
#     numbers keep the browser out of it.
#
# The pairs below are (weight the glyphs are cut at, weight the file claims).
# The tuned values came from measuring ink against the old Hiragino rendering,
# size band by size band; see the theme's --w-* comments.
#
# Check the result with:  pdffonts pyconjp2026-keynote.pdf
# Anything but NotoSansJP / NotoSansIPA / NotoSansKRsub / NotoSansMono means a
# character fell through to a system font.
#
# Needs fonttools and brotli; they go into a throwaway venv so nothing is added
# to the machine.
cd "$(dirname "$0")/../.."
set -e

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

python3 -m venv "$WORK/venv"
"$WORK/venv/bin/pip" -q install fonttools brotli

GF="https://github.com/google/fonts/raw/main/ofl"
curl -sL -o "$WORK/NotoSansJP.ttf"   "$GF/notosansjp/NotoSansJP%5Bwght%5D.ttf"
curl -sL -o "$WORK/NotoSans.ttf"     "$GF/notosans/NotoSans%5Bwdth,wght%5D.ttf"
curl -sL -o "$WORK/NotoSansKR.ttf"   "$GF/notosanskr/NotoSansKR%5Bwght%5D.ttf"
curl -sL -o "$WORK/NotoSansMono.ttf" "$GF/notosansmono/NotoSansMono%5Bwdth,wght%5D.ttf"
curl -sL -o assets/font/OFL-NotoSansJP.txt   "$GF/notosansjp/OFL.txt"
curl -sL -o assets/font/OFL-NotoSans.txt     "$GF/notosans/OFL.txt"
curl -sL -o assets/font/OFL-NotoSansKR.txt   "$GF/notosanskr/OFL.txt"
curl -sL -o assets/font/OFL-NotoSansMono.txt "$GF/notosansmono/OFL.txt"

# Every character the slides use, entities resolved -- that last part is what
# brings in the © of the credit lines -- plus kana, ASCII and the punctuation a
# later edit is likely to reach for.
python3 - "$WORK/chars.txt" "$WORK/mono.txt" <<'PYEOF'
import html, re, sys

chars = set()
for name in ("index.html", "slides.md"):
    text = open(name, encoding="utf-8").read()
    chars |= {c for c in text + html.unescape(text) if c.strip()}
chars |= {chr(c) for c in range(0x20, 0x7F)}
chars |= {chr(c) for c in range(0x3041, 0x3097)}      # hiragana
chars |= {chr(c) for c in range(0x30A1, 0x30FB)}      # katakana
chars |= set("　、。，．・：；？！ー―‐／＼〜｜…‥「」『』（）［］｛｝〈〉《》【】"
             "＋－±×÷＝≠＜＞≦≧°′″℃￥＄％＃＆＊＠§☆★○●◎◇◆□■△▲▽▼※〒"
             "→←↑↓①②③④⑤⑥⑦⑧⑨⑩©®™")
open(sys.argv[1], "w", encoding="utf-8").write("".join(sorted(chars)))

# The code panels: what is inside <code> and <pre>, plus plain ASCII
h = open("index.html", encoding="utf-8").read()
code = "".join(re.findall(r"<code[^>]*>(.*?)</code>", h, re.S))
code += "".join(re.findall(r"<pre[^>]*>(.*?)</pre>", h, re.S))
mono = {c for c in html.unescape(re.sub(r"<[^>]+>", "", code)) if c.strip()}
mono |= {chr(c) for c in range(0x20, 0x7F)}
mono |= set("—–‘’“”→←↑↓×÷±≠≒…・「」（）")
open(sys.argv[2], "w", encoding="utf-8").write("".join(sorted(mono)))
PYEOF

printf 'ˈɪə' > "$WORK/ipa.txt"
printf '안녕하세요' > "$WORK/kr.txt"

cut_one() {   # source, axes, weight the file claims, characters, output, family
  "$WORK/venv/bin/python" - "$1" "$2" "$3" "$4" "$5" "$6" "$WORK/venv/bin/pyftsubset" <<'PYEOF'
import json
import subprocess
import sys

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

src, axes, declared, chars, out, family, pyftsubset = sys.argv[1:8]
declared = int(declared)

font = instancer.instantiateVariableFont(TTFont(src), json.loads(axes), inplace=False)
font["OS/2"].usWeightClass = declared
for rec in font["name"].names:
    if rec.nameID in (1, 4, 16):
        rec.string = family
    elif rec.nameID in (2, 17):
        rec.string = "Regular"
    elif rec.nameID == 6:
        rec.string = family.replace(" ", "") + "-" + str(declared)
tmp = out + ".ttf"
font.save(tmp)
subprocess.run([pyftsubset, tmp,
                "--text-file=" + chars, "--flavor=woff2",
                "--layout-features=*", "--output-file=" + out], check=True)
PYEOF
  rm -f "$5.ttf"
}

# (cut at, claims to be)
for pair in 330:300 385:400 425:500 460:600 500:700 620:800; do
  cut="${pair%:*}"; say="${pair#*:}"
  cut_one "$WORK/NotoSansJP.ttf" "{\"wght\": $cut}" "$say" "$WORK/chars.txt" \
          "assets/font/NotoSansJP-$cut.woff2" "Noto Sans JP $say"
done

# Noto Sans JP carries no IPA and no Hangul; the code face travels too
cut_one "$WORK/NotoSans.ttf" '{"wght": 400, "wdth": 100}' 400 "$WORK/ipa.txt" \
        assets/font/NotoSans-ipa-subset.woff2 "Noto Sans IPA"
cut_one "$WORK/NotoSansKR.ttf" '{"wght": 400}' 400 "$WORK/kr.txt" \
        assets/font/NotoSansKR-hangul-subset.woff2 "Noto Sans KR sub"
cut_one "$WORK/NotoSansMono.ttf" '{"wght": 400, "wdth": 100}' 400 "$WORK/mono.txt" \
        assets/font/NotoSansMono-subset.woff2 "Noto Sans Mono"

ls -l assets/font/
