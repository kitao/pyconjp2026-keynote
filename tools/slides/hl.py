"""Post-processing for the built HTML.

Marp cannot highlight individual lines of code, so the generated HTML is
rewritten here. Marking a line in slides.md with a trailing `#!hl` drops the
marker from the output and gives that line a faint background instead.

  while True:  #!hl   ->   <span class="cl hl">while True:</span>

Every line is wrapped in <span class="cl"> so the background can be laid down
per line; highlight.js never spans a newline, so splitting on newlines is safe.

The same pass hangs opening brackets at the start of a line and inserts the
quarter-space between Japanese and Latin text.
"""

import os
import re
import sys

# The marker is a Python comment, so highlight.js wraps it in
# <span class="hljs-comment">.
MARK = re.compile(r'\s*(<span class="hljs-comment">)?#!hl(</span>)?\s*$')

# highlight.js does not know Pyxel, so pyxel.xxx is coloured here. Names in all
# caps are constants (KEY_LEFT and friends); the rest are functions (init, blt).
PYXEL = re.compile(r"\bpyxel\.([A-Za-z_]\w*)")


# pyxel.js inside a URL is a file name, not a module plus a function. It is
# part of a string literal, so it is left alone; colouring it would tint the
# middle of the string.
URL_PLAIN = re.compile(r"https?://[^\s\"&<]+")


# The body of <pyxel-run script="..."> is Python, but the block is parsed as
# HTML, so highlight.js leaves it plain. To make it read like the game slides
# (23-27), Python colours are applied inside that attribute, reusing the class
# names highlight.js would have used.
PY_BEGIN = re.compile(r'class="hljs-name">pyxel-run<')
PY_END = re.compile(r"^&quot;")
PY_KEYWORD = re.compile(
    r"\b(import|from|as|def|class|return|if|elif|else|for|while|in|is|not|and|or"
    r"|pass|break|continue|with|lambda|global|nonlocal|yield|try|except|finally|raise)\b")
PY_NUMBER = re.compile(r"\b\d+(?:\.\d+)?\b")


def paint_python(line: str) -> str:
    """Colour one line inside an attribute as Python (pyxel.xxx is paint's job)."""
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
        out.append(m.group(0))          # URLs pass through untouched
        pos = m.end()
    out.append(PYXEL.sub(one, line[pos:]))
    return "".join(out)


def wrap(html: str) -> str:
    def one(m):
        body = m.group(2)
        # The newline just before </code> is not a line
        if body.endswith("\n"):
            body = body[:-1]
        out = []
        in_python = False            # Inside <pyxel-run script="...">?
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
        # Join without newlines. The spans are block level, so a newline
        # character would add a line of its own: the leading would double,
        # blank lines would stop reading as blank, and auto-scaling would
        # shrink the type to half its size.
        return m.group(1) + "".join(out) + m.group(3)

    return re.sub(
        r"(<code class=\"language-[a-z]+\">)(.*?)(</code>)",
        one,
        html,
        flags=re.S,
    )


# An opening bracket at the start of a line sits inset, because the bracket
# carries space on its left. CSS alone cannot tell whether a line starts with
# one (Chrome does not support hanging-punctuation), so it is marked here and
# hung by the theme.
# Only Japanese brackets qualify; the Latin quotes are narrow, and hanging them
# by the same amount pushes them too far out.
# A line still starts at its start even with <b> or a span in between, so those
# are matched too (this is what used to miss the opening bracket in
# <span class="cr"><b> on slides 9 and 10).
# text-indent only applies to blocks, so putting it on an inline span is inert.
HANG = re.compile(r'<(h1|h2|p|div|span)([^>]*)>((?:<[^/][^>]*>)*\s*[「『（【〈《])')
# A centred line needs a different amount. There the leading space shows up as
# a difference between the left and right margins, so hanging it half way
# balances; hanging it fully pushes the line too far left.
CENTERED = re.compile(r'class="[^"]*\b(msg|concl|rel|who|ids|doc-h)\b')
# A short phrase that both opens and closes with a bracket already balances:
# the space on the left is cancelled by the space on the right, so hanging it
# throws it off instead (measured on slides 16 and 17).
OPEN_B = "（「『【〈《"
CLOSE_B = "）」』】〉》"


