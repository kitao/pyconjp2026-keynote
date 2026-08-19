"""Serve the deck and the pages it links to, with nothing coming off the network.

The talk opens three pages off the slides: Pyxel Code Maker, Pyxel MML Studio
and Pyxel User Examples. The first two fetch Pyodide, ace and a few small
libraries from public CDNs, so a bad hall network takes the demos down.

This serves those pages from the working copies already on this machine, and
swaps the addresses inside links and scripts for local ones. Follow a link from
the slides and it lands here instead of on github.io. Text the audience reads is
left alone, so the URL page 37 puts on screen still says github.io.

  python3 tools/stage/offline.py --fetch   # once, while the network is good
  python3 tools/stage/offline.py           # start it and open the deck

--fetch puts the third-party files under .offline/, which is not tracked: they
belong to other projects, and this repo carries the talk rather than a copy of
their releases. The Pyxel side is not copied at all — it is read from ../pyxel
and ../pyxel-user-examples (override with PYXEL_DIR / PYXEL_EXAMPLES_DIR).

MML Studio draws its QR code with api.qrserver.com, and the closing line of
that demo points at it. --fetch unpacks the segno wheel into .offline/ and this
draws the code itself, so the beat survives with the network down. Nothing is
installed; deleting .offline/ undoes it.
"""

import http.server
import io
import json
import mimetypes
import os
import re
import sys
import urllib.parse
import urllib.request
import webbrowser
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYXEL = Path(os.environ.get("PYXEL_DIR") or ROOT.parent / "pyxel")
EXAMPLES = Path(os.environ.get("PYXEL_EXAMPLES_DIR") or ROOT.parent / "pyxel-user-examples")
CACHE = ROOT / ".offline"
PYPI = CACHE / "pypi"
PORT = int(os.environ.get("PORT") or 8080)

# Every absolute URL these pages reach for, and the path that answers it once
# this server is the only thing listening. Order matters: longest prefix first.
REWRITES = (
    ("https://kitao.github.io/pyconjp2026-keynote/", "/"),
    ("https://kitao.github.io/pyxel-user-examples/", "/pyxel-user-examples/"),
    ("https://kitao.github.io/pyxel/web/", "/pyxel/web/"),
    ("https://cdn.jsdelivr.net/gh/", "/gh/"),
    ("https://cdn.jsdelivr.net/pyodide/", "/vendor/pyodide/"),
    ("https://cdn.jsdelivr.net/npm/", "/vendor/npm/"),
    ("https://cdnjs.cloudflare.com/ajax/libs/", "/vendor/cdnjs/"),
    ("https://api.qrserver.com/v1/create-qr-code/", "/qr"),
    # The launcher asks GitHub which commit a branch points at and falls back to
    # the branch name when no answer comes. Refusing at once is that same
    # fallback, without waiting out a DNS timeout in front of an audience.
    ("https://api.github.com/", "/api-github/"),
)

# The repos jsDelivr would serve under /gh/, and the working copy standing in
# for each. Anything else under /gh/ is a 404 rather than a silent miss.
GH_REPOS = {"kitao/pyxel": PYXEL, "kitao/pyconjp2026-keynote": ROOT}

# Rewriting only makes sense for files that can hold a URL.
TEXT_SUFFIXES = {".html", ".htm", ".js", ".mjs", ".css", ".json"}

# Pyodide streams its wasm, which fails unless the type is exactly this. The
# rest are types Python does not ship a guess for.
for _suffix, _type in (
    (".wasm", "application/wasm"),
    (".mjs", "text/javascript"),
    (".whl", "application/octet-stream"),
    (".pyxapp", "application/octet-stream"),
    (".pyxres", "application/octet-stream"),
):
    mimetypes.add_type(_type, _suffix)


