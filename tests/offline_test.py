"""Regression checks for offline-demo paths and redirects; no network downloads."""

import http.client
import importlib.util
import io
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("keynote_offline", ROOT / "tools/stage/offline.py")
offline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(offline)


class OfflineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "repo"
        self.root.mkdir()
        self.patches = patch.multiple(
            offline, ROOT=self.root, PYXEL=self.root / "pyxel",
            EXAMPLES=self.root / "examples", CACHE=self.root / "cache",
            GH_REPOS={"kitao/pyxel": self.root / "pyxel"},
        )
        self.patches.start()
        self.addCleanup(self.patches.stop)

    def test_public_paths_remain_inside_their_mount(self):
        self.assertEqual(offline.local_path("/assets/image.png"), self.root / "assets/image.png")
        self.assertEqual(offline.local_path("/pyxel/web/code-maker/?x=1"), self.root / "pyxel/web/code-maker")
        self.assertEqual(offline.local_path("/gh/kitao/pyxel@main/wasm/pyxel.js"), self.root / "pyxel/wasm/pyxel.js")

    def test_hidden_files_and_traversal_are_rejected(self):
        for path in ["/.git/config", "/.env", "/%2egit/config", "/assets/../.env", "/assets/%2e%2e/file", "/vendor/.env"]:
            with self.subTest(path=path):
                self.assertIsNone(offline.local_path(path))

    def test_symlinks_cannot_expose_hidden_files_or_leave_the_mount(self):
        (self.root / "alias").symlink_to(self.root / ".env")
        (self.root / "outside").symlink_to(self.root.parent / "private")
        self.assertIsNone(offline.local_path("/alias"))
        self.assertIsNone(offline.local_path("/outside"))

    def test_current_links_are_rewritten_without_changing_printed_text(self):
        text = '<a href="https://kitao.dev/pyxel/code-maker/">https://kitao.dev/pyxel/</a>'
        self.assertEqual(offline.rewrite(text, True), '<a href="/pyxel/web/code-maker/">https://kitao.dev/pyxel/</a>')
        self.assertEqual(offline.swap('https://kitao.dev/pyxel/2.9.9/pyxel.js'), '/pyxel/wasm/pyxel.js')

    def test_error_logs_do_not_include_query_values(self):
        output = io.StringIO()
        request = SimpleNamespace(path="/missing?token=synthetic-value")
        with patch.object(offline.sys, "stderr", output):
            offline.Handler.log_message(request, "%s %s", "GET /missing?token=synthetic-value", "404")
        self.assertEqual(output.getvalue(), "  404 /missing\n")

    def test_http_redirects_keep_queries_and_hidden_paths_return_404(self):
        directory = self.root / "app"
        directory.mkdir()
        (directory / "index.html").write_text("offline app")

        class QuietHandler(offline.Handler):
            def log_message(self, *_):
                pass

        with offline.http.server.ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                connection = http.client.HTTPConnection("127.0.0.1", server.server_port)
                connection.request("GET", "/app?play=example")
                response = connection.getresponse()
                self.assertEqual(response.status, 301)
                self.assertEqual(response.getheader("Location"), "/app/?play=example")
                response.read()
                connection.request("GET", "/.git/config")
                response = connection.getresponse()
                self.assertEqual(response.status, 404)
                response.read()
                connection.close()
            finally:
                server.shutdown()
                thread.join()


if __name__ == "__main__":
    unittest.main()
