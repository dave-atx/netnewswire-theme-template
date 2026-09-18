from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nnw_theme_tools.cli import _absolute_homepage, command_init
from nnw_theme_tools.project import PLACEHOLDER_MARKER, ThemeError, write_plist


class InitTests(unittest.TestCase):
    def test_rejects_placeholder_homepage(self) -> None:
        with self.assertRaisesRegex(ThemeError, "placeholder"):
            _absolute_homepage("https://example.com")

    def test_initialization_removes_starter_screenshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            theme = root / "Starter.nnwtheme"
            theme.mkdir()
            write_plist(
                theme / "Info.plist",
                {
                    "ThemeIdentifier": "com.example.starter",
                    "Name": "Starter",
                    "CreatorHomePage": "https://example.com",
                    "CreatorName": "Theme Author",
                    "Version": 1,
                },
            )
            (root / "README.md").write_text(
                "<!-- nnw-theme-identity:start -->\nold\n"
                "<!-- nnw-theme-identity:end -->\n\nKept documentation.\n",
                encoding="utf-8",
            )
            (root / "screenshots").mkdir()
            screenshot = root / "screenshots" / "theme-preview.png"
            screenshot.write_bytes(b"template image")
            (root / PLACEHOLDER_MARKER).touch()
            args = argparse.Namespace(
                name="Quiet Reader",
                creator="Theme Author",
                homepage="https://github.com/theme-author",
                github_user="theme-author",
                identifier="io.github.theme-author.quiet-reader",
                confirm_identifier="io.github.theme-author.quiet-reader",
                marketplace="no",
                install_browser=False,
            )

            with (
                patch("nnw_theme_tools.cli.find_root", return_value=root),
                patch("nnw_theme_tools.cli.find_theme", return_value=theme),
            ):
                command_init(args)

            self.assertFalse(screenshot.exists())
            self.assertFalse((root / PLACEHOLDER_MARKER).exists())
            self.assertTrue((root / "Quiet Reader.nnwtheme").is_dir())
            self.assertIn("Kept documentation.", (root / "README.md").read_text())


if __name__ == "__main__":
    unittest.main()
