"""render/probe.json を読み、ページ横断で値のばらつきを洗い出す。

  python3 tools/audit.py            # 全部
  python3 tools/audit.py rule       # 線だけ（text / link / rule / box / var）

「同じ役割の要素が、ページによって違う値を持っている」ものを不整合として出す。
役割はセレクタの末尾（p.lead, div.msg など）で判定する。
"""

import sys, json, re
from collections import defaultdict, Counter

D = json.load(open("render/probe.json"))

# 版面（テンプレの不変項目。tools/inspect/measure.py と同じ値）
PAD_L, PAD_R = 131, 1789
BODY_TOP, BODY_BOT = 268, 940

# 版面の規則が当てはまらないページ
SPECIAL_CLS = {"cover", "hero", "section", "full", "closing", "image-main"}


def is_special(sc):
    return bool(SPECIAL_CLS & set(sc.split()))


def leaf(sel):
    """セレクタの末尾（役割の名前）"""
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
    head("【文字】同じ役割で値が割れているもの")
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
        # 1ページにしか出ない役割は、その場かぎりの飾りなので除く
        pages = {x["p"] for x in rs}
        if len(pages) < 2:
            continue
        found += 1
        print(f"\n● {name}   {len(rs)}件 / {len(pages)}ページ   {len(keys)}通り")
        for k, n in keys.most_common():
            ps = sorted({x["p"] for x in rs
                         if (x["fs"], x["fw"], x["lh"], rgb(x["col"]), x["ls"], x["ff"]) == k})
            mark = "  ← 少数" if n <= 2 and len(keys) > 1 else ""
            print(f"   {n:>3}件  字{k[0]:<6} 太{k[1]:<4} 行{str(k[2]):<6} 色{k[3]:<8} "
                  f"送{k[4]:<6} {k[5][:16]:<16} P.{','.join(map(str, ps[:12]))}"
                  f"{'...' if len(ps) > 12 else ''}{mark}")
    if not found:
        print("  割れているものはありません")


def audit_rule():
    head("【線】色と太さの分布")
    c = Counter()
    for r in D:
        if r["t"] != "rule":
            continue
        c[(rgb(r["col"]), r["w"])] += 1
    print(f"{'色':<10} {'太さ':<7} {'件数':>5}   出るページ")
    for (col, w), n in sorted(c.items(), key=lambda kv: -kv[1]):
        ps = sorted({r["p"] for r in D
                     if r["t"] == "rule" and rgb(r["col"]) == col and r["w"] == w})
        mark = "   ← 1〜2ページだけ" if len(ps) <= 2 else ""
        print(f"{col:<10} {w:<7} {n:>5}   P.{','.join(map(str, ps[:14]))}"
              f"{'...' if len(ps) > 14 else ''}{mark}")

    head("【線】同じ役割で色か太さが割れているもの")
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
        print(f"\n● {name}  {kind}   {len(pages)}ページ")
        for k, n in keys.most_common():
            ps = sorted({x["p"] for x in rs if (rgb(x["col"]), x["w"]) == k})
            print(f"   {n:>3}件  色{k[0]:<9} 太さ{k[1]:<6} P.{','.join(map(str, ps[:12]))}")
    if not found:
        print("  割れているものはありません")


def audit_link():
    head("【リンク】色・下線・太さ")
    print(f"{'頁':>3}  {'色':<9} {'下線':<6} {'太さ':<4} {'字':<5} セレクタ")
    for r in sorted([r for r in D if r["t"] == "link"], key=lambda r: r["p"]):
        print(f"{r['p']:>3}  {rgb(r['col']):<9} {r['td']:<6} {r['fw']:<4} {r['fs']:<5} "
              f"{r['sel']}  | {r['txt'][:30]}")
    cols = Counter(rgb(r["col"]) for r in D if r["t"] == "link")
    print(f"\n  色の内訳: " + "  ".join(f"{c}×{n}" for c, n in cols.most_common()))

    # --cy はリンク以外にも使われているか（色だけではリンクの印にならない、の確認）
    cy = "#395c98"
    others = sorted({(r["p"], leaf(r["sel"])) for r in D
                     if r["t"] == "text" and rgb(r["col"]) == cy})
    if others:
        print(f"\n  同じ色 {cy} を使っている非リンクの要素:")
        byname = defaultdict(set)
        for p, n in others:
            byname[n].add(p)
        for n, ps in sorted(byname.items()):
            print(f"    {n:<24} P.{','.join(map(str, sorted(ps)[:14]))}")


def audit_box():
    head("【版面】section 直下の中身が版面からはみ出している／余っている")
    print(f"{'頁':>3}  {'左':>6} {'右':>6} {'上':>6} {'下':>6}   所見")
    for p in range(1, max(r["p"] for r in D) + 1):
        rs = [r for r in D if r["t"] == "box" and r["p"] == p]
        if not rs:
            continue
        sc = rs[0]["sc"]
        if is_special(sc):
            print(f"{p:>3}  {'':>6} {'':>6} {'':>6} {'':>6}   （特別レイアウト・{sc}）")
            continue
        x0 = min(r["x"] for r in rs)
        x1 = max(r["x"] + r["w"] for r in rs)
        y0 = min(r["y"] for r in rs)
        y1 = max(r["y"] + r["h"] for r in rs)
        note = []
        if x0 < PAD_L - 1:
            note.append(f"左に{PAD_L-x0:.0f}px はみ出し")
        if x1 > PAD_R + 1:
            note.append(f"右に{x1-PAD_R:.0f}px はみ出し")
        if y1 > BODY_BOT + 60:
            note.append(f"下に{y1-BODY_BOT:.0f}px はみ出し")
        print(f"{p:>3}  {x0:>6.0f} {x1:>6.0f} {y0:>6.0f} {y1:>6.0f}   {' / '.join(note)}")


def audit_var():
    head("【書体】使われている font-family")
    c = Counter(r["ff"] for r in D if r["t"] == "text")
    for f, n in c.most_common():
        ps = sorted({r["p"] for r in D if r["t"] == "text" and r["ff"] == f})
        print(f"  {f:<28} {n:>5}件  {len(ps)}ページ"
              + (f"  P.{','.join(map(str, ps))}" if len(ps) <= 6 else ""))

    head("【太さ】使われている font-weight")
    c = Counter(r["fw"] for r in D if r["t"] == "text")
    for f, n in c.most_common():
        print(f"  {f:<6} {n:>5}件")

    head("【字の大きさ】使われている font-size（近い値が並んでいないか）")
    c = Counter(r["fs"] for r in D if r["t"] == "text")
    prev = None
    for f, n in sorted(c.items()):
        gap = f" ← 直前と{f-prev:.1f}pxしか違わない" if prev is not None and 0 < f - prev <= 2 else ""
        print(f"  {f:<7} {n:>5}件{gap}")
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