def local_path(url_path):
    """Map a request path to a file, or None if it is outside what we serve."""
    path = urllib.parse.unquote(url_path.split("?", 1)[0].split("#", 1)[0])
    if path.startswith("/api-github/"):
        return None
    if path.startswith("/gh/"):
        parts = [p for p in path[len("/gh/"):].split("/") if p]
        if len(parts) < 2:
            return None
        # jsDelivr pins a revision as user/repo@ref; the working copy is the ref.
        base = GH_REPOS.get("%s/%s" % (parts[0], parts[1].split("@", 1)[0]))
        rest = parts[2:]
    else:
        for prefix, root in (
            ("/pyxel-user-examples/", EXAMPLES),
            ("/pyxel/", PYXEL),
            ("/vendor/", CACHE),
        ):
            if path.startswith(prefix):
                base, rest = root, path[len(prefix):].split("/")
                break
        else:
            base, rest = ROOT, path.split("/")
    if base is None:
        return None
    base = base.resolve()
    full = base.joinpath(*[p for p in rest if p and p != ".."]).resolve()
    return full if full == base or full.is_relative_to(base) else None


# Where a URL may be swapped inside HTML: the value of an attribute, or a CSS
# url(). Body text is left alone — page 37 puts the launcher's address on screen
# as the subject of the slide, and page 36 shows a script tag as printed code.
# Marp escapes the quotes in those code blocks, so neither can match here.
ATTR_URL = re.compile(
    r"""((?:href|src|action|poster|content)\s*=\s*["']|url\(\s*["']?)([^"')\s]+)""",
    re.I)
SCRIPT_BLOCK = re.compile(r"(<script\b[^>]*>)(.*?)(</script\s*>)", re.S | re.I)


def swap(text):
    for url, path in REWRITES:
        text = text.replace(url, path)
    return text


def rewrite(text, html):
    if not html:
        return swap(text)
    attrs = lambda part: ATTR_URL.sub(lambda m: m.group(1) + swap(m.group(2)), part)
    out, last = [], 0
    for match in SCRIPT_BLOCK.finditer(text):
        # Inside a script tag every URL is code, so all of it is fair game. The
        # opening tag still goes through attrs(), for its src.
        out += [attrs(text[last:match.start()]),
                attrs(match.group(1)) + swap(match.group(2)) + match.group(3)]
        last = match.end()
    out.append(attrs(text[last:]))
    return "".join(out)


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "keynote-offline"

    def do_GET(self):
        self.respond(True)

    def do_HEAD(self):
        self.respond(False)

    def respond(self, send_body):
        if self.path.split("?", 1)[0] == "/qr":
            png = draw_qr(urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query))
            if png is None:
                return self.reply(404, b"no qr encoder", "text/plain", send_body)
            return self.reply(200, png, "image/png", send_body)
        full = local_path(self.path)
        if full is None:
            return self.reply(404, b"not served here", "text/plain", send_body)
        if full.is_dir():
            # Without the slash the browser resolves ../ one level too high.
            if not self.path.split("?", 1)[0].endswith("/"):
                self.send_response(301)
                self.send_header("Location", self.path.split("?", 1)[0] + "/")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            full = full / "index.html"
        if not full.is_file():
            return self.reply(404, b"not found", "text/plain", send_body)

        kind = mimetypes.guess_type(full.name)[0] or "application/octet-stream"
        suffix = full.suffix.lower()
        if suffix in TEXT_SUFFIXES:
            text = full.read_text(encoding="utf-8")
            body = rewrite(text, suffix in (".html", ".htm")).encode("utf-8")
            kind += "; charset=utf-8"
        else:
            body = full.read_bytes()
        self.reply(200, body, kind, send_body)

    def reply(self, status, body, kind, send_body):
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if send_body:
            self.wfile.write(body)

    def log_message(self, fmt, *args):
        # A 200 says nothing; a miss is the only thing worth seeing on stage.
        if len(args) > 1 and str(args[1]) != "200":
            sys.stderr.write("  %s %s\n" % (args[1], args[0]))


def draw_qr(query):
    """Stand in for api.qrserver.com, whose parameters this mirrors."""
    if str(PYPI) not in sys.path:
        sys.path.insert(0, str(PYPI))
    try:
        import segno
    except ImportError:
        return None
    first = lambda key, fallback: query.get(key, [fallback])[0]
    size = int(first("size", "128x128").split("x")[0])
    # qrserver returns exactly the size asked for and leaves no quiet zone, so
    # the code fills the box. Matching both matters: the demo types MML in and
    # the audience watches the code grow, and a border of its own would make
    # this one read smaller than the one on the slide.
    buffer = io.BytesIO()
    segno.make(first("data", ""), error="l").save(
        buffer, kind="png", scale=1, border=0,
        dark="#" + first("color", "000000"),
        light="#" + first("bgcolor", "ffffff"))
    buffer.seek(0)
    try:
        from PIL import Image
    except ImportError:
        return buffer.getvalue()
    # Nearest, so the modules stay square-edged at the size the page asks for.
    grown = Image.open(buffer).convert("RGB").resize((size, size), Image.NEAREST)
    out = io.BytesIO()
    grown.save(out, format="PNG")
    return out.getvalue()


