"""コードブロックの行に背景を付ける。

Marp には行ハイライトの機能が無いので、生成後の HTML を加工する。
slides.md のコード中で、強調したい行の末尾に `#!hl` と書いておくと、
その目印は出力から消え、代わりにその行へ薄い背景が付く。

  while True:  #!hl   →   <span class="cl hl">while True:</span>

各行を <span class="cl"> で包むのは、行単位の背景を敷くため。
（highlight.js の出力は行をまたがないので、改行で切って包める）
"""

import os
import re
import sys

# 目印は Python のコメントなので、highlight.js が <span class="hljs-comment"> で包む
MARK = re.compile(r'\s*(<span class="hljs-comment">)?#!hl(</span>)?\s*$')

# highlight.js は Pyxel を知らないので、pyxel.xxx を自前で色分けする。
# 大文字だけの名前は定数（KEY_LEFT など）、それ以外は関数（init, blt など）
PYXEL = re.compile(r"\bpyxel\.([A-Za-z_]\w*)")


# URL の中の pyxel.js は、モジュール名＋関数名ではなくただのファイル名。
# 文字列の一部なので色を足さない（足すと文字列の中だけ色が変わって見える）
URL_PLAIN = re.compile(r"https?://[^\s\"&<]+")


# <pyxel-run script="…"> の中身は Python だが、この塊は HTML として解析されるので、
# highlight.js は素通しにする。ゲームのページ（P.23〜P.27）と同じ見え方にするため、
# 属性の中だけ Python として色を足す。使う名前は highlight.js のものに合わせる
PY_BEGIN = re.compile(r'class="hljs-name">pyxel-run<')
PY_END = re.compile(r"^&quot;")
PY_KEYWORD = re.compile(
    r"\b(import|from|as|def|class|return|if|elif|else|for|while|in|is|not|and|or"
    r"|pass|break|continue|with|lambda|global|nonlocal|yield|try|except|finally|raise)\b")
PY_NUMBER = re.compile(r"\b\d+(?:\.\d+)?\b")


def paint_python(line: str) -> str:
    """属性の中の1行に、Python と同じ色を付ける（pyxel.xxx は paint が担う）"""
    line = PY_KEYWORD.sub(r'<span class="hljs-keyword">\1</span>', line)
    return PY_NUMBER.sub(r'<span class="hljs-number">\g<0></span>', line)


def paint(line: str) -> str:
    def one(m):
        name = m.group(1)
        cls = "pk" if name.isupper() else "pf"
        return f'<span class="pm">pyxel</span>.<span class="{cls}">{name}</span>'

    out, pos = [], 0
    for m in URL_PLAIN.finditer(line):
        out.append(PYXEL.sub(one, line[pos:m.start()]))
        out.append(m.group(0))          # URL はそのまま
        pos = m.end()
    out.append(PYXEL.sub(one, line[pos:]))
    return "".join(out)


def wrap(html: str) -> str:
    def one(m):
        body = m.group(2)
        # </code> の直前の改行は行ではない
        if body.endswith("\n"):
            body = body[:-1]
        out = []
        in_python = False            # <pyxel-run script="…"> の中にいるか
        for line in body.split("\n"):
            hl = bool(MARK.search(line))
            if hl:
                line = MARK.sub("", line)
            cls = "cl hl" if hl else "cl"
            if in_python and PY_END.match(line):
                in_python = False
            elif in_python:
                line = paint_python(line)
            elif PY_BEGIN.search(line):
                in_python = True
            out.append(f'<span class="{cls}">{paint(line)}</span>')
        # 改行では繋がない。<span> は block なので改行文字が余分な1行を作ってしまい、
        # 行送りが2倍に膨らんで空行が空行に見えなくなる（字も auto-scaling で半分まで縮む）
        return m.group(1) + "".join(out) + m.group(3)

    return re.sub(
        r"(<code class=\"language-[a-z]+\">)(.*?)(</code>)",
        one,
        html,
        flags=re.S,
    )


# 行頭の鉤括弧は、括弧の左が空くぶん頭が内側に入る。
# CSS だけでは「で始まるかどうかを見分けられないので、ここで印を付けてぶら下げる。
# （hanging-punctuation は Chrome が未対応）
# 和文の括弧だけを対象にする。ラテンの “ ' は字幅が狭く、同じ量を下げると出過ぎる
# 括弧の直前に <b> などが挟まっていても行頭は行頭。span も対象に入れる
# （P.9/P.10 の <span class="cr"><b>『METAL GEAR SOLID』 がこれで漏れていた）。
# text-indent はブロックにしか効かないので、インラインの span に付いても害はない
HANG = re.compile(r'<(h1|h2|p|div|span)([^>]*)>((?:<[^/][^>]*>)*\s*[「『（【〈《])')
# 中央ぞろえの行は、下げる量が左ぞろえと違う。行頭の空きは左右のアキの差として
# 出るので、半分だけ戻せば釣り合う。全部下げると今度は左へ出すぎる
CENTERED = re.compile(r'class="[^"]*\b(msg|concl|rel|who|ids|doc-h)\b')
# 「（複雑さ大）」のように括弧で始まって括弧で閉じる短い語は、左右の空きが
# 相殺して中心がもともと揃っている。下げると逆にずれる（P.16/P.17 で実測）
OPEN_B = "（「『【〈《"
CLOSE_B = "）」』】〉》"


