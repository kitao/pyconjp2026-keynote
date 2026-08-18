"""Refuse a PDF whose pages are not all the same size and the right way up.

Chrome writes a /Rotate onto a page now and again. It does not come from
anything in the deck and it is not the same page twice: printing again clears
it. A reader gets one slide on its side, so build.sh runs this and stops.

  python3 tools/slides/checkpdf.py <pdf>
"""

import collections
import re
import subprocess
import sys

pdf = sys.argv[1]
out = subprocess.run(["pdfinfo", "-f", "1", "-l", "9999", pdf],
                     capture_output=True, text=True).stdout

rot = {int(p): int(r) for p, r in re.findall(r"^Page +(\d+) rot: +(-?\d+)", out, re.M)}
size = collections.Counter(re.findall(r"^Page +\d+ size: +([\d.]+ x [\d.]+)", out, re.M))

turned = [p for p, r in sorted(rot.items()) if r != 0]
if turned:
    raise SystemExit("page %s came out rotated; print again"
                     % ", ".join(str(p) for p in turned))
if len(size) > 1:
    raise SystemExit("pages came out at different sizes: %s" % dict(size))
if not size:
    raise SystemExit("no pages found in %s" % pdf)

print("%d pages, all %s pts, none rotated" % (sum(size.values()), next(iter(size))))
