"""Read render/probe.json and surface values that vary across slides.

  python3 tools/inspect/audit.py         everything
  python3 tools/inspect/audit.py rule    one section only
                                         (text / link / rule / box / var)

Anything where elements of the same role carry different values on different
slides is reported as an inconsistency. The role is taken from the tail of the
selector (p.lead, div.msg and so on).
"""

import sys, json, re
from collections import defaultdict, Counter

D = json.load(open("render/probe.json"))

# The type area, fixed by the template; same values as tools/inspect/measure.py
PAD_L, PAD_R = 131, 1789
BODY_TOP, BODY_BOT = 268, 940

# Slides the type-area rules do not apply to
SPECIAL_CLS = {"cover", "hero", "section", "full", "closing", "image-main"}


def is_special(sc):
    return bool(SPECIAL_CLS & set(sc.split()))


def leaf(sel):
    """Tail of the selector, i.e. the name of the role."""
    return sel.split(" > ")[-1]


def rgb(c):
    m = re.match(r"rgba?\(([\d.]+), ([\d.]+), ([\d.]+)", c or "")
    if not m:
        return c
    r, g, b = (int(float(x)) for x in m.groups())
    return "#%02x%02x%02x" % (r, g, b)


def head(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def audit_text():
    head("TEXT: same role, different values")
    g = defaultdict(list)
    for r in D:
        if r["t"] != "text":
            continue
        g[leaf(r["sel"])].append(r)
    found = 0
    for name, rs in sorted(g.items()):
        if len(rs) < 2:
            continue
        keys = Counter((x["fs"], x["fw"], x["lh"], rgb(x["col"]), x["ls"], x["ff"]) for x in rs)
        if len(keys) < 2:
            continue
        # A role that appears on one slide only is a one-off flourish, not a
        # pattern, so it is skipped.
        pages = {x["p"] for x in rs}
        if len(pages) < 2:
            continue
        found += 1
        print(f"\n* {name}   {len(rs)} uses / {len(pages)} slides   {len(keys)} variants")
        for k, n in keys.most_common():
            ps = sorted({x["p"] for x in rs
                         if (x["fs"], x["fw"], x["lh"], rgb(x["col"]), x["ls"], x["ff"]) == k})
            mark = "  <- rare" if n <= 2 and len(keys) > 1 else ""
            print(f"   {n:>3}x  size {k[0]:<6} wt {k[1]:<4} lh {str(k[2]):<6} col {k[3]:<8} "
                  f"ls {k[4]:<6} {k[5][:16]:<16} P.{','.join(map(str, ps[:12]))}"
                  f"{'...' if len(ps) > 12 else ''}{mark}")
    if not found:
        print("  nothing varies")


def audit_rule():
    head("RULES: distribution of colour and width")
    c = Counter()
    for r in D:
        if r["t"] != "rule":
            continue
        c[(rgb(r["col"]), r["w"])] += 1
    print(f"{'colour':<10} {'width':<7} {'uses':>5}   slides")
    for (col, w), n in sorted(c.items(), key=lambda kv: -kv[1]):
        ps = sorted({r["p"] for r in D
                     if r["t"] == "rule" and rgb(r["col"]) == col and r["w"] == w})
        mark = "   <- only 1-2 slides" if len(ps) <= 2 else ""
        print(f"{col:<10} {w:<7} {n:>5}   P.{','.join(map(str, ps[:14]))}"
              f"{'...' if len(ps) > 14 else ''}{mark}")

    head("RULES: same role, different colour or width")
    g = defaultdict(list)
    for r in D:
        if r["t"] == "rule":
            g[(leaf(r["sel"]), r["kind"])].append(r)
    found = 0
    for (name, kind), rs in sorted(g.items()):
        pages = {x["p"] for x in rs}
        if len(pages) < 2:
            continue
        keys = Counter((rgb(x["col"]), x["w"]) for x in rs)
        if len(keys) < 2:
            continue
        found += 1
        print(f"\n* {name}  {kind}   {len(pages)} slides")
        for k, n in keys.most_common():
            ps = sorted({x["p"] for x in rs if (rgb(x["col"]), x["w"]) == k})
            print(f"   {n:>3}x  colour {k[0]:<9} width {k[1]:<6} P.{','.join(map(str, ps[:12]))}")
    if not found:
        print("  nothing varies")


def audit_link():
    head("LINKS: colour, underline, weight")
    print(f"{'pg':>3}  {'colour':<9} {'under':<6} {'wt':<4} {'size':<5} selector")
    for r in sorted([r for r in D if r["t"] == "link"], key=lambda r: r["p"]):
        print(f"{r['p']:>3}  {rgb(r['col']):<9} {r['td']:<6} {r['fw']:<4} {r['fs']:<5} "
              f"{r['sel']}  | {r['txt'][:30]}")
    cols = Counter(rgb(r["col"]) for r in D if r["t"] == "link")
    print(f"\n  colours: " + "  ".join(f"{c} x{n}" for c, n in cols.most_common()))

    # Is --cy used outside links too? If so, colour alone does not mark a link.
    cy = "#395c98"
    others = sorted({(r["p"], leaf(r["sel"])) for r in D
                     if r["t"] == "text" and rgb(r["col"]) == cy})
    if others:
        print(f"\n  non-link elements using the same colour {cy}:")
        byname = defaultdict(set)
        for p, n in others:
            byname[n].add(p)
        for n, ps in sorted(byname.items()):
            print(f"    {n:<24} P.{','.join(map(str, sorted(ps)[:14]))}")


def audit_box():
    head("TYPE AREA: direct children overflowing or leaving space")
    print(f"{'pg':>3}  {'left':>6} {'right':>6} {'top':>6} {'bot':>6}   notes")
    for p in range(1, max(r["p"] for r in D) + 1):
        rs = [r for r in D if r["t"] == "box" and r["p"] == p]
        if not rs:
            continue
        sc = rs[0]["sc"]
        if is_special(sc):
            print(f"{p:>3}  {'':>6} {'':>6} {'':>6} {'':>6}   (special layout: {sc})")
            continue
        x0 = min(r["x"] for r in rs)
        x1 = max(r["x"] + r["w"] for r in rs)
        y0 = min(r["y"] for r in rs)
        y1 = max(r["y"] + r["h"] for r in rs)
        note = []
        if x0 < PAD_L - 1:
            note.append(f"{PAD_L-x0:.0f}px past the left edge")
        if x1 > PAD_R + 1:
            note.append(f"{x1-PAD_R:.0f}px past the right edge")
        if y1 > BODY_BOT + 60:
            note.append(f"{y1-BODY_BOT:.0f}px past the bottom")
        print(f"{p:>3}  {x0:>6.0f} {x1:>6.0f} {y0:>6.0f} {y1:>6.0f}   {' / '.join(note)}")


def audit_var():
    head("FONTS: font-family in use")
    c = Counter(r["ff"] for r in D if r["t"] == "text")
    for f, n in c.most_common():
        ps = sorted({r["p"] for r in D if r["t"] == "text" and r["ff"] == f})
        print(f"  {f:<28} {n:>5}x  {len(ps)} slides"
              + (f"  P.{','.join(map(str, ps))}" if len(ps) <= 6 else ""))

    head("WEIGHTS: font-weight in use")
    c = Counter(r["fw"] for r in D if r["t"] == "text")
    for f, n in c.most_common():
        print(f"  {f:<6} {n:>5}x")

    head("SIZES: font-size in use, watching for values that sit too close")
    c = Counter(r["fs"] for r in D if r["t"] == "text")
    prev = None
    for f, n in sorted(c.items()):
        gap = f" <- only {f-prev:.1f}px from the previous" if prev is not None and 0 < f - prev <= 2 else ""
        print(f"  {f:<7} {n:>5}x{gap}")
        prev = f


what = sys.argv[1] if len(sys.argv) > 1 else "all"
if what in ("all", "text"):
    audit_text()
if what in ("all", "rule"):
    audit_rule()
if what in ("all", "link"):
    audit_link()
if what in ("all", "box"):
    audit_box()
if what in ("all", "var"):
    audit_var()
