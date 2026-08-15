"""Measure the dimensions of a slide.

Writing the measuring code afresh each time gets the ranges wrong and picks up
the wrong thing (counting a wall as a resident, mixing a border with a
background). Anything whose position is fixed lives here as a constant.

  python3 tools/inspect/measure.py 32          # vertical structure of slide 32
  python3 tools/inspect/measure.py 32 --bands  # every band that carries ink
"""

import sys
import numpy as np
from PIL import Image

# -- Fixed by the template; do not move ------------------------------------
SLIDE_W, SLIDE_H = 1920, 1080
PAD_L, PAD_R = 131, 1789        # Left and right of the type area
BODY_TOP, BODY_BOT = 268, 940   # Top and bottom of the body area
RULE_Y = 210                    # The rule under the heading

# -- The footer band, a separate layer that must always be excluded --------
# Residents bottom right, page number bottom left, both from y999 down.
HOUSE_X0, HOUSE_X1 = 1550, 1810   # Width covering the residents alone; the
                                  # three of them sit at x1559-1788
# Narrowing this counts the first resident (x1559-1608) as body content and
# reports a false overflow of the type area.
PAGENO_X0, PAGENO_X1 = 120, 240   # Width covering the page number alone
FOOT_Y0 = 950                     # Everything below counts as the footer band

# Width used when measuring the body. Content usually sits in the central
# 1500 px (starting at 210), but some layouts (two-up, .chron, .pack) span the
# full type area, so the full width is used.
BODY_X0, BODY_X1 = PAD_L, PAD_R


def load(page):
    a = np.array(Image.open(f"render/P{page}.png").convert("RGB")).astype(int)
    if a.shape[1] != SLIDE_W:
        raise SystemExit(f"unexpected image width: {a.shape[1]} (expected {SLIDE_W})")
    return a


def ink(a, th=26):
    return np.abs(a - 255).sum(axis=2) > th


def bands(m, y0, y1, x0, x1, min_h=3):
    """Bands that carry ink, top to bottom."""
    sub = m[y0:y1, x0:x1]
    rows = sub.sum(axis=1) > 2
    out, s = [], None
    for i, v in enumerate(rows):
        if v and s is None:
            s = i
        if not v and s is not None:
            if i - s >= min_h:
                out.append((y0 + s, y0 + i - 1))
            s = None
    if s is not None and (y1 - y0) - s >= min_h:
        out.append((y0 + s, y1 - 1))
    return out


def span_x(m, y0, y1, x0, x1):
    sub = m[y0:y1 + 1, x0:x1]
    xs = np.where(sub.any(axis=0))[0]
    return (x0 + xs.min(), x0 + xs.max()) if len(xs) else (None, None)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    page = int(sys.argv[1])
    show_bands = "--bands" in sys.argv
    a = load(page)
    m = ink(a)

    # Body, excluding the footer band
    body = bands(m, RULE_Y + 8, FOOT_Y0, BODY_X0, BODY_X1)
    # Footer band; each part is measured in its own narrow width, because a
    # wider range would swallow body content.
    house = bands(m, FOOT_Y0, SLIDE_H, HOUSE_X0, HOUSE_X1)
    pageno = bands(m, FOOT_Y0, SLIDE_H, PAGENO_X0, PAGENO_X1)

    print(f"── P.{page} ──")
    if not body:
        print("no ink in the body")
        return
    top, bot = body[0][0], body[-1][1]
    l, r = span_x(m, RULE_Y + 8, FOOT_Y0 - 1, BODY_X0, BODY_X1)

    print(f"body       y{top}-{bot}   x{l}-{r}")
    print(f"  below the rule ({RULE_Y})   {top - RULE_Y} px")
    print(f"  to the bottom ({BODY_BOT})   {BODY_BOT - bot} px" +
          ("   <- overflowing" if bot > BODY_BOT else ""))
    print(f"  to the right ({PAD_R})     {PAD_R - r} px")
    if house:
        print(f"residents  y{house[0][0]}-{house[-1][1]}   gap from body {house[0][0] - bot} px")
    if pageno:
        print(f"page no.   y{pageno[0][0]}-{pageno[-1][1]}")

    if show_bands:
        print("\nbands with ink:")
        prev = None
        for y0, y1 in body:
            bl, br = span_x(m, y0, y1, BODY_X0, BODY_X1)
            gap = "" if prev is None else f"  gap above {y0 - prev} px"
            print(f"  y{y0:4}-{y1:<4} height {y1 - y0 + 1:4}  x{bl}-{br}{gap}")
            prev = y1


if __name__ == "__main__":
    main()