def balanced(head_and_rest: str) -> bool:
    """行頭の括弧が、その行の中で閉じて終わっているか。

    「（複雑さ大）」のように括弧で始まり括弧で閉じて終わる短い語は、
    開き括弧の左の空きを閉じ括弧の右の空きが打ち消すので、下げると逆にずれる。
    「「楽しく作る」をデザインする」のように括弧の後に文が続くものは相殺しない。
    タグは中身を持たないので取り除いてから見る。
    """
    text = re.sub(r"<[^>]*>", "", head_and_rest)
    text = text.strip()
    if not text or text[0] not in OPEN_B:
        return False
    depth = 0
    for i, ch in enumerate(text):
        if ch in OPEN_B:
            depth += 1
        elif ch in CLOSE_B:
            depth -= 1
            if depth == 0:
                # 閉じたところで行が終わっていれば相殺する
                return text[i + 1:].strip() == ""
    return False


def hang(html: str) -> str:
    """行頭の和文括弧をぶら下げる。

    タグや class で対象を絞らず、行頭が和文括弧なら必ず下げる。
    絞ると漏れた要素（.msg・.v・.fn など）だけ左端が13.5px内側に入る。
    """
    def one(m):
        tag, attrs, head = m.groups()
        # 括弧で閉じる短い語は、開き括弧の空きを閉じ括弧の空きが打ち消すので触らない。
        # 行の終わりまで見たいので、開始タグに対応する終了タグまでを渡す
        seg = html[m.start():m.start() + 400]
        end = seg.find(f"</{tag}>")
        if end >= 0:
            seg = seg[:end]
        seg = seg[len(f"<{tag}{attrs}>"):]
        if balanced(seg):
            return m.group(0)
        cls = "hang mid " if CENTERED.search(attrs) else "hang "
        if 'class="' in attrs:
            attrs = attrs.replace('class="', 'class="' + cls, 1)
        else:
            attrs += f' class="{cls.strip()}"'
        return f"<{tag}{attrs}>{head}"

    return HANG.sub(one, html)


# 和文と欧文のあいだの四分アキ。日本語組版では和欧の境目に 1/4em ほどの
# 空きを入れる（公式ドキュメントの日本語もすべて空きを入れている）。
# 半角スペースを打つと 1/2em で広すぎ、CSS の text-autospace は Chrome が未対応。
# タグの中とコードは触らない（Marp は各スライドを <svg> で包むので svg は外せない）。
# エンティティ（&copy; など）は末尾が ; なので和字と隣り合わず、そのまま素通りする。
# 数字だけの連なりは欧文として扱わない。「2018 年」「4,900 円」「1 つ」のように
# 数量に助数詞・単位が続くものは、日本語では空けないため。
# 一方「PS2」「3D」「Base64」は数字が語の一部で、後ろに来るのは助詞・和語なので空ける。
# 見分けは「英字を1つ以上含むか」。版番号は語の続きとして扱う（「Pyxel 3.0」）。
# 約物（、。「」（）・）も対象外。約物は自分で空きを持っているので、足すと空きすぎる
JA = "ぁ-んァ-ヴー々〆ヵヶ一-龥"
HEAD = r"[0-9]*[A-Za-z]"                        # 欧文語の始まり（3D の 3 も含む）
WORD = HEAD + r"[A-Za-z0-9]*(?:[ ][0-9][0-9.]*)?"   # 末尾の括弧は版番号（Pyxel 3.0）
# 欧文語 → 和字。語の切れ目から見るので「をBase64」も拾える
# （\b は使えない。和字も \w なので語頭と見なされない）
AKI_BEFORE_JA = re.compile(r"(?<![A-Za-z0-9])" + WORD + r"(?=[" + JA + "])")
# 和字 → 欧文語
AKI_AFTER_JA = re.compile(r"([" + JA + r"])(?=" + HEAD + ")")
# <title> はブラウザのタブと PDF のメタデータに出る「文字列」で、組版の対象ではない。
# ここにアキの span を入れると、タブに &lt;span class="aki"&gt; が見える
KEEP = re.compile(r"<(pre|script|style|title)\b.*?</\1>", re.S)