def balanced(head_and_rest: str) -> bool:
    """Does the opening bracket close again before the line ends?

    A short phrase that opens and closes with a bracket cancels its own edges,
    so hanging it makes it worse. A line where text continues after the closing
    bracket does not cancel and should be hung.
    Tags carry no width, so they are stripped before looking.
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
                # It cancels only if the line ends where the bracket closes
                return text[i + 1:].strip() == ""
    return False


def hang(html: str) -> str:
    """Hang Japanese opening brackets that start a line.

    No filtering by tag or class: if a line starts with one, it is hung.
    Filtering leaves elements out (.msg, .v, .fn and so on), and those alone
    end up inset by 13.5 px.
    """
    def one(m):
        tag, attrs, head = m.groups()
        # Leave the self-cancelling short phrases alone. The whole line is
        # needed to tell, so pass everything up to the matching closing tag.
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


# The quarter-space between Japanese and Latin text. Japanese typesetting puts
# roughly 1/4 em at the boundary; the Pyxel documentation does the same. Typing
# a space gives 1/2 em, which is too wide, and Chrome does not support the CSS
# text-autospace property, so the space is inserted here as an empty span.
# Tags and code are left alone (the svg cannot be skipped, since Marp wraps
# every slide in one). Entities such as &copy; end in a semicolon, so they
# never sit next to a Japanese character and pass straight through.
# A run of digits alone is not treated as Latin: a quantity followed by a
# counter or a unit is set solid in Japanese ("2018 nen", "4,900 yen", "1 tsu").
# In "PS2", "3D" and "Base64" the digits are part of the word and what follows
# is a particle, so those do take the space. The test is whether the run
# contains at least one letter. A version number counts as part of the word
# ("Pyxel 3.0").
# Punctuation is excluded too: it already carries its own space, and adding
# more opens the line up too far.
JA = "ぁ-んァ-ヴー々〆ヵヶ一-龥"
HEAD = r"[0-9]*[A-Za-z]"                        # Start of a Latin word (the 3 of 3D counts)
WORD = HEAD + r"[A-Za-z0-9]*(?:[ ][0-9][0-9.]*)?"   # Trailing group is a version (Pyxel 3.0)
# Latin word followed by Japanese. Matching from the word break also catches a
# word that follows Japanese directly (\b is no use here: Japanese counts as \w,
# so the boundary never registers).
AKI_BEFORE_JA = re.compile(r"(?<![A-Za-z0-9])" + WORD + r"(?=[" + JA + "])")
# Japanese followed by a Latin word
AKI_AFTER_JA = re.compile(r"([" + JA + r"])(?=" + HEAD + ")")
# <title> is a plain string shown in the browser tab and in the PDF metadata,
# not something being typeset. Inserting a span there puts a literal
# &lt;span class="aki"&gt; in the tab.
KEEP = re.compile(r"<(pre|script|style|title)\b.*?</\1>", re.S)


SPAN = '<span class="aki"></span>'
# A space that lands right after an opening tag. It sits at the very start of
# the element's content, so when that element becomes a line of its own the
# space is just an indent. It is marked so the theme can drop it. The mark is
# needed because :first-child does not count text nodes and would also catch
# spaces in the middle of a line.
SPAN_LEAD = '<span class="aki lead"></span>'
OPEN_TAG = re.compile(r"<(a|b|strong|em|i|small|span|code|sup|sub)\b[^>]*>\Z", re.I)
KAN = re.compile(r"[" + JA + r"]")
# Used across element boundaries. Built from the same WORD and HEAD, so it
# cannot drift from the in-text rule.
WORD_END = re.compile(r"(?<![A-Za-z0-9])" + WORD + r"\Z")
WORD_START = re.compile(HEAD)


def is_boundary(before: str, after: str) -> bool:
    """Is this cross-element boundary one between Japanese and Latin?

    Takes the whole text on each side. The last and first characters alone are
    not enough to tell a digit that belongs to a word from a digit that is a
    quantity: "km19809" + "shi" (slide 35) is a word, "2018" + "nen" is not.
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


# Also catch boundaries that straddle an <a> or <b>. Boundaries at block
# elements start a new line, so nothing is inserted there.
INLINE = re.compile(r"</?(a|b|strong|em|i|small|span|code|sup|sub)\b[^>]*>\Z", re.I)


def aki_outside_tags(chunk: str) -> str:
    out, pos, prev_text, prev_tag = [], 0, "", ""
    for m in re.finditer(r"<[^>]+>", chunk):
        text = chunk[pos:m.start()]
        # If an inline tag sits between two characters that form a boundary,
        # the space goes here.
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
        out.append(m.group(0))          # Code passes through untouched
        pos = m.end()
    out.append(aki_outside_tags(html[pos:]))
    return "".join(out)


# A long URL inside a code block wraps at an arbitrary point and breaks mid
# word ("...jsdelivr.ne / t/gh/..."). Inserting <wbr> after each slash confines
# the wrap to the path separators. Only inside <pre>: putting it in an href
# would break the link.
URL_IN_CODE = re.compile(r"https?://[^\s\"&<]+")
PRE_BLOCK = re.compile(r"<pre\b.*?</pre>", re.S)


def url_wbr(html: str) -> str:
    def in_pre(m):
        return URL_IN_CODE.sub(
            lambda u: re.sub(r"/(?=[^/])", "/<wbr>", u.group(0)), m.group(0))
    return PRE_BLOCK.sub(in_pre, html)


# A CSS background-image is only fetched once the element is actually painted.
# Chrome's --print-to-pdf writes the PDF without painting to a screen, so the
# fetch never completes in time and every image referenced only from CSS drops
# out (it shows up as the residents in the bottom right vanishing from every
# other page). Images that are also used in an <img> are fetched anyway, so
# only the CSS-only ones are lost. Declaring a preload makes them load before
# the paint.
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
