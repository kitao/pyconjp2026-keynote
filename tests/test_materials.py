"""The shipped trailer app and demo game stay in step with their sources."""

import re
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MaterialsTests(unittest.TestCase):
    def test_trailer_app_packages_exactly_the_current_sources(self):
        # The trailer QR code opens trailer/trailer.pyxapp straight from GitHub.
        with zipfile.ZipFile(ROOT / "trailer/trailer.pyxapp") as app:
            members = {name: app.read(name) for name in app.namelist()}
        self.assertEqual(members.pop("trailer/.pyxapp_startup_script"), b"trailer.py")
        expected = ["LICENSE-MPLUS.txt", "cast.png", "telop.py", "trailer.py",
                    "umplus_j10r.bdf", "umplus_j12r.bdf"]
        self.assertEqual(sorted(members), ["trailer/" + name for name in expected])
        for name, data in members.items():
            with self.subTest(name=name):
                self.assertEqual(data, (ROOT / name).read_bytes())

    def test_demo_game_is_the_code_on_the_last_game_slide(self):
        slide = (ROOT / "slides.md").read_text(encoding="utf-8").split("\n---\n")[27]
        shown = re.search(r"```python\n(.*?)```", slide, re.S).group(1)
        shown = re.sub(r"\s*#!hl$", "", shown, flags=re.M)
        game = (ROOT / "demo/game/game.py").read_text(encoding="utf-8")
        # Everything after the module docstring.
        self.assertEqual(game.split('"""\n', 1)[1], shown)


if __name__ == "__main__":
    unittest.main()