SPAN = '<span class="aki"></span>'
# 開きタグの直後に入るアキ。要素の中身の先頭なので、その要素が行になる場合は
# ただの字下げになる。CSS で消せるよう印を付ける（:first-child はテキストを
# 数えないので、文中のアキまで巻き込む。だからここで区別する）
SPAN_LEAD = '<span class="aki lead"></span>'
OPEN_TAG = re.compile(r"<(a|b|strong|em|i|small|span|code|sup|sub)\b[^>]*>\Z", re.I)
KAN = re.compile(r"[" + JA + r"]")
# 要素をまたぐ判定用。同じ WORD・HEAD から組むので、文中の判定とずれない
WORD_END = re.compile(r"(?<![A-Za-z0-9])" + WORD + r"\Z")
WORD_START = re.compile(HEAD)


def is_boundary(before: str, after: str) -> bool:
    """要素をまたいだ隣り合わせが和欧の境目か。前後のテキストを丸ごと受け取る。

    末尾・先頭の1字だけでは、数字が欧文語の一部か数量かを見分けられない。
    「km19809」＋「氏」（P.35）は語の一部、「2018」＋「年」は数量。
    """
    if not before or not after:
        return False
    if KAN.match(after[0]):
        return bool(WORD_END.search(before))
    if KAN.match(before[-1]):
        return bool(WORD_START.match(after))
    return False


def aki_text(text: str) -> str:
    text = AKI_BEFORE_JA.sub(r'\g<0>' + SPAN, text)
    return AKI_AFTER_JA.sub(r'\1' + SPAN, text)


# <a> や <b> をまたいだ和欧の境目（「…Examples</a>に集まった」など）も拾う。
# 行が変わるブロック要素の境目では入れない
INLINE = re.compile(r"</?(a|b|strong|em|i|small|span|code|sup|sub)\b[^>]*>\Z", re.I)


def aki_outside_tags(chunk: str) -> str:
    out, pos, prev_text, prev_tag = [], 0, "", ""
    for m in re.finditer(r"<[^>]+>", chunk):
        text = chunk[pos:m.start()]
        # 直前がインラインタグで、その前の字と今の字が和欧の境目なら、ここにアキを入れる
        if text and prev_text and INLINE.search(prev_tag):
            if is_boundary(prev_text, text):
                out.append(SPAN_LEAD if OPEN_TAG.search(prev_tag) else SPAN)
        out.append(aki_text(text))
        out.append(m.group(0))
        if text:
            prev_text = text
        prev_tag = m.group(0)
        pos = m.end()
    tail = chunk[pos:]
    if tail and prev_text and INLINE.search(prev_tag):
        if is_boundary(prev_text, tail):
            out.append(SPAN_LEAD if OPEN_TAG.search(prev_tag) else SPAN)
    out.append(aki_text(tail))
    return "".join(out)


def aki(html: str) -> str:
    out, pos = [], 0
    for m in KEEP.finditer(html):
        out.append(aki_outside_tags(html[pos:m.start()]))
        out.append(m.group(0))          # コードはそのまま
        pos = m.end()
    out.append(aki_outside_tags(html[pos:]))
    return "".join(out)


# コードの中の長いURLは、そのままだと任意の位置で折り返されて
# 「…jsdelivr.ne / t/gh/…」のように単語の途中で切れる。<wbr> を / の後に
# 差し込み、折り返しをパスの区切りに限定する。<pre> の中だけに入れる
# （href の中に入れるとリンクが壊れる）
URL_IN_CODE = re.compile(r"https?://[^\s\"&<]+")
PRE_BLOCK = re.compile(r"<pre\b.*?</pre>", re.S)


def url_wbr(html: str) -> str:
    def in_pre(m):
        return URL_IN_CODE.sub(
            lambda u: re.sub(r"/(?=[^/])", "/<wbr>", u.group(0)), m.group(0))
    return PRE_BLOCK.sub(in_pre, html)


# CSS の background-image は、その要素を実際に描くときになって初めて読みに行く。
# Chrome の --print-to-pdf は画面に描かないまま PDF を書き出すので、
# 読み込みが間に合わず、CSS からしか参照していない画像が丸ごと抜け落ちる
# （右下の住人が1枚おきに消える、という形で出る）。
# <img> でも使っている画像は先に読まれて残るので、CSS 専用の画像だけが欠ける。
# 先読みを宣言して、描く前に読み終わらせる。
CSS_URL = re.compile(r'url\(\s*"?([^")]+\.(?:png|jpg|jpeg|gif|webp|svg))"?\s*\)')


def preload_css_images(html: str, css_text: str) -> str:
    links = "".join(
        f'<link rel="preload" as="image" href="{u}">'
        for u in sorted(set(CSS_URL.findall(css_text))))
    if not links:
        return html
    return html.replace("</head>", links + "</head>", 1)


if __name__ == "__main__":
    path = sys.argv[1]
    src = open(path).read()
    theme = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "..", "theme", "pyxel.css")
    css = open(theme, encoding="utf-8").read()
    open(path, "w").write(preload_css_images(url_wbr(aki(hang(wrap(src)))), css))
