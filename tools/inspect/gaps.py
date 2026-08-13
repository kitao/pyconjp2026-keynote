"""同じ役割の要素どうしの余白が、ページをまたいで揃っているかを測る。

版面や見出しの位置は揃っていても、「見出しの罫 → リード」「リード → 中身」の
アキがページごとに違うと、繰ったときに紙面が揺れて見える。

  python3 tools/gaps.py
"""

import json
from collections import defaultdict

D = json.load(open("render/probe.json"))
RULE_Y = 211          # 見出しの下の罫（全ページ共通）
SPECIAL = {"cover", "hero", "section", "closing", "image-main", "full"}


def is_special(sc):
    return bool(SPECIAL & set(sc.split()))


# section 直下の要素を、ページごとに上から並べる
pages = defaultdict(list)
for r in D:
    if r["t"] != "box":
        continue
    if r["sel"].split(".")[0] in ("h1", "h2"):
        continue
    pages[r["p"]].append(r)

print("【罫（y211）から最初の中身までのアキ】")
first = defaultdict(list)
for p, rs in sorted(pages.items()):
    sc = rs[0]["sc"] if rs else ""
    if is_special(sc):
        continue
    rs = sorted(rs, key=lambda r: r["y"])
    if not rs:
        continue
    top = rs[0]
    kind = top["sel"].split(" > ")[-1]
    first[round(top["y"] - RULE_Y)].append((p, kind))
for gap, items in sorted(first.items()):
    ps = ", ".join(f"P.{p}({k})" for p, k in items[:8])
    mark = "  ← 少数" if len(items) <= 2 else ""
    print(f"  {gap:>4}px  {len(items):>2}ページ   {ps}{'...' if len(items) > 8 else ''}{mark}")

print("\n【リードの下から次の要素までのアキ】")
lead_gap = defaultdict(list)
for p, rs in sorted(pages.items()):
    if not rs or is_special(rs[0]["sc"]):
        continue
    rs = sorted(rs, key=lambda r: r["y"])
    for i, r in enumerate(rs[:-1]):
        if "lead" not in r["sel"]:
            continue
        nxt = rs[i + 1]
        gap = round(nxt["y"] - (r["y"] + r["h"]))
        lead_gap[gap].append((p, nxt["sel"].split(" > ")[-1]))
for gap, items in sorted(lead_gap.items()):
    ps = ", ".join(f"P.{p}({k})" for p, k in items[:8])
    mark = "  ← 少数" if len(items) <= 2 else ""
    print(f"  {gap:>4}px  {len(items):>2}ページ   {ps}{'...' if len(items) > 8 else ''}{mark}")

print("\n【行間（line-height）が同じ字の大きさで割れているもの】")
g = defaultdict(set)
for r in D:
    if r["t"] != "text" or r["lh"] == "normal":
        continue
    g[r["fs"]].add(round(float(r["lh"]) / r["fs"], 3))
for fs, lhs in sorted(g.items()):
    if len(lhs) > 2:
        print(f"  字{fs:<6} 行間の比 {sorted(lhs)}")