def fetch_segno():
    """Unpack the segno wheel into .offline/, rather than installing it."""
    with urllib.request.urlopen("https://pypi.org/pypi/segno/json", timeout=60) as response:
        release = json.load(response)["urls"]
    wheel = next(u["url"] for u in release if u["filename"].endswith("-py3-none-any.whl"))
    with urllib.request.urlopen(wheel, timeout=60) as response:
        data = response.read()
    PYPI.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        archive.extractall(PYPI)
    print("  %7.1f KB  %s (for the MML Studio QR code)"
          % (len(data) / 1024, PYPI.relative_to(ROOT)))


def wanted_urls():
    """Read every served file and collect the CDN URLs they name."""
    pattern = re.compile(
        "(%s)([A-Za-z0-9._~:/?#@!$&*+,;=%%-]+)"
        % "|".join(re.escape(u) for u, p in REWRITES if p.startswith("/vendor/"))
    )
    found = set()
    for root in (ROOT, PYXEL, EXAMPLES):
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
                continue
            if any(p in (".git", "node_modules", "target", "dist", ".offline")
                   for p in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            found.update(a + b for a, b in pattern.findall(text))

    # Both loaders build the paths to the rest of their own release at run time,
    # from where they were loaded. Nothing on disk names those files, so the
    # loop above cannot see them and they have to be listed.
    siblings = {
        "/ace.js": ("theme-monokai.js", "mode-python.js", "worker-python.js"),
        "/pyodide.js": ("pyodide-lock.json", "python_stdlib.zip",
                        "pyodide.asm.wasm", "pyodide.asm.mjs", "pyodide.asm.js"),
    }
    for url in sorted(found):
        for loader, names in siblings.items():
            if url.endswith(loader):
                base = url.rsplit("/", 1)[0] + "/"
                found.update(base + n for n in names)
    return sorted(found)


def fetch():
    urls = wanted_urls()
    if not urls:
        raise SystemExit("found no CDN urls to fetch; are ../pyxel and the deck in place?")
    total = 0
    for url in urls:
        for prefix, path in REWRITES:
            if url.startswith(prefix) and path.startswith("/vendor/"):
                dest = CACHE / path[len("/vendor/"):] / url[len(prefix):]
                break
        else:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                data = response.read()
        except OSError as error:
            # ace does not ship a worker for every mode; a miss here is normal.
            print("  skip %s (%s)" % (url, error))
            continue
        dest.write_bytes(data)
        total += len(data)
        print("  %7.1f KB  %s" % (len(data) / 1024, dest.relative_to(ROOT)))
    fetch_segno()
    print("cached %.1f MB under %s" % (total / 1048576, CACHE.relative_to(ROOT)))


def serve():
    missing = [str(p) for p in (PYXEL, EXAMPLES, CACHE) if not p.is_dir()]
    if missing:
        raise SystemExit("missing: %s\nrun --fetch first, or set PYXEL_DIR / "
                         "PYXEL_EXAMPLES_DIR" % ", ".join(missing))
    # Bind before opening anything: if the port is taken, the old server is
    # still answering and a browser window would hide that this one never ran.
    try:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError as error:
        raise SystemExit("cannot listen on port %d: %s\nanother copy is "
                         "probably running; stop it, or set PORT" % (PORT, error))
    base = "http://localhost:%d" % PORT
    print("deck            %s/" % base)
    print("code maker      %s/pyxel/web/code-maker/" % base)
    print("mml studio      %s/pyxel/web/mml-studio/" % base)
    print("user examples   %s/pyxel-user-examples/" % base)
    print("\nlinks in the slides now point here. misses are listed below.\n")
    webbrowser.open_new_tab(base + "/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    flags = sys.argv[1:]
    unknown = [f for f in flags if f != "--fetch"]
    if unknown:
        raise SystemExit("unknown option %s; see the top of this file"
                         % ", ".join(unknown))
    fetch() if "--fetch" in flags else serve()
